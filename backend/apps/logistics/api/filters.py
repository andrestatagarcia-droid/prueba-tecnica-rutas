import django_filters

from apps.logistics.models import Route


class RouteFilter(django_filters.FilterSet):
    registered_from = django_filters.IsoDateTimeFilter(
        field_name="registered_at",
        lookup_expr="gte",
    )
    registered_to = django_filters.IsoDateTimeFilter(
        field_name="registered_at",
        lookup_expr="lte",
    )

    class Meta:
        model = Route
        fields = ("status", "priority", "origin_office")
