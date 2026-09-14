import uuid

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class Office(models.Model):
    id = models.PositiveIntegerField(primary_key=True)
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        db_table = "offices"
        ordering = ["id"]

    def __str__(self) -> str:
        return f"{self.id} - {self.name}"


class Priority(models.Model):
    id = models.PositiveIntegerField(primary_key=True)
    name = models.CharField(max_length=20, unique=True)

    class Meta:
        db_table = "priorities"
        ordering = ["id"]
        constraints = [
            models.CheckConstraint(condition=Q(id__gt=0), name="priority_id_positive"),
        ]

    def __str__(self) -> str:
        return f"{self.id} - {self.name}"


class GeographicPoint(models.Model):
    id = models.BigIntegerField(primary_key=True)
    city = models.CharField(max_length=100)
    latitude_reference = models.DecimalField(max_digits=9, decimal_places=6)
    longitude_reference = models.DecimalField(max_digits=9, decimal_places=6)

    class Meta:
        db_table = "geographic_points"
        ordering = ["id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(latitude_reference__gte=-90) & Q(latitude_reference__lte=90),
                name="geo_point_latitude_range",
            ),
            models.CheckConstraint(
                condition=Q(longitude_reference__gte=-180) & Q(longitude_reference__lte=180),
                name="geo_point_longitude_range",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.id} - {self.city}"


class ImportBatch(models.Model):
    class Status(models.TextChoices):
        PROCESSING = "PROCESSING", _("Procesando")
        COMPLETED = "COMPLETED", _("Completado")
        FAILED = "FAILED", _("Fallido")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file_name = models.CharField(max_length=255)
    file_checksum = models.CharField(max_length=64, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PROCESSING)
    total_rows = models.PositiveIntegerField(default=0)
    imported_rows = models.PositiveIntegerField(default=0)
    rejected_rows = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "import_batches"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.file_name} - {self.status}"


class Route(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", _("Pendiente")
        READY = "READY", _("Lista")
        EXECUTED = "EXECUTED", _("Ejecutada")
        FAILED = "FAILED", _("Fallida")

    source_id = models.BigIntegerField(null=True, blank=True, unique=True)
    origin_office = models.ForeignKey(Office, on_delete=models.PROTECT, related_name="routes")
    registered_at = models.DateTimeField(default=timezone.now)
    origin = models.CharField(max_length=255)
    destination = models.CharField(max_length=255)
    distance_km = models.DecimalField(max_digits=10, decimal_places=2)
    priority = models.ForeignKey(Priority, on_delete=models.PROTECT, related_name="routes")
    time_window_start = models.DateTimeField()
    time_window_end = models.DateTimeField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(default=timezone.now)
    import_batch = models.ForeignKey(
        ImportBatch,
        on_delete=models.SET_NULL,
        related_name="routes",
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "routes"
        ordering = ["-created_at", "id"]
        indexes = [
            models.Index(fields=["status"], name="route_status_idx"),
            models.Index(fields=["priority"], name="route_priority_idx"),
            models.Index(fields=["registered_at"], name="route_registered_idx"),
        ]
        constraints = [
            models.CheckConstraint(condition=Q(distance_km__gt=0), name="route_distance_positive"),
            models.CheckConstraint(
                condition=Q(time_window_start__lt=F("time_window_end")),
                name="route_valid_time_window",
            ),
            models.UniqueConstraint(
                fields=["origin", "destination", "time_window_start", "time_window_end"],
                name="route_exact_business_key_unique",
            ),
        ]

    def __str__(self) -> str:
        return f"Ruta {self.id}: {self.origin} → {self.destination}"


class RoutePayload(models.Model):
    route = models.OneToOneField(Route, on_delete=models.CASCADE, primary_key=True, related_name="payload")
    raw_payload = models.JSONField()
    point = models.ForeignKey(GeographicPoint, on_delete=models.PROTECT, related_name="route_payloads")
    address = models.CharField(max_length=255)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    first_piece_weight = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    class Meta:
        db_table = "route_payloads"
        constraints = [
            models.CheckConstraint(
                condition=Q(latitude__gte=-90) & Q(latitude__lte=90),
                name="route_payload_latitude_range",
            ),
            models.CheckConstraint(
                condition=Q(longitude__gte=-180) & Q(longitude__lte=180),
                name="route_payload_longitude_range",
            ),
            models.CheckConstraint(
                condition=Q(first_piece_weight__isnull=True) | Q(first_piece_weight__gte=0),
                name="route_payload_weight_nonnegative",
            ),
        ]

    def __str__(self) -> str:
        return f"Payload de ruta {self.route_id}"


class ExecutionLog(models.Model):
    class Result(models.TextChoices):
        SUCCESS = "SUCCESS", _("Exitosa")
        ERROR = "ERROR", _("Error")

    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name="execution_logs")
    execution_time = models.DateTimeField(default=timezone.now)
    result = models.CharField(max_length=20, choices=Result.choices)
    message = models.TextField()

    class Meta:
        db_table = "execution_logs"
        ordering = ["-execution_time", "-id"]
        indexes = [
            models.Index(fields=["route", "-execution_time"], name="execution_route_time_idx"),
        ]

    def __str__(self) -> str:
        return f"Ruta {self.route_id} - {self.result}"


class ImportIssue(models.Model):
    batch = models.ForeignKey(ImportBatch, on_delete=models.CASCADE, related_name="issues")
    row_number = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    route_source_id = models.BigIntegerField(null=True, blank=True)
    field = models.CharField(max_length=100)
    code = models.CharField(max_length=80)
    message = models.TextField()
    raw_value = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = "import_issues"
        ordering = ["row_number", "id"]
        indexes = [
            models.Index(fields=["batch", "row_number"], name="issue_batch_row_idx"),
            models.Index(fields=["code"], name="issue_code_idx"),
        ]

    def __str__(self) -> str:
        return f"Fila {self.row_number} - {self.code}"
