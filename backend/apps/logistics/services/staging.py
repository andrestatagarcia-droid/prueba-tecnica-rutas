from datetime import date, datetime
from typing import Any

from django.db import connection

from .normalization import is_missing


STAGING_DEFINITIONS = {
    "oficina_org": [
        ("id_oficina", "idOficina"),
        ("nombre_oficina_origen", "NombreOficinaOrigen"),
    ],
    "priorities_ref": [
        ("priority", "priority"),
        ("priority_name", "priority_name"),
    ],
    "poblacion_cor": [
        ("id_punto", "idPunto"),
        ("ciudad", "ciudad"),
        ("lat_ref", "lat_ref"),
        ("lon_ref", "lon_ref"),
    ],
    "routes": [
        ("id_route", "idRoute"),
        ("id_oficina_origen", "idOficinaOrigen"),
        ("fecha_registro", "fechaRegistro"),
        ("origin", "origin"),
        ("destination", "destination"),
        ("distance_km", "distance_km"),
        ("priority", "priority"),
        ("time_window_start", "time_window_start"),
        ("time_window_end", "time_window_end"),
        ("status", "status"),
        ("created_at", "created_at"),
    ],
    "route_payload": [
        ("id_route", "idRoute"),
        ("payload", "payload"),
    ],
    "execution_logs": [
        ("id", "id"),
        ("route_id", "route_id"),
        ("execution_time", "execution_time"),
        ("result", "result"),
        ("message", "message"),
    ],
}


def _raw_text(value: Any) -> str | None:
    if is_missing(value):
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if hasattr(value, "to_pydatetime"):
        return value.to_pydatetime().isoformat()
    if hasattr(value, "item"):
        try:
            value = value.item()
        except (TypeError, ValueError):
            pass
    return str(value)


def write_staging_tables(batch_id, frames) -> None:
    with connection.cursor() as cursor:
        for sheet_name, columns in STAGING_DEFINITIONS.items():
            database_columns = [column[0] for column in columns]
            source_columns = [column[1] for column in columns]
            column_sql = ", ".join(["import_batch_id", "source_row", *database_columns])
            placeholders = ", ".join(["%s"] * (2 + len(columns)))
            insert_sql = f"INSERT INTO staging.{sheet_name} ({column_sql}) VALUES ({placeholders})"
            rows = []
            for source_row, record in enumerate(frames[sheet_name].to_dict(orient="records"), start=2):
                rows.append(
                    (
                        str(batch_id),
                        source_row,
                        *[_raw_text(record.get(source_column)) for source_column in source_columns],
                    )
                )
            cursor.executemany(insert_sql, rows)

