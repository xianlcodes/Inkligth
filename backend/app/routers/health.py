from fastapi import APIRouter
from app.schemas import HealthCheck
from app.services.health_service import HealthService

router = APIRouter()


@router.get("/health", response_model=HealthCheck)
async def health_check():
    return HealthService.get_health()
