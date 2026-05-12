"""Service discovery and health endpoints."""
from fastapi import APIRouter

router = APIRouter(tags=["system"])


@router.get("/health")
def health() -> dict:
    """Liveness probe: static OK payload identifying this service."""
    return {"status": "ok", "service": "user-accounts-prefs"}


@router.get("/")
def root() -> dict:
    """Root greeting for manual checks or load balancers."""
    return {"message": "Welcome to User Preferences and Accounts Service"}
