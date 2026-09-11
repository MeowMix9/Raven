from fastapi import FastAPI

from raven import __version__
from raven.api.health import router as health_router

app = FastAPI(title="Raven", version=__version__)
app.include_router(health_router)
