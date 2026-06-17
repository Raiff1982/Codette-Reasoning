"""
REST API skin for Codette's CognitiveUnit.

Exposes the reasoning engine as a FastAPI HTTP service.
Requires: pip install fastapi uvicorn

Usage:
    python -m api.rest_skin
    # or
    uvicorn api.rest_skin:app --host 0.0.0.0 --port 8000

Endpoints:
    POST /turn          — process one reasoning turn
    POST /feedback      — record feedback signal
    GET  /state         — export session snapshot
    POST /state/restore — restore from snapshot
    GET  /health        — liveness check
"""

from __future__ import annotations

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    _FASTAPI_AVAILABLE = True
except ImportError:
    _FASTAPI_AVAILABLE = False
    logger.warning("FastAPI not installed. Run: pip install fastapi uvicorn")

from core.cognitive_unit import Turn, Feedback, CognitiveSnapshot, TurnResult

try:
    from database_manager import DatabaseManager as _DB
    _db = _DB.get_default()
except Exception:
    _db = None


# ---------------------------------------------------------------------------
# Pydantic request/response models (FastAPI requires these)
# ---------------------------------------------------------------------------

if _FASTAPI_AVAILABLE:

    class TurnRequest(BaseModel):
        query: str
        session_id: str = "default"
        domain_hint: Optional[str] = None
        debate_rounds: int = 2

    class TurnResponse(BaseModel):
        content: str
        intent: dict = {}
        metadata: dict = {}
        session_id: str = "default"

    class FeedbackRequest(BaseModel):
        session_id: str
        helpful: bool
        note: str = ""

    class RestoreRequest(BaseModel):
        session_id: str
        memory_export: str
        cocoon_count: int
        metadata: dict = {}


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

def create_app(cognitive_unit=None) -> "FastAPI":
    """
    Create the FastAPI app. Pass a CognitiveUnit implementation or leave None
    to auto-initialize ForgeEngine on first request.
    """
    if not _FASTAPI_AVAILABLE:
        raise ImportError("FastAPI is required: pip install fastapi uvicorn")

    app = FastAPI(
        title="Codette Reasoning API",
        description="Multi-perspective reasoning engine — REST skin",
        version="1.0.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Lazy-init ForgeEngine if no unit provided
    _unit_holder: dict = {"unit": cognitive_unit}

    def _get_unit():
        if _unit_holder["unit"] is None:
            try:
                from reasoning_forge.forge_engine import ForgeEngine
                _unit_holder["unit"] = ForgeEngine()
                logger.info("[REST] ForgeEngine initialized")
            except Exception as e:
                raise HTTPException(status_code=503, detail=f"Engine init failed: {e}")
        return _unit_holder["unit"]

    @app.get("/health")
    def health():
        return {"status": "ok", "engine": type(_get_unit()).__name__}

    @app.post("/turn", response_model=TurnResponse)
    def process_turn(req: TurnRequest):
        unit = _get_unit()
        turn = Turn(
            query=req.query,
            session_id=req.session_id,
            domain_hint=req.domain_hint,
            debate_rounds=req.debate_rounds,
        )
        try:
            result: TurnResult = unit.process_turn(turn)
        except Exception as e:
            logger.exception("Turn processing failed")
            raise HTTPException(status_code=500, detail=str(e))
        if _db:
            try:
                _db.log_turn(
                    session_id=result.session_id,
                    query=req.query,
                    response=result.content,
                    intent=result.intent,
                    metadata=result.metadata,
                )
            except Exception:
                pass
        return TurnResponse(
            content=result.content,
            intent=result.intent,
            metadata=result.metadata,
            session_id=result.session_id,
        )

    @app.post("/feedback")
    def receive_feedback(req: FeedbackRequest):
        unit = _get_unit()
        feedback = Feedback(session_id=req.session_id, helpful=req.helpful, note=req.note)
        try:
            unit.receive_feedback(feedback)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
        if _db:
            try:
                _db.log_feedback(req.session_id, req.helpful, req.note)
            except Exception:
                pass
        return {"status": "recorded"}

    @app.get("/state")
    def export_state():
        unit = _get_unit()
        try:
            snap: CognitiveSnapshot = unit.export_state()
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
        return {
            "session_id": snap.session_id,
            "memory_export": snap.memory_export,
            "cocoon_count": snap.cocoon_count,
            "metadata": snap.metadata,
        }

    @app.post("/state/restore")
    def restore_state(req: RestoreRequest):
        unit = _get_unit()
        snap = CognitiveSnapshot(
            session_id=req.session_id,
            memory_export=req.memory_export,
            cocoon_count=req.cocoon_count,
            metadata=req.metadata,
        )
        try:
            unit.restore_state(snap)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
        return {"status": "restored", "cocoon_count": req.cocoon_count}

    return app


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if _FASTAPI_AVAILABLE:
    app = create_app()

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("CODETTE_API_PORT", 8765))
    uvicorn.run("api.rest_skin:app", host="0.0.0.0", port=port, reload=False)
