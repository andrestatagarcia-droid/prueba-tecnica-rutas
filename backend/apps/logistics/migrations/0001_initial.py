import uuid

import django.core.validators
import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="GeographicPoint",
            fields=[
                ("id", models.BigIntegerField(primary_key=True, serialize=False)),
                ("city", models.CharField(max_length=100)),
                ("latitude_reference", models.DecimalField(decimal_places=6, max_digits=9)),
                ("longitude_reference", models.DecimalField(decimal_places=6, max_digits=9)),
            ],
            options={"db_table": "geographic_points", "ordering": ["id"]},
        ),
        migrations.CreateModel(
            name="ImportBatch",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("file_name", models.CharField(max_length=255)),
                ("file_checksum", models.CharField(blank=True, max_length=64)),
                ("status", models.CharField(choices=[("PROCESSING", "Procesando"), ("COMPLETED", "Completado"), ("FAILED", "Fallido")], default="PROCESSING", max_length=20)),
                ("total_rows", models.PositiveIntegerField(default=0)),
                ("imported_rows", models.PositiveIntegerField(default=0)),
                ("rejected_rows", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
            ],
            options={"db_table": "import_batches", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="Office",
            fields=[
                ("id", models.PositiveIntegerField(primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=100, unique=True)),
            ],
            options={"db_table": "offices", "ordering": ["id"]},
        ),
        migrations.CreateModel(
            name="Priority",
            fields=[
                ("id", models.PositiveIntegerField(primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=20, unique=True)),
            ],
            options={"db_table": "priorities", "ordering": ["id"]},
        ),
        migrations.AddConstraint(
            model_name="geographicpoint",
            constraint=models.CheckConstraint(condition=models.Q(("latitude_reference__gte", -90), ("latitude_reference__lte", 90)), name="geo_point_latitude_range"),
        ),
        migrations.AddConstraint(
            model_name="geographicpoint",
            constraint=models.CheckConstraint(condition=models.Q(("longitude_reference__gte", -180), ("longitude_reference__lte", 180)), name="geo_point_longitude_range"),
        ),
        migrations.AddConstraint(
            model_name="priority",
            constraint=models.CheckConstraint(condition=models.Q(("id__gt", 0)), name="priority_id_positive"),
        ),
        migrations.CreateModel(
            name="Route",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("source_id", models.BigIntegerField(blank=True, null=True, unique=True)),
                ("registered_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("origin", models.CharField(max_length=255)),
                ("destination", models.CharField(max_length=255)),
                ("distance_km", models.DecimalField(decimal_places=2, max_digits=10)),
                ("time_window_start", models.DateTimeField()),
                ("time_window_end", models.DateTimeField()),
                ("status", models.CharField(choices=[("PENDING", "Pendiente"), ("READY", "Lista"), ("EXECUTED", "Ejecutada"), ("FAILED", "Fallida")], default="PENDING", max_length=20)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("import_batch", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="routes", to="logistics.importbatch")),
                ("origin_office", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="routes", to="logistics.office")),
                ("priority", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="routes", to="logistics.priority")),
            ],
            options={
                "db_table": "routes",
                "ordering": ["-created_at", "id"],
                "indexes": [
                    models.Index(fields=["status"], name="route_status_idx"),
                    models.Index(fields=["priority"], name="route_priority_idx"),
                    models.Index(fields=["registered_at"], name="route_registered_idx"),
                ],
            },
        ),
        migrations.AddConstraint(
            model_name="route",
            constraint=models.CheckConstraint(condition=models.Q(("distance_km__gt", 0)), name="route_distance_positive"),
        ),
        migrations.AddConstraint(
            model_name="route",
            constraint=models.CheckConstraint(condition=models.Q(("time_window_start__lt", models.F("time_window_end"))), name="route_valid_time_window"),
        ),
        migrations.AddConstraint(
            model_name="route",
            constraint=models.UniqueConstraint(fields=("origin", "destination", "time_window_start", "time_window_end"), name="route_exact_business_key_unique"),
        ),
        migrations.CreateModel(
            name="RoutePayload",
            fields=[
                ("route", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, related_name="payload", serialize=False, to="logistics.route")),
                ("raw_payload", models.JSONField()),
                ("address", models.CharField(max_length=255)),
                ("latitude", models.DecimalField(decimal_places=6, max_digits=9)),
                ("longitude", models.DecimalField(decimal_places=6, max_digits=9)),
                ("first_piece_weight", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ("point", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="route_payloads", to="logistics.geographicpoint")),
            ],
            options={"db_table": "route_payloads"},
        ),
        migrations.AddConstraint(
            model_name="routepayload",
            constraint=models.CheckConstraint(condition=models.Q(("latitude__gte", -90), ("latitude__lte", 90)), name="route_payload_latitude_range"),
        ),
        migrations.AddConstraint(
            model_name="routepayload",
            constraint=models.CheckConstraint(condition=models.Q(("longitude__gte", -180), ("longitude__lte", 180)), name="route_payload_longitude_range"),
        ),
        migrations.AddConstraint(
            model_name="routepayload",
            constraint=models.CheckConstraint(condition=models.Q(("first_piece_weight__isnull", True), ("first_piece_weight__gte", 0), _connector="OR"), name="route_payload_weight_nonnegative"),
        ),
        migrations.CreateModel(
            name="ExecutionLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("execution_time", models.DateTimeField(default=django.utils.timezone.now)),
                ("result", models.CharField(choices=[("SUCCESS", "Exitosa"), ("ERROR", "Error")], max_length=20)),
                ("message", models.TextField()),
                ("route", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="execution_logs", to="logistics.route")),
            ],
            options={
                "db_table": "execution_logs",
                "ordering": ["-execution_time", "-id"],
                "indexes": [models.Index(fields=["route", "-execution_time"], name="execution_route_time_idx")],
            },
        ),
        migrations.CreateModel(
            name="ImportIssue",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("row_number", models.PositiveIntegerField(validators=[django.core.validators.MinValueValidator(1)])),
                ("route_source_id", models.BigIntegerField(blank=True, null=True)),
                ("field", models.CharField(max_length=100)),
                ("code", models.CharField(max_length=80)),
                ("message", models.TextField()),
                ("raw_value", models.JSONField(blank=True, null=True)),
                ("batch", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="issues", to="logistics.importbatch")),
            ],
            options={
                "db_table": "import_issues",
                "ordering": ["row_number", "id"],
                "indexes": [
                    models.Index(fields=["batch", "row_number"], name="issue_batch_row_idx"),
                    models.Index(fields=["code"], name="issue_code_idx"),
                ],
            },
        ),
    ]
