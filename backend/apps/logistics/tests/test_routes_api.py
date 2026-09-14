from datetime import timedelta
from decimal import Decimal

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.logistics.models import (
    ExecutionLog,
    GeographicPoint,
    Office,
    Priority,
    Route,
    RoutePayload,
)


class RouteApiTests(APITestCase):
    def setUp(self):
        self.office = Office.objects.create(id=10, name="BOG-TEST")
        self.priority = Priority.objects.create(id=20, name="ALTA")
        self.point = GeographicPoint.objects.create(
            id=30,
            city="Bogotá",
            latitude_reference=Decimal("4.609710"),
            longitude_reference=Decimal("-74.081750"),
        )

    def route_request(self, *, route_status=Route.Status.READY, suffix="A"):
        start = (timezone.now() + timedelta(days=1)).replace(microsecond=0)
        return {
            "origin_office": self.office.id,
            "registered_at": timezone.now().replace(microsecond=0).isoformat(),
            "origin": f"Bodega {suffix}",
            "destination": f"Cliente {suffix}",
            "distance_km": "12.50",
            "priority": self.priority.id,
            "time_window_start": start.isoformat(),
            "time_window_end": (start + timedelta(hours=2)).isoformat(),
            "status": route_status,
            "payload": {
                "point": self.point.id,
                "address": "Cll 10 # 20-30, Bogotá",
                "latitude": "4.609710",
                "longitude": "-74.081750",
                "first_piece_weight": "8.25",
                "raw_payload": {"source": "api-test"},
            },
        }

    def create_route(self, *, route_status=Route.Status.READY, suffix="A"):
        data = self.route_request(route_status=route_status, suffix=suffix)
        payload_data = data.pop("payload")
        route = Route.objects.create(
            origin_office=self.office,
            registered_at=data["registered_at"],
            origin=data["origin"],
            destination=data["destination"],
            distance_km=data["distance_km"],
            priority=self.priority,
            time_window_start=data["time_window_start"],
            time_window_end=data["time_window_end"],
            status=data["status"],
        )
        RoutePayload.objects.create(
            route=route,
            point=self.point,
            address=payload_data["address"],
            latitude=payload_data["latitude"],
            longitude=payload_data["longitude"],
            first_piece_weight=payload_data["first_piece_weight"],
            raw_payload=payload_data["raw_payload"],
        )
        return route

    def test_creates_route_with_nested_payload(self):
        response = self.client.post(
            reverse("route-list-create"),
            self.route_request(),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Route.objects.count(), 1)
        self.assertEqual(response.data["payload"]["point"], self.point.id)
        self.assertEqual(response.data["status"], Route.Status.READY)

    def test_rejects_invalid_time_window(self):
        data = self.route_request()
        data["time_window_end"] = data["time_window_start"]

        response = self.client.post(reverse("route-list-create"), data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("time_window_end", response.data)
        self.assertEqual(Route.objects.count(), 0)

    def test_rejects_address_city_mismatch(self):
        data = self.route_request()
        data["payload"]["address"] = "Cll 10 # 20-30, Medellín"

        response = self.client.post(reverse("route-list-create"), data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Route.objects.count(), 0)

    def test_lists_and_filters_routes(self):
        ready = self.create_route(route_status=Route.Status.READY, suffix="READY")
        self.create_route(route_status=Route.Status.PENDING, suffix="PENDING")

        response = self.client.get(
            reverse("route-list-create"),
            {"status": Route.Status.READY, "page_size": 10},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], ready.id)

    def test_returns_route_detail(self):
        route = self.create_route()

        response = self.client.get(reverse("route-detail", args=[route.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], route.id)
        self.assertEqual(response.data["origin_office_name"], self.office.name)

    def test_executes_ready_route_and_records_all_existing_attempts(self):
        ready = self.create_route(route_status=Route.Status.READY, suffix="READY")
        pending = self.create_route(route_status=Route.Status.PENDING, suffix="PENDING")
        missing_id = max(ready.id, pending.id) + 1000

        response = self.client.post(
            reverse("route-execute"),
            {"route_ids": [ready.id, pending.id, missing_id]},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["requested"], 3)
        self.assertEqual(response.data["executed"], 1)
        self.assertEqual(response.data["failed"], 2)
        ready.refresh_from_db()
        pending.refresh_from_db()
        self.assertEqual(ready.status, Route.Status.EXECUTED)
        self.assertEqual(pending.status, Route.Status.PENDING)
        self.assertEqual(ExecutionLog.objects.filter(route=ready).count(), 1)
        self.assertEqual(ExecutionLog.objects.filter(route=pending).count(), 1)
        self.assertFalse(ExecutionLog.objects.filter(route_id=missing_id).exists())

    def test_returns_paginated_route_logs(self):
        route = self.create_route()
        self.client.post(
            reverse("route-execute"),
            {"route_ids": [route.id]},
            format="json",
        )

        response = self.client.get(reverse("route-logs", args=[route.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["result"], ExecutionLog.Result.SUCCESS)

    def test_rejects_duplicate_execution_ids(self):
        route = self.create_route()

        response = self.client.post(
            reverse("route-execute"),
            {"route_ids": [route.id, route.id]},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(ExecutionLog.objects.count(), 0)
