from django.urls import path

from .api.views import (
    RouteDetailView,
    RouteExecuteView,
    RouteImportView,
    RouteListCreateView,
    RouteLogsView,
)
from .views import health_check

urlpatterns = [
    path("health/", health_check, name="health-check"),
    path("routes/", RouteListCreateView.as_view(), name="route-list-create"),
    path("routes/import/", RouteImportView.as_view(), name="route-import"),
    path("routes/execute/", RouteExecuteView.as_view(), name="route-execute"),
    path("routes/<int:pk>/", RouteDetailView.as_view(), name="route-detail"),
    path("routes/<int:pk>/logs/", RouteLogsView.as_view(), name="route-logs"),
]
