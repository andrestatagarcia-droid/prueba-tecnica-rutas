from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework import filters as drf_filters
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView, ListCreateAPIView, RetrieveAPIView
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.logistics.models import ExecutionLog, Route
from apps.logistics.services.execution import RouteExecutionService
from apps.logistics.services.importer import ImportServiceError, RouteImportService

from .filters import RouteFilter
from .pagination import StandardPageNumberPagination
from .serializers import (
    ExecutionLogSerializer,
    RouteCreateSerializer,
    RouteExecutionRequestSerializer,
    RouteImportUploadSerializer,
    RouteReadSerializer,
)


class RouteImportView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = RouteImportUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            summary = RouteImportService.import_uploaded_file(serializer.validated_data["file"])
        except ImportServiceError as exc:
            return Response(
                {
                    "batch_id": str(exc.batch_id) if exc.batch_id else None,
                    "status": "FAILED",
                    "message": str(exc),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(summary.as_dict(), status=status.HTTP_201_CREATED)


class RouteListCreateView(ListCreateAPIView):
    queryset = Route.objects.select_related(
        "origin_office",
        "priority",
        "payload",
        "payload__point",
    ).all()
    filter_backends = (
        DjangoFilterBackend,
        drf_filters.SearchFilter,
        drf_filters.OrderingFilter,
    )
    filterset_class = RouteFilter
    search_fields = ("origin", "destination", "payload__address")
    ordering_fields = ("registered_at", "created_at", "distance_km", "priority")
    ordering = ("-created_at", "id")
    pagination_class = StandardPageNumberPagination

    def get_serializer_class(self):
        if self.request.method == "POST":
            return RouteCreateSerializer
        return RouteReadSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            route = serializer.save()
        except IntegrityError as exc:
            raise ValidationError(
                {"route": "La ruta viola una restricción de integridad o ya existe."}
            ) from exc
        route = self.get_queryset().get(pk=route.pk)
        return Response(RouteReadSerializer(route).data, status=status.HTTP_201_CREATED)


class RouteDetailView(RetrieveAPIView):
    queryset = RouteListCreateView.queryset
    serializer_class = RouteReadSerializer


class RouteExecuteView(APIView):
    def post(self, request):
        serializer = RouteExecutionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        summary = RouteExecutionService.execute(serializer.validated_data["route_ids"])
        return Response(summary.as_dict(), status=status.HTTP_200_OK)


class RouteLogsView(ListAPIView):
    serializer_class = ExecutionLogSerializer
    pagination_class = StandardPageNumberPagination

    def get_queryset(self):
        route = get_object_or_404(Route.objects.only("id"), pk=self.kwargs["pk"])
        return ExecutionLog.objects.filter(route=route)
