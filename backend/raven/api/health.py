from fastapi import APIRouter

from raven import __version__

router = APIRouter(tags=["health"])


def _health_response() -> dict[str, str]:
    return {"status": "ok", "service": "raven-api", "version": __version__}


@router.get("/health")
def health() -> dict[str, str]:
    return _health_response()


@router.get("/api/v1/health")
def versioned_health() -> dict[str, str]:
    return _health_response()
