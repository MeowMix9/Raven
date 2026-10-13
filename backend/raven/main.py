from fastapi import FastAPI

from raven import __version__
from raven.api.health import router as health_router
from raven.api.inventory import router as inventory_router

app = FastAPI(title="Raven", version=__version__)
app.include_router(health_router)
app.include_router(inventory_router)
