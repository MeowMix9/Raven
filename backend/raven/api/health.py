from fastapi import APIRouter

from raven import __version__

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "raven-api", "version": __version__}
