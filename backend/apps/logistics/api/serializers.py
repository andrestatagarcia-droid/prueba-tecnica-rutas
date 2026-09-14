from pathlib import Path
from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from apps.logistics.models import (
    ExecutionLog,
    GeographicPoint,
    Office,
    Priority,
    Route,
    RoutePayload,
)
from apps.logistics.services.normalization import normalize_comparison_text, normalize_spaces
from apps.logistics.services.validation import ADDRESS_PATTERN


MAX_FILE_SIZE_BYTES = 15 * 1024 * 1024


class RouteImportUploadSerializer(serializers.Serializer):
    file = serializers.FileField()

    def validate_file(self, uploaded_file):
        if Path(uploaded_file.name).suffix.lower() != ".xlsx":
            raise serializers.ValidationError("El archivo debe tener extensión .xlsx.")
        if uploaded_file.size > MAX_FILE_SIZE_BYTES:
            raise serializers.ValidationError("El archivo supera el límite de 15 MB.")
        return uploaded_file


class RoutePayloadWriteSerializer(serializers.Serializer):
    point = serializers.PrimaryKeyRelatedField(queryset=GeographicPoint.objects.all())
    address = serializers.CharField(max_length=255)
    latitude = serializers.DecimalField(
        max_digits=9,
        decimal_places=6,
        min_value=Decimal("-90"),
        max_value=Decimal("90"),
    )
    longitude = serializers.DecimalField(
        max_digits=9,
        decimal_places=6,
        min_value=Decimal("-180"),
        max_value=Decimal("180"),
    )
    first_piece_weight = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("0"),
        allow_null=True,
        required=False,
    )
    raw_payload = serializers.JSONField(required=False, default=dict)

    def validate_address(self, value):
        normalized = normalize_spaces(value)
        if normalized is None or not ADDRESS_PATTERN.fullmatch(normalized):
            raise serializers.ValidationError(
                "La dirección no cumple el formato esperado, por ejemplo: Cll 10 # 20-30, Bogotá."
            )
        return normalized

    def validate(self, attrs):
        point = attrs.get("point")
        address = attrs.get("address")
        if point is not None and address is not None:
            address_city = address.rsplit(",", 1)[-1]
            if normalize_comparison_text(address_city) != normalize_comparison_text(point.city):
                raise serializers.ValidationError(
                    {"address": "La ciudad de la dirección no coincide con el punto geográfico."}
                )
        return attrs


class RouteCreateSerializer(serializers.ModelSerializer):
    origin_office = serializers.PrimaryKeyRelatedField(queryset=Office.objects.all())
    priority = serializers.PrimaryKeyRelatedField(queryset=Priority.objects.all())
    registered_at = serializers.DateTimeField(required=False, default=timezone.now)
    status = serializers.ChoiceField(
        choices=(Route.Status.PENDING, Route.Status.READY),
        required=False,
        default=Route.Status.PENDING,
    )
    payload = RoutePayloadWriteSerializer()

    class Meta:
        model = Route
        fields = (
            "origin_office",
            "registered_at",
            "origin",
            "destination",
            "distance_km",
            "priority",
            "time_window_start",
            "time_window_end",
            "status",
            "payload",
        )
        extra_kwargs = {
            "origin": {"allow_blank": False},
            "destination": {"allow_blank": False},
            "distance_km": {"min_value": Decimal("0.01")},
        }

    def validate(self, attrs):
        start = attrs.get("time_window_start")
        end = attrs.get("time_window_end")
        if start is not None and end is not None and start >= end:
            raise serializers.ValidationError(
                {"time_window_end": "La fecha final debe ser posterior a la fecha inicial."}
            )

        origin = normalize_spaces(attrs.get("origin"))
        destination = normalize_spaces(attrs.get("destination"))
        attrs["origin"] = origin
        attrs["destination"] = destination
        if all(value is not None for value in (origin, destination, start, end)):
            duplicate = Route.objects.filter(
                origin=origin,
                destination=destination,
                time_window_start=start,
                time_window_end=end,
            ).exists()
            if duplicate:
                raise serializers.ValidationError(
                    {"route": "Ya existe una ruta con el mismo origen, destino y ventana de tiempo."}
                )
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        payload_data = validated_data.pop("payload")
        route = Route.objects.create(**validated_data)
        RoutePayload.objects.create(route=route, **payload_data)
        return route


class RoutePayloadReadSerializer(serializers.ModelSerializer):
    point = serializers.IntegerField(source="point_id")
    point_city = serializers.CharField(source="point.city")

    class Meta:
        model = RoutePayload
        fields = (
            "point",
            "point_city",
            "address",
            "latitude",
            "longitude",
            "first_piece_weight",
            "raw_payload",
        )


class RouteReadSerializer(serializers.ModelSerializer):
    origin_office = serializers.IntegerField(source="origin_office_id")
    origin_office_name = serializers.CharField(source="origin_office.name")
    priority = serializers.IntegerField(source="priority_id")
    priority_name = serializers.CharField(source="priority.name")
    payload = RoutePayloadReadSerializer()

    class Meta:
        model = Route
        fields = (
            "id",
            "source_id",
            "origin_office",
            "origin_office_name",
            "registered_at",
            "origin",
            "destination",
            "distance_km",
            "priority",
            "priority_name",
            "time_window_start",
            "time_window_end",
            "status",
            "created_at",
            "payload",
        )


class RouteExecutionRequestSerializer(serializers.Serializer):
    route_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=False,
        max_length=100,
    )

    def validate_route_ids(self, value):
        if len(value) != len(set(value)):
            raise serializers.ValidationError("Los identificadores de ruta no pueden repetirse.")
        return value


class ExecutionLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExecutionLog
        fields = ("id", "route", "execution_time", "result", "message")
