import hashlib
from dataclasses import dataclass
from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.logistics.models import (
    GeographicPoint,
    ImportBatch,
    ImportIssue,
    Office,
    Priority,
    Route,
    RoutePayload,
)

from .normalization import json_safe, to_integer
from .staging import write_staging_tables
from .validation import PayloadCandidate, RouteCandidate, validate_route_record
from .workbook import (
    WorkbookStructureError,
    build_payload_groups,
    extract_reference_data,
    frame_records,
    read_workbook,
)


MAX_RESPONSE_ERRORS = 200


class ImportServiceError(RuntimeError):
    def __init__(self, message: str, batch_id=None):
        super().__init__(message)
        self.batch_id = batch_id


@dataclass(frozen=True)
class ImportSummary:
    batch_id: str
    status: str
    total_rows: int
    imported: int
    rejected: int
    error_count: int
    errors: list[dict[str, Any]]

    def as_dict(self) -> dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "status": self.status,
            "total_rows": self.total_rows,
            "imported": self.imported,
            "rejected": self.rejected,
            "error_count": self.error_count,
            "errors": self.errors,
            "has_more_errors": self.error_count > len(self.errors),
        }


class RouteImportService:
    @classmethod
    def import_uploaded_file(cls, uploaded_file) -> ImportSummary:
        content = uploaded_file.read()
        batch = ImportBatch.objects.create(
            file_name=uploaded_file.name,
            file_checksum=hashlib.sha256(content).hexdigest(),
        )

        try:
            frames = read_workbook(content)
            offices, priorities, points = extract_reference_data(frames)
            with transaction.atomic():
                write_staging_tables(batch.id, frames)
                cls._upsert_references(offices, priorities, points)
                summary = cls._validate_and_persist(batch, frames, offices, priorities, points)
            return summary
        except WorkbookStructureError as exc:
            cls._mark_failed(batch, "INVALID_WORKBOOK", str(exc))
            raise ImportServiceError(str(exc), batch.id) from exc
        except Exception as exc:
            message = "La importación falló durante el procesamiento o la persistencia."
            cls._mark_failed(batch, "IMPORT_FAILED", f"{message} {exc}")
            raise ImportServiceError(message, batch.id) from exc

    @staticmethod
    def _upsert_references(offices, priorities, points) -> None:
        Office.objects.bulk_create(
            [Office(**office) for office in offices],
            update_conflicts=True,
            update_fields=["name"],
            unique_fields=["id"],
            batch_size=500,
        )
        Priority.objects.bulk_create(
            [Priority(**priority) for priority in priorities],
            update_conflicts=True,
            update_fields=["name"],
            unique_fields=["id"],
            batch_size=500,
        )
        GeographicPoint.objects.bulk_create(
            [GeographicPoint(**point) for point in points],
            update_conflicts=True,
            update_fields=["city", "latitude_reference", "longitude_reference"],
            unique_fields=["id"],
            batch_size=500,
        )

    @classmethod
    def _validate_and_persist(cls, batch, frames, offices, priorities, points) -> ImportSummary:
        route_records = frame_records(frames["routes"])
        payload_groups = build_payload_groups(frames["route_payload"])
        office_ids = {office["id"] for office in offices}
        priority_ids = {priority["id"] for priority in priorities}
        geographic_points = {point["id"]: point for point in points}
        existing_source_ids = set(
            Route.objects.exclude(source_id__isnull=True).values_list("source_id", flat=True)
        )
        existing_business_keys = set(
            Route.objects.values_list(
                "origin",
                "destination",
                "time_window_start",
                "time_window_end",
            )
        )
        seen_source_ids: set[int] = set()
        seen_business_keys: set[tuple] = set()
        valid_candidates: list[tuple[RouteCandidate, PayloadCandidate]] = []
        issue_models: list[ImportIssue] = []
        response_errors: list[dict[str, Any]] = []

        for row_number, row in enumerate(route_records, start=2):
            route_source_id = to_integer(row.get("idRoute"))
            grouped_payloads = payload_groups.get(route_source_id, []) if route_source_id is not None else []
            payload_raw = grouped_payloads[0] if grouped_payloads else None
            result = validate_route_record(
                row,
                payload_raw,
                office_ids=office_ids,
                priority_ids=priority_ids,
                geographic_points=geographic_points,
                seen_source_ids=seen_source_ids,
                seen_business_keys=seen_business_keys,
                existing_source_ids=existing_source_ids,
                existing_business_keys=existing_business_keys,
                duplicate_payload=len(grouped_payloads) > 1,
            )
            if result.is_valid:
                valid_candidates.append((result.route, result.payload))
                continue

            for issue in result.issues:
                issue_data = issue.as_dict(row_number, route_source_id)
                issue_models.append(
                    ImportIssue(
                        batch=batch,
                        row_number=row_number,
                        route_source_id=route_source_id,
                        field=issue.field,
                        code=issue.code,
                        message=issue.message,
                        raw_value=json_safe(issue.raw_value),
                    )
                )
                if len(response_errors) < MAX_RESPONSE_ERRORS:
                    response_errors.append(issue_data)

        if issue_models:
            ImportIssue.objects.bulk_create(issue_models, batch_size=500)

        route_models = [
            Route(
                source_id=route.source_id,
                origin_office_id=route.office_id,
                registered_at=route.registered_at,
                origin=route.origin,
                destination=route.destination,
                distance_km=route.distance_km,
                priority_id=route.priority_id,
                time_window_start=route.time_window_start,
                time_window_end=route.time_window_end,
                status=route.status,
                created_at=route.created_at,
                import_batch=batch,
            )
            for route, _ in valid_candidates
        ]
        Route.objects.bulk_create(route_models, batch_size=500)

        payload_models = [
            RoutePayload(
                route=route_model,
                raw_payload=payload.raw_payload,
                point_id=payload.point_id,
                address=payload.address,
                latitude=payload.latitude,
                longitude=payload.longitude,
                first_piece_weight=payload.first_piece_weight,
            )
            for route_model, (_, payload) in zip(route_models, valid_candidates, strict=True)
        ]
        RoutePayload.objects.bulk_create(payload_models, batch_size=500)

        imported = len(valid_candidates)
        rejected = len(route_records) - imported
        batch.status = ImportBatch.Status.COMPLETED
        batch.total_rows = len(route_records)
        batch.imported_rows = imported
        batch.rejected_rows = rejected
        batch.completed_at = timezone.now()
        batch.save(
            update_fields=[
                "status",
                "total_rows",
                "imported_rows",
                "rejected_rows",
                "completed_at",
            ]
        )
        return ImportSummary(
            batch_id=str(batch.id),
            status=batch.status,
            total_rows=len(route_records),
            imported=imported,
            rejected=rejected,
            error_count=len(issue_models),
            errors=response_errors,
        )

    @staticmethod
    def _mark_failed(batch, code: str, message: str) -> None:
        batch.status = ImportBatch.Status.FAILED
        batch.completed_at = timezone.now()
        batch.save(update_fields=["status", "completed_at"])
        ImportIssue.objects.create(
            batch=batch,
            row_number=1,
            field="workbook",
            code=code,
            message=message,
        )

