from dataclasses import dataclass
from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.logistics.models import ExecutionLog, Route


@dataclass(frozen=True)
class ExecutionSummary:
    requested: int
    executed: int
    failed: int
    results: list[dict[str, Any]]

    def as_dict(self) -> dict[str, Any]:
        return {
            "requested": self.requested,
            "executed": self.executed,
            "failed": self.failed,
            "results": self.results,
        }


class RouteExecutionService:
    @staticmethod
    @transaction.atomic
    def execute(route_ids: list[int]) -> ExecutionSummary:
        routes_by_id = {
            route.id: route
            for route in Route.objects.select_for_update().filter(id__in=route_ids)
        }
        execution_time = timezone.now()
        routes_to_update: list[Route] = []
        logs: list[ExecutionLog] = []
        results: list[dict[str, Any]] = []
        executed = 0

        for route_id in route_ids:
            route = routes_by_id.get(route_id)
            if route is None:
                results.append(
                    {
                        "route_id": route_id,
                        "result": "NOT_FOUND",
                        "status": None,
                        "message": "La ruta no existe.",
                    }
                )
                continue

            if route.status == Route.Status.READY:
                route.status = Route.Status.EXECUTED
                routes_to_update.append(route)
                result = ExecutionLog.Result.SUCCESS
                message = "Ruta ejecutada correctamente."
                executed += 1
            else:
                result = ExecutionLog.Result.ERROR
                message = "La ruta no está en estado READY."

            logs.append(
                ExecutionLog(
                    route=route,
                    execution_time=execution_time,
                    result=result,
                    message=message,
                )
            )
            results.append(
                {
                    "route_id": route_id,
                    "result": result,
                    "status": route.status,
                    "message": message,
                }
            )

        if routes_to_update:
            Route.objects.bulk_update(routes_to_update, ["status"])
        if logs:
            ExecutionLog.objects.bulk_create(logs)

        return ExecutionSummary(
            requested=len(route_ids),
            executed=executed,
            failed=len(route_ids) - executed,
            results=results,
        )
