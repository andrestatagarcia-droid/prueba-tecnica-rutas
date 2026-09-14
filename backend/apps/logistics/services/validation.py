import re
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Mapping, MutableSet

from .normalization import (
    get_alias,
    is_missing,
    json_safe,
    normalize_comparison_text,
    normalize_spaces,
    parse_json_object,
    to_datetime,
    to_decimal,
    to_integer,
)


ALLOWED_STATUSES = {"PENDING", "READY", "EXECUTED", "FAILED"}
ADDRESS_PATTERN = re.compile(
    r"^(?:cll|calle|cra|carrera|av|avenida|dg|diagonal|tv|transversal)\s+"
    r"\d+[a-z]?\s*#\s*\d+[a-z]?\s*-\s*\d+\s*,\s*[\wáéíóúüñ .-]+$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ValidationIssue:
    field: str
    code: str
    message: str
    raw_value: Any = None

    def as_dict(self, row_number: int, route_source_id: int | None) -> dict[str, Any]:
        return {
            "row": row_number,
            "route_id": route_source_id,
            "field": self.field,
            "code": self.code,
            "message": self.message,
            "raw_value": json_safe(self.raw_value),
        }


@dataclass(frozen=True)
class RouteCandidate:
    source_id: int
    office_id: int
    registered_at: datetime
    origin: str
    destination: str
    distance_km: Decimal
    priority_id: int
    time_window_start: datetime
    time_window_end: datetime
    status: str
    created_at: datetime


@dataclass(frozen=True)
class PayloadCandidate:
    raw_payload: dict[str, Any]
    point_id: int
    address: str
    latitude: Decimal
    longitude: Decimal
    first_piece_weight: Decimal | None


@dataclass
class RecordValidationResult:
    route: RouteCandidate | None = None
    payload: PayloadCandidate | None = None
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return self.route is not None and self.payload is not None and not self.issues


def _required_text(row: Mapping[str, Any], field_name: str, issues: list[ValidationIssue]) -> str | None:
    value = normalize_spaces(row.get(field_name))
    if value is None:
        issues.append(ValidationIssue(field_name, "REQUIRED", f"El campo {field_name} es obligatorio.", row.get(field_name)))
    return value


def _required_integer(row: Mapping[str, Any], field_name: str, issues: list[ValidationIssue]) -> int | None:
    raw_value = row.get(field_name)
    if is_missing(raw_value):
        issues.append(ValidationIssue(field_name, "REQUIRED", f"El campo {field_name} es obligatorio.", raw_value))
        return None
    value = to_integer(raw_value)
    if value is None:
        issues.append(ValidationIssue(field_name, "INVALID_INTEGER", f"El campo {field_name} debe ser un entero.", raw_value))
    return value


def _required_datetime(row: Mapping[str, Any], field_name: str, issues: list[ValidationIssue]) -> datetime | None:
    raw_value = row.get(field_name)
    if is_missing(raw_value):
        issues.append(ValidationIssue(field_name, "REQUIRED", f"El campo {field_name} es obligatorio.", raw_value))
        return None
    value = to_datetime(raw_value)
    if value is None:
        issues.append(ValidationIssue(field_name, "INVALID_DATETIME", f"El campo {field_name} no contiene una fecha y hora válida.", raw_value))
    return value


def validate_route_record(
    row: Mapping[str, Any],
    payload_raw: Any,
    *,
    office_ids: set[int],
    priority_ids: set[int],
    geographic_points: Mapping[int, Mapping[str, Any]],
    seen_source_ids: MutableSet[int],
    seen_business_keys: MutableSet[tuple[str, str, datetime, datetime]],
    existing_source_ids: set[int] | None = None,
    existing_business_keys: set[tuple[str, str, datetime, datetime]] | None = None,
    duplicate_payload: bool = False,
) -> RecordValidationResult:
    issues: list[ValidationIssue] = []
    existing_source_ids = existing_source_ids or set()
    existing_business_keys = existing_business_keys or set()

    source_id = _required_integer(row, "idRoute", issues)
    if source_id is not None:
        if source_id <= 0:
            issues.append(ValidationIssue("idRoute", "NON_POSITIVE", "El identificador de ruta debe ser positivo.", source_id))
        if source_id in seen_source_ids:
            issues.append(ValidationIssue("idRoute", "DUPLICATE_ROUTE_ID", "El identificador de ruta está repetido dentro del archivo.", source_id))
        else:
            seen_source_ids.add(source_id)
        if source_id in existing_source_ids:
            issues.append(ValidationIssue("idRoute", "ROUTE_ALREADY_IMPORTED", "La ruta ya existe en la base de datos.", source_id))

    office_id = _required_integer(row, "idOficinaOrigen", issues)
    if office_id is not None and office_id not in office_ids:
        issues.append(ValidationIssue("idOficinaOrigen", "UNKNOWN_OFFICE", "La oficina de origen no existe en el catálogo.", office_id))

    origin = _required_text(row, "origin", issues)
    destination = _required_text(row, "destination", issues)

    raw_distance = row.get("distance_km")
    distance = to_decimal(raw_distance)
    if is_missing(raw_distance):
        issues.append(ValidationIssue("distance_km", "REQUIRED", "La distancia es obligatoria.", raw_distance))
    elif distance is None:
        issues.append(ValidationIssue("distance_km", "INVALID_NUMBER", "La distancia debe ser numérica.", raw_distance))
    elif distance <= 0:
        issues.append(ValidationIssue("distance_km", "NON_POSITIVE_DISTANCE", "La distancia debe ser mayor que cero.", raw_distance))

    priority_id = _required_integer(row, "priority", issues)
    if priority_id is not None:
        if priority_id <= 0:
            issues.append(ValidationIssue("priority", "NON_POSITIVE_PRIORITY", "La prioridad debe ser positiva.", priority_id))
        elif priority_id not in priority_ids:
            issues.append(ValidationIssue("priority", "UNKNOWN_PRIORITY", "La prioridad no existe en el catálogo.", priority_id))

    time_window_start = _required_datetime(row, "time_window_start", issues)
    time_window_end = _required_datetime(row, "time_window_end", issues)
    if time_window_start is not None and time_window_end is not None and time_window_start >= time_window_end:
        issues.append(ValidationIssue("time_window", "INVALID_TIME_WINDOW", "La fecha inicial debe ser menor que la fecha final.", {"start": time_window_start, "end": time_window_end}))

    status = normalize_spaces(row.get("status"))
    status = status.upper() if status else None
    if status is None:
        issues.append(ValidationIssue("status", "REQUIRED", "El estado es obligatorio.", row.get("status")))
    elif status not in ALLOWED_STATUSES:
        issues.append(ValidationIssue("status", "INVALID_STATUS", "El estado no pertenece al conjunto permitido.", status))

    registered_at = _required_datetime(row, "fechaRegistro", issues)
    created_at = _required_datetime(row, "created_at", issues)

    if origin and destination and time_window_start and time_window_end:
        business_key = (origin, destination, time_window_start, time_window_end)
        if business_key in seen_business_keys:
            issues.append(ValidationIssue("route", "DUPLICATE_IN_FILE", "La combinación de origen, destino y ventana está repetida dentro del archivo."))
        else:
            seen_business_keys.add(business_key)
        if business_key in existing_business_keys:
            issues.append(ValidationIssue("route", "DUPLICATE_IN_DATABASE", "La combinación de origen, destino y ventana ya existe."))

    route_candidate = None
    required_route_values = (
        source_id,
        office_id,
        registered_at,
        origin,
        destination,
        distance,
        priority_id,
        time_window_start,
        time_window_end,
        status,
        created_at,
    )
    if all(value is not None for value in required_route_values):
        route_candidate = RouteCandidate(
            source_id=source_id,
            office_id=office_id,
            registered_at=registered_at,
            origin=origin,
            destination=destination,
            distance_km=distance,
            priority_id=priority_id,
            time_window_start=time_window_start,
            time_window_end=time_window_end,
            status=status,
            created_at=created_at,
        )

    payload_candidate = _validate_payload(
        payload_raw,
        geographic_points=geographic_points,
        issues=issues,
        duplicate_payload=duplicate_payload,
    )
    return RecordValidationResult(route=route_candidate, payload=payload_candidate, issues=issues)


def _validate_payload(
    payload_raw: Any,
    *,
    geographic_points: Mapping[int, Mapping[str, Any]],
    issues: list[ValidationIssue],
    duplicate_payload: bool,
) -> PayloadCandidate | None:
    if duplicate_payload:
        issues.append(ValidationIssue("payload", "DUPLICATE_PAYLOAD", "La ruta tiene más de un payload en el archivo."))
    if is_missing(payload_raw):
        issues.append(ValidationIssue("payload", "MISSING_PAYLOAD", "No existe payload para la ruta."))
        return None

    payload = parse_json_object(payload_raw)
    if payload is None:
        issues.append(ValidationIssue("payload", "INVALID_JSON", "El payload no contiene un objeto JSON válido.", payload_raw))
        return None

    found_point, point_raw, _ = get_alias(payload, ["idPunto", "id_punto", "pointId", "point_id"])
    point_id = to_integer(point_raw) if found_point else None
    if not found_point or is_missing(point_raw):
        issues.append(ValidationIssue("idPunto", "REQUIRED", "El identificador del punto es obligatorio.", point_raw))
    elif point_id is None:
        issues.append(ValidationIssue("idPunto", "INVALID_INTEGER", "El identificador del punto debe ser un entero.", point_raw))

    reference = geographic_points.get(point_id) if point_id is not None else None
    if point_id is not None and reference is None:
        issues.append(ValidationIssue("idPunto", "UNKNOWN_GEOGRAPHIC_POINT", "El punto no existe en poblacion_cor.", point_id))

    found_address, address_raw, _ = get_alias(payload, ["direccion", "dirección", "address"])
    address = normalize_spaces(address_raw) if found_address else None
    address_format_valid = True
    if address is None:
        issues.append(ValidationIssue("address", "MISSING_ADDRESS", "La dirección es obligatoria.", address_raw))
        address_format_valid = False
    elif not ADDRESS_PATTERN.match(address):
        issues.append(ValidationIssue("address", "INVALID_ADDRESS_FORMAT", "La dirección no cumple el formato esperado.", address))
        address_format_valid = False

    if address and address_format_valid and reference:
        address_city = address.rsplit(",", 1)[-1]
        if normalize_comparison_text(address_city) != normalize_comparison_text(reference.get("city")):
            issues.append(
                ValidationIssue(
                    "address",
                    "ADDRESS_CITY_MISMATCH",
                    "La ciudad de la dirección no coincide con el punto geográfico de referencia.",
                    {"address_city": address_city.strip(), "reference_city": reference.get("city")},
                )
            )

    latitude = _coordinate_value(payload, ["latitud", "latitude", "lat"], "latitude", -90, 90, issues)
    longitude = _coordinate_value(payload, ["longitud", "longitude", "lon", "lng"], "longitude", -180, 180, issues)

    first_piece_weight = None
    found_pieces, pieces_raw, _ = get_alias(payload, ["piezas", "pieces", "items", "elements"])
    if found_pieces and not is_missing(pieces_raw):
        if not isinstance(pieces_raw, list):
            issues.append(ValidationIssue("piezas", "INVALID_PIECES", "El campo de piezas debe ser una lista.", pieces_raw))
        elif pieces_raw:
            first_piece = pieces_raw[0]
            if isinstance(first_piece, Mapping):
                found_weight, weight_raw, _ = get_alias(first_piece, ["peso", "weight"])
                if found_weight and not is_missing(weight_raw):
                    first_piece_weight = to_decimal(weight_raw)
                    if first_piece_weight is None or first_piece_weight < 0:
                        issues.append(ValidationIssue("peso", "INVALID_WEIGHT", "El peso del primer elemento debe ser numérico y no negativo.", weight_raw))
            else:
                issues.append(ValidationIssue("piezas[0]", "INVALID_PIECE", "El primer elemento de piezas debe ser un objeto.", first_piece))

    payload_fields_valid = all(value is not None for value in (point_id, address, latitude, longitude))
    if not payload_fields_valid or any(issue.field in {"payload", "idPunto", "address", "latitude", "longitude", "piezas", "piezas[0]", "peso"} for issue in issues):
        return None
    return PayloadCandidate(
        raw_payload=payload,
        point_id=point_id,
        address=address,
        latitude=latitude,
        longitude=longitude,
        first_piece_weight=first_piece_weight,
    )


def _coordinate_value(
    payload: Mapping[str, Any],
    aliases: list[str],
    field_name: str,
    minimum: int,
    maximum: int,
    issues: list[ValidationIssue],
) -> Decimal | None:
    found, raw_value, _ = get_alias(payload, aliases)
    if not found or is_missing(raw_value):
        issues.append(ValidationIssue(field_name, "MISSING_COORDINATE", f"La coordenada {field_name} es obligatoria.", raw_value))
        return None
    value = to_decimal(raw_value)
    if value is None:
        issues.append(ValidationIssue(field_name, "INVALID_COORDINATE", f"La coordenada {field_name} debe ser numérica.", raw_value))
        return None
    if value < minimum or value > maximum:
        issues.append(ValidationIssue(field_name, "COORDINATE_OUT_OF_RANGE", f"La coordenada {field_name} está fuera del rango permitido.", raw_value))
        return None
    return value

