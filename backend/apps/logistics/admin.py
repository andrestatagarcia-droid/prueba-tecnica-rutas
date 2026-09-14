from django.contrib import admin

from .models import (
    ExecutionLog,
    GeographicPoint,
    ImportBatch,
    ImportIssue,
    Office,
    Priority,
    Route,
    RoutePayload,
)

admin.site.register(Office)
admin.site.register(Priority)
admin.site.register(GeographicPoint)
admin.site.register(ImportBatch)
admin.site.register(ImportIssue)
admin.site.register(Route)
admin.site.register(RoutePayload)
admin.site.register(ExecutionLog)

