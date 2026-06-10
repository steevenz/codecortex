"""
/**
 * @project   CodeCortex
 * @package   Server
 * @author    Steeven Andrian
 * @copyright (c) 2026 Aegis Codework
 * @standard  Aegis-CrossStack-v1.0
 * @stack     Python, FastAPI
 * * Webhook listener for Git events (push, PR, merge) to trigger re-index.
 */
"""

import os
import json
import logging
import hmac
import hashlib
from typing import Optional
from fastapi import FastAPI, HTTPException, Request, Depends
from src.core.logging import get_logger

logger = get_logger(__name__)

SECRET = os.getenv("CODECORTEX_WEBHOOK_SECRET", "").strip()


def verify_signature(payload: bytes, signature_header: Optional[str]) -> bool:
    if not SECRET or not signature_header:
        return False
    expected = "sha256=" + hmac.new(SECRET.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header.strip())


def register_webhook_routes(app: FastAPI, trigger_reindex):
    @app.post("/webhook/git-event")
    async def handle_git_event(request: Request):
        body = await request.body()
        sig = request.headers.get("X-Hub-Signature-256")
        if not verify_signature(body, sig):
            raise HTTPException(status_code=403, detail="Invalid signature")

        event = request.headers.get("X-GitHub-Event", "push")
        payload = json.loads(body)
        repo_name = payload.get("repository", {}).get("full_name", "unknown")
        ref = payload.get("ref", "")

        if event in ("push", "pull_request", "merge"):
            logger.info(f"Webhook event={event} repo={repo_name} ref={ref}")
            try:
                trigger_reindex(repo_name, ref)
            except Exception as e:
                logger.error(f"Re-index failed for {repo_name}: {e}")

        return {"status": "received", "event": event, "repo": repo_name}
