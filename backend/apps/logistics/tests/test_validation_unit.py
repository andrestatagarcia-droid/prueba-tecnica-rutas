import json
import unittest

from apps.logistics.services.validation import validate_route_record


class RouteValidationUnitTests(unittest.TestCase):
    def setUp(self):
        self.route = {
            "idRoute": 900001,
            "idOficinaOrigen": 1,
            "fechaRegistro": "2026-01-02T08:00:00",
            "origin": "Cll 1 #2-3, Bogotá",
            "destination": "Cll 4 #5-6, Bogotá",
            "distance_km": 5.25,
            "priority": 1,
            "time_window_start": "2026-01-02T09:00:00",
            "time_window_end": "2026-01-02T11:00:00",
            "status": "READY",
            "created_at": "2026-01-02T08:00:00",
        }
        self.payload = json.dumps(
            {
                "idPunto": 100001,
                "address": "Cll 10 #20-30, Bogotá",
                "lat": "4.710989",
                "lon": "-74.072092",
                "piezas": [{"peso": 4.5}],
            }
        )
        self.points = {
            100001: {
                "id": 100001,
                "city": "Bogotá",
                "latitude_reference": 4.711,
                "longitude_reference": -74.072,
            }
        }

    def validate(self, route=None, payload=None):
        return validate_route_record(
            route or self.route,
            self.payload if payload is None else payload,
            office_ids={1},
            priority_ids={1},
            geographic_points=self.points,
            seen_source_ids=set(),
            seen_business_keys=set(),
        )

    def test_accepts_aliases_and_numeric_strings(self):
        result = self.validate()
        self.assertTrue(result.is_valid)
        self.assertEqual(str(result.payload.latitude), "4.710989")
        self.assertEqual(str(result.payload.first_piece_weight), "4.5")

    def test_rejects_inverted_time_window(self):
        route = dict(self.route)
        route["time_window_end"] = route["time_window_start"]
        result = self.validate(route=route)
        self.assertIn("INVALID_TIME_WINDOW", {issue.code for issue in result.issues})

    def test_rejects_non_numeric_coordinate(self):
        payload = json.dumps(
            {
                "idPunto": 100001,
                "direccion": "Cll 10 #20-30, Bogotá",
                "latitud": "no_num",
                "longitud": -74.07,
            }
        )
        result = self.validate(payload=payload)
        self.assertIn("INVALID_COORDINATE", {issue.code for issue in result.issues})

    def test_rejects_coordinate_out_of_range(self):
        payload = json.dumps(
            {
                "idPunto": 100001,
                "direccion": "Cll 10 #20-30, Bogotá",
                "latitud": 120,
                "longitud": -200,
            }
        )
        result = self.validate(payload=payload)
        self.assertEqual(
            sum(issue.code == "COORDINATE_OUT_OF_RANGE" for issue in result.issues),
            2,
        )

    def test_rejects_city_mismatch(self):
        payload = json.dumps(
            {
                "idPunto": 100001,
                "direccion": "Cll 10 #20-30, Cali",
                "latitud": 4.71,
                "longitud": -74.07,
            }
        )
        result = self.validate(payload=payload)
        self.assertIn("ADDRESS_CITY_MISMATCH", {issue.code for issue in result.issues})

    def test_allows_payload_without_pieces(self):
        payload = json.dumps(
            {
                "idPunto": 100001,
                "direccion": "Cll 10 #20-30, Bogotá",
                "latitud": 4.71,
                "longitud": -74.07,
            }
        )
        result = self.validate(payload=payload)
        self.assertTrue(result.is_valid)
        self.assertIsNone(result.payload.first_piece_weight)


if __name__ == "__main__":
    unittest.main()

