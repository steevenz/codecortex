"""
@project   Myawesomeproject
@package   src
@author    Steeven Andrian
@copyright (c) Steeven Andrian
@fileoverview Main entry point for Myawesomeproject.
"""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from src.core.logger import get_logger, set_request_id

logger = get_logger(__name__)

from fastapi import FastAPI
import uvicorn

app = FastAPI(
    title="Myawesomeproject",
    version="0.1.0",
    description="Web API Project (FastAPI)",
)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"message": "Hello from Myawesomeproject", "version": "0.1.0"}


def cli():
    """CLI entry point — starts the uvicorn server."""
    request_id = set_request_id(logger)
    logger.info("Starting Myawesomeproject", extra={"request_id": request_id})
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    cli()
