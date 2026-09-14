#!/usr/bin/env python3
import json
import math
import re
import sys
import unicodedata
from pathlib import Path

import pandas as pd


ADDRESS_PATTERN = re.compile(
    r"^(?:cll|calle|cra|carrera|av|avenida|dg|diagonal|tv|transversal)\s+"
    r"\d+[a-z]?\s*#\s*\d+[a-z]?\s*-\s*\d+\s*,\s*[\wáéíóúüñ .-]+$",
    re.IGNORECASE,
)
ALLOWED_STATUSES = {"PENDING", "READY", "EXECUTED", "FAILED"}
EARTH_RADIUS_KM = 6371.0088


def get_alias(payload, names):
    for name in names:
        if name in payload:
            return payload[name]
    return None


def number(value):
    if value is None:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def normalized_text(value):
    text = "" if value is None else re.sub(r"\s+", " ", str(value)).strip().lower()
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(char for char in decomposed if unicodedata.category(char) != "Mn")


def haversine(latitude, longitude, reference_latitude, reference_longitude):
    lat_1 = math.radians(latitude)
    lat_2 = math.radians(reference_latitude)
    delta_lat = math.radians(reference_latitude - latitude)
    delta_lon = math.radians(reference_longitude - longitude)
    haversine_value = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat_1) * math.cos(lat_2) * math.sin(delta_lon / 2) ** 2
    )
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(min(1, haversine_value)))


def main():
    dataset = Path(sys.argv[1] if len(sys.argv) > 1 else "data/dataset.xlsx")
    sheets = pd.read_excel(dataset, sheet_name=None)
    routes = sheets["routes"]
    payload_rows = sheets["route_payload"]
    logs = sheets["execution_logs"]

    offices = set(sheets["oficina_org"]["idOficina"].dropna().astype(int))
    priorities = set(sheets["priorities_ref"]["priority"].dropna().astype(int))
    points = sheets["poblacion_cor"].set_index("idPunto").to_dict(orient="index")
    payload_groups = {
        route_id: group["payload"].tolist()
        for route_id, group in payload_rows.groupby("idRoute", dropna=False)
    }
    duplicate_counts = routes.groupby(
        ["origin", "destination", "time_window_start", "time_window_end"],
        dropna=False,
    )["idRoute"].transform("size")

    counters = {
        "routes": len(routes),
        "invalid_time_windows": 0,
        "invalid_distances": 0,
        "invalid_coordinates": 0,
        "invalid_addresses": 0,
        "unknown_points": 0,
        "address_city_mismatches": 0,
        "invalid_payloads": 0,
        "unknown_offices": 0,
        "invalid_priorities": 0,
        "invalid_statuses": 0,
        "exact_duplicates": 0,
        "valid_routes": 0,
        "rejected_routes": 0,
    }
    geographic_distances = []
    distance_differences = []

    for position, (_, route) in enumerate(routes.iterrows()):
        route_id = route.get("idRoute")
        grouped_payloads = payload_groups.get(route_id, [])
        payload = None
        if len(grouped_payloads) == 1:
            raw_payload = grouped_payloads[0]
            try:
                payload = json.loads(raw_payload) if isinstance(raw_payload, str) else None
            except (json.JSONDecodeError, TypeError):
                payload = None

        invalid_payload = len(grouped_payloads) != 1 or not isinstance(payload, dict)
        payload = payload or {}
        point_id = get_alias(payload, ["idPunto", "id_punto", "pointId", "point_id"])
        address = get_alias(payload, ["direccion", "dirección", "address"])
        latitude = number(get_alias(payload, ["latitud", "latitude", "lat"]))
        longitude = number(get_alias(payload, ["longitud", "longitude", "lon", "lng"]))
        point = points.get(point_id)

        invalid_time_window = (
            pd.isna(route.get("time_window_start"))
            or pd.isna(route.get("time_window_end"))
            or route.get("time_window_start") >= route.get("time_window_end")
        )
        distance = number(route.get("distance_km"))
        invalid_distance = distance is None or distance <= 0
        invalid_coordinates = (
            latitude is None
            or longitude is None
            or not -90 <= latitude <= 90
            or not -180 <= longitude <= 180
        )
        valid_address = isinstance(address, str) and bool(ADDRESS_PATTERN.fullmatch(address.strip()))
        invalid_address = not valid_address
        unknown_point = point is None
        city_mismatch = False
        if valid_address and point is not None:
            city_mismatch = normalized_text(address.rsplit(",", 1)[-1]) != normalized_text(
                point.get("ciudad")
            )

        office_id = number(route.get("idOficinaOrigen"))
        priority_id = number(route.get("priority"))
        unknown_office = office_id is None or int(office_id) not in offices
        invalid_priority = (
            priority_id is None or priority_id <= 0 or int(priority_id) not in priorities
        )
        status = str(route.get("status")).strip().upper()
        invalid_status = status not in ALLOWED_STATUSES
        exact_duplicate = duplicate_counts.iloc[position] > 1

        flags = {
            "invalid_time_windows": invalid_time_window,
            "invalid_distances": invalid_distance,
            "invalid_coordinates": invalid_coordinates,
            "invalid_addresses": invalid_address,
            "unknown_points": unknown_point,
            "address_city_mismatches": city_mismatch,
            "invalid_payloads": invalid_payload,
            "unknown_offices": unknown_office,
            "invalid_priorities": invalid_priority,
            "invalid_statuses": invalid_status,
            "exact_duplicates": exact_duplicate,
        }
        for counter, active in flags.items():
            counters[counter] += int(active)

        rejected = any(flags.values())
        counters["rejected_routes"] += int(rejected)
        counters["valid_routes"] += int(not rejected)

        if not invalid_coordinates and point is not None:
            reference_latitude = number(point.get("lat_ref"))
            reference_longitude = number(point.get("lon_ref"))
            if (
                reference_latitude is not None
                and reference_longitude is not None
                and -90 <= reference_latitude <= 90
                and -180 <= reference_longitude <= 180
            ):
                geographic_distance = haversine(
                    latitude,
                    longitude,
                    reference_latitude,
                    reference_longitude,
                )
                geographic_distances.append(geographic_distance)
                if distance is not None:
                    distance_differences.append(abs(distance - geographic_distance))

    log_counts = logs.groupby("route_id").size()
    route_ids = set(routes["idRoute"].dropna())
    routes_with_logs = set(logs["route_id"].dropna())
    counters.update(
        {
            "logs": len(logs),
            "routes_with_logs": len(routes_with_logs),
            "routes_without_logs": len(route_ids - routes_with_logs),
            "routes_with_multiple_logs": int((log_counts > 1).sum()),
            "maximum_logs_per_route": int(log_counts.max()),
            "geographic_distances_computable": len(geographic_distances),
            "average_geographic_distance_km": round(
                sum(geographic_distances) / len(geographic_distances), 3
            ),
            "average_distance_difference_km": round(
                sum(distance_differences) / len(distance_differences), 3
            ),
        }
    )

    expected = {
        "routes": 5000,
        "invalid_time_windows": 152,
        "invalid_distances": 142,
        "invalid_coordinates": 314,
        "invalid_addresses": 229,
        "unknown_points": 135,
        "address_city_mismatches": 4017,
        "valid_routes": 658,
        "rejected_routes": 4342,
        "logs": 6434,
        "routes_with_logs": 3743,
        "routes_without_logs": 1257,
        "routes_with_multiple_logs": 1999,
        "maximum_logs_per_route": 3,
        "geographic_distances_computable": 4551,
    }
    mismatches = {
        key: {"expected": expected_value, "actual": counters.get(key)}
        for key, expected_value in expected.items()
        if counters.get(key) != expected_value
    }
    print(json.dumps({"dataset": str(dataset), **counters}, indent=2, ensure_ascii=False))
    if mismatches:
        print(json.dumps({"control_mismatches": mismatches}, indent=2, ensure_ascii=False))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
