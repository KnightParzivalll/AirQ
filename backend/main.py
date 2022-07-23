from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from stations.api import stations_router

config = {
    "handlers": [
        {
            "sink": ".logs/debug.log",
            "level": "DEBUG",
            "rotation": "1 MB",
            "compression": "zip",
        },
    ],
}

logger.configure(**config)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(stations_router)
