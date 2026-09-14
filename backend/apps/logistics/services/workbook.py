from collections import defaultdict
from io import BytesIO
from typing import Any

import pandas as pd

from .normalization import normalize_spaces, to_decimal, to_integer


REQUIRED_SHEETS = {
    "oficina_org": {"idOficina", "NombreOficinaOrigen"},
    "priorities_ref": {"priority", "priority_name"},
    "poblacion_cor": {"idPunto", "ciudad", "lat_ref", "lon_ref"},
    "routes": {
        "idRoute",
        "idOficinaOrigen",
        "fechaRegistro",
        "origin",
        "destination",
        "distance_km",
        "priority",
        "time_window_start",
        "time_window_end",
        "status",
        "created_at",
    },
    "route_payload": {"idRoute", "payload"},
    "execution_logs": {"id", "route_id", "execution_time", "result", "message"},
}


class WorkbookStructureError(ValueError):
    pass


def read_workbook(content: bytes) -> dict[str, pd.DataFrame]:
    try:
        frames = pd.read_excel(BytesIO(content), sheet_name=None, engine="openpyxl")
    except Exception as exc:
        raise WorkbookStructureError(f"No fue posible leer el archivo Excel: {exc}") from exc

    missing_sheets = sorted(set(REQUIRED_SHEETS) - set(frames))
    if missing_sheets:
        raise WorkbookStructureError(f"Faltan hojas obligatorias: {', '.join(missing_sheets)}.")

    for sheet_name, required_columns in REQUIRED_SHEETS.items():
        frames[sheet_name].columns = [str(column).strip() for column in frames[sheet_name].columns]
        missing_columns = sorted(required_columns - set(frames[sheet_name].columns))
        if missing_columns:
            raise WorkbookStructureError(
                f"La hoja {sheet_name} no contiene las columnas: {', '.join(missing_columns)}."
            )
    return frames


def frame_records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    return frame.to_dict(orient="records")


def extract_reference_data(
    frames: dict[str, pd.DataFrame],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    offices: list[dict[str, Any]] = []
    priorities: list[dict[str, Any]] = []
    points: list[dict[str, Any]] = []

    seen_offices: set[int] = set()
    for row_number, row in enumerate(frame_records(frames["oficina_org"]), start=2):
        office_id = to_integer(row.get("idOficina"))
        name = normalize_spaces(row.get("NombreOficinaOrigen"))
        if office_id is None or office_id <= 0 or name is None:
            raise WorkbookStructureError(f"Referencia de oficina inválida en la fila {row_number}.")
        if office_id in seen_offices:
            raise WorkbookStructureError(f"Oficina duplicada en la fila {row_number}: {office_id}.")
        seen_offices.add(office_id)
        offices.append({"id": office_id, "name": name})

    seen_priorities: set[int] = set()
    for row_number, row in enumerate(frame_records(frames["priorities_ref"]), start=2):
        priority_id = to_integer(row.get("priority"))
        name = normalize_spaces(row.get("priority_name"))
        if priority_id is None or priority_id <= 0 or name is None:
            raise WorkbookStructureError(f"Referencia de prioridad inválida en la fila {row_number}.")
        if priority_id in seen_priorities:
            raise WorkbookStructureError(f"Prioridad duplicada en la fila {row_number}: {priority_id}.")
        seen_priorities.add(priority_id)
        priorities.append({"id": priority_id, "name": name})

    seen_points: set[int] = set()
    for row_number, row in enumerate(frame_records(frames["poblacion_cor"]), start=2):
        point_id = to_integer(row.get("idPunto"))
        city = normalize_spaces(row.get("ciudad"))
        latitude = to_decimal(row.get("lat_ref"))
        longitude = to_decimal(row.get("lon_ref"))
        valid_coordinates = (
            latitude is not None
            and longitude is not None
            and -90 <= latitude <= 90
            and -180 <= longitude <= 180
        )
        if point_id is None or point_id <= 0 or city is None or not valid_coordinates:
            raise WorkbookStructureError(f"Punto geográfico inválido en la fila {row_number}.")
        if point_id in seen_points:
            raise WorkbookStructureError(f"Punto geográfico duplicado en la fila {row_number}: {point_id}.")
        seen_points.add(point_id)
        points.append(
            {
                "id": point_id,
                "city": city,
                "latitude_reference": latitude,
                "longitude_reference": longitude,
            }
        )
    return offices, priorities, points


def build_payload_groups(frame: pd.DataFrame) -> dict[int, list[Any]]:
    payloads: dict[int, list[Any]] = defaultdict(list)
    for row in frame_records(frame):
        route_id = to_integer(row.get("idRoute"))
        if route_id is not None:
            payloads[route_id].append(row.get("payload"))
    return dict(payloads)

