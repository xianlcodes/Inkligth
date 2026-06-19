from app.core.config import settings


class HealthService:
    @staticmethod
    def get_health() -> dict:
        return {"status": "ok", "version": settings.VERSION}
