from __future__ import annotations


class HealthService:
    def __init__(self, *, vector_health_service=None) -> None:
        self._vector_health_service = vector_health_service

    def check(self) -> dict[str, object]:
        checks: dict[str, str] = {"api": "ok"}
        status = "ok"

        if self._vector_health_service is None:
            checks["vector_memory"] = "disabled"
        else:
            vector_checks = self._vector_health_service.check()
            checks.update(vector_checks)
            if any(value != "ok" for value in vector_checks.values()):
                status = "degraded"

        return {
            "status": status,
            "checks": checks,
        }
