from datetime import timedelta
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from apps.logistics.models import Office, Priority, Route


class RouteModelTests(TestCase):
    def setUp(self):
        self.office = Office.objects.create(id=1, name="BOG-TEST")
        self.priority = Priority.objects.create(id=1, name="P0001")

    def route_data(self):
        start = timezone.now()
        return {
            "origin_office": self.office,
            "origin": "Cll 1 # 2-3, Bogotá",
            "destination": "Cll 4 # 5-6, Bogotá",
            "distance_km": Decimal("5.25"),
            "priority": self.priority,
            "time_window_start": start,
            "time_window_end": start + timedelta(hours=2),
            "status": Route.Status.READY,
        }

    def test_creates_valid_route(self):
        route = Route.objects.create(**self.route_data())
        self.assertEqual(route.status, Route.Status.READY)

    def test_database_rejects_non_positive_distance(self):
        data = self.route_data()
        data["distance_km"] = Decimal("0")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Route.objects.create(**data)

    def test_database_rejects_invalid_time_window(self):
        data = self.route_data()
        data["time_window_end"] = data["time_window_start"]
        with self.assertRaises(IntegrityError), transaction.atomic():
            Route.objects.create(**data)

