"""Codette API — NON-FUNCTIONAL. Kept as a record, not as a service.

This module cannot start. It imports ``codette.codette_core``, and no such
package exists anywhere in this repository — ``webapp/codette.py`` is a flat
module, not that package. Nothing references ``main:app``: no Dockerfile, no CI
job, no script. It originated in a hackathon build (first committed in #14,
be01c22) and was never wired up here.

Labelled rather than deleted, per the house rule in CLAUDE.md.

One thing was NOT left as found. This file previously hardcoded the API key that
``verify_api_key`` compares against — the only authentication on
``/codette/respond`` — as a literal, alongside a comment saying it should be in
an environment variable. Dead code or not, a live-looking credential does not
belong in a public repository, so it now reads from the environment and fails
closed when unset. The literal that was here is in git history and should be
treated as disclosed: rotate it wherever it was ever used.
"""

import os

from fastapi import FastAPI, HTTPException, Security, Depends
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from typing import Optional
from codette.codette_core import AICore  # noqa: F401 — absent; see module docstring
import hmac
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Codette API")
codette = AICore()

# Security configuration.
# No default. An unset key must not silently degrade to a guessable shared
# secret, so verify_api_key rejects every request until CODETTE_API_KEY is set.
API_KEY_NAME = "X-API-Key"
API_KEY = os.environ.get("CODETTE_API_KEY")
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=True)

class PromptRequest(BaseModel):
    prompt: str
    context: Optional[dict] = None

class ErrorResponse(BaseModel):
    error: str
    timestamp: str
    request_id: str

async def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    if not API_KEY:
        logger.error("CODETTE_API_KEY is unset; refusing all authenticated requests")
        raise HTTPException(
            status_code=503,
            detail="Server is not configured for authentication"
        )
    if not hmac.compare_digest(api_key, API_KEY):
        logger.warning(f"Invalid API key attempt at {datetime.utcnow()}")
        raise HTTPException(
            status_code=403,
            detail="Invalid API key"
        )
    return api_key

@app.post("/codette/respond", response_model=dict)
async def respond(
    prompt_request: PromptRequest,
    api_key: str = Depends(verify_api_key)
):
    try:
        logger.info(f"Processing request with context: {prompt_request.context}")
        result = codette.process_input(
            prompt=prompt_request.prompt,
            context=prompt_request.context
        )
        
        return {
            "response": result,
            "timestamp": datetime.utcnow().isoformat(),
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@app.get("/health")
async def health_check():
    try:
        # Perform basic health check
        codette.health_check()
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail="Service unhealthy"
        )

@app.on_event("startup")
async def startup_event():
    logger.info("Starting Codette API service")
    try:
        # Initialize any necessary resources
        codette.initialize()
    except Exception as e:
        logger.critical(f"Failed to initialize Codette: {str(e)}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down Codette API service")
    try:
        # Cleanup any resources
        codette.cleanup()
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")