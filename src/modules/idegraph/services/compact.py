"""
@project   CodeCortex
@package   modules.idegraph.services
@author    Steeven Andrian
@copyright (c) 2026 CODDY Codework
:package:  modules.idegraph.services
:standard: CODDY-IdeGraph-v1.0

Compact — Conversation compaction using local LLM (Ollama).
Unified interface that replaces both CompactEngine and MemoryCompactor.
"""

import json
import os
import re
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List

from src.modules.idegraph.core.logging_service import get_logger

logger = get_logger(__name__)

AGENTS_HOME = Path.home() / ".aicoders" / ".agents"
COMPACTS_DIR = AGENTS_HOME / "logs" / "compacts"
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
COMPACT_MODEL = os.environ.get("COMPACT_MODEL", "llama3.2:3b")
COMPACT_SCHEMA_VERSION = "2.0.0"


class Compact:
    def __init__(self):
        COMPACTS_DIR.mkdir(parents=True, exist_ok=True)

    def compact(self, conversation_text: str, title: str = "") -> Optional[Dict[str, Any]]:
        prompt = self._build_prompt(conversation_text, title)
        raw = self._call_ollama(prompt)
        if raw:
            parsed = self._parse_output(raw)
            if parsed:
                self._save_compact(parsed)
                return parsed
        return self._fallback(conversation_text, title)

    def _build_prompt(self, text: str, title: str) -> str:
        return f"""Summarize this AI coding session (max 400 words). Extract:

1. GOAL: What the user wanted (1 sentence)
2. CURRENT_STATE: What existed before (the problem/context)
3. TARGET_STATE: The desired end state
4. APPROACH: Why this implementation approach
5. STEPS: Ordered list of actions taken
6. ADDED: New files or features created
7. CHANGED: Existing things modified
8. FIXED: Bugs or issues resolved
9. KEY_DECISIONS: Important technical decisions and rationale
10. NOTES: Context that should survive to the next session
11. RESULT: completed | partial | failed

Conversation:
{text[:8000]}

Output as plain text with labeled sections.
"""

    def _call_ollama(self, prompt: str) -> Optional[str]:
        import urllib.request
        payload = json.dumps({
            "model": COMPACT_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"num_predict": 512, "temperature": 0.3},
        }).encode()
        try:
            req = urllib.request.Request(
                f"{OLLAMA_URL}/api/generate", data=payload,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read())
                return result.get("response", "").strip()
        except Exception as e:
            logger.warning(f"Ollama call failed: {e}")
            return None

    def _parse_output(self, raw: str) -> Optional[Dict[str, Any]]:
        try:
            if "goal:" in raw.lower():
                result = {}
                current_key = None
                current_list = []
                for line in raw.split("\n"):
                    l = line.strip()
                    if not l:
                        continue
                    for key in ["goal:", "thinking:", "decisions:", "alternatives:",
                                 "action:", "files:", "result:", "insights:"]:
                        if l.lower().startswith(key.lower()):
                            if current_key:
                                self._set_field(result, current_key, current_list)
                            current_key = key.rstrip(":").lower()
                            val = l[len(key):].strip()
                            current_list = [val] if val else []
                            break
                    else:
                        if current_key in ("decisions", "alternatives", "files"):
                            current_list.append(l)
                        elif current_key:
                            current_list.append(l)
                if current_key:
                    self._set_field(result, current_key, current_list)
                if result.get("goal") or result.get("action"):
                    return result
            return {"goal": "(parsed)", "raw": raw[:500]}
        except Exception:
            return None

    def _set_field(self, result: Dict, key: str, val: List[str]):
        text = "\n".join(v for v in val if v and not v.startswith("- ")).strip()
        items = [v.lstrip("- ").strip() for v in val if v.startswith("- ")]
        if key in ("decisions", "alternatives", "files"):
            result[key] = items or text
        else:
            result[key] = text

    def _fallback(self, text: str, title: str) -> Dict[str, Any]:
        msgs = re.split(r"### (USER|ASSISTANT|SYSTEM)", text)
        user_msgs = []
        assistant_msgs = []
        for i in range(1, len(msgs), 2):
            role = msgs[i].strip()
            content = msgs[i + 1].strip() if i + 1 < len(msgs) else ""
            if role == "USER":
                user_msgs.append(content)
            elif role == "ASSISTANT":
                assistant_msgs.append(content)
        decisions = []
        for msg in assistant_msgs:
            for pattern in [r"Let me\s+(\w+)", r"I('ll| will)\s+(\w+)", r"decided to\s+(\w+)"]:
                m = re.search(pattern, msg, re.IGNORECASE)
                if m:
                    decisions.append({"decision": m.group(0)[:100], "why": ""})
                    break
        file_refs = list(set(re.findall(r'`([^`]+\.[a-zA-Z]+)`', text)))[:15]
        result = {
            "schema_version": COMPACT_SCHEMA_VERSION,
            "goal": title or "AI coding session",
            "improvement_plan": {"current_state": "LLM unavailable", "target_state": "", "approach": ""},
            "task_plan": [],
            "changelog": {"added": [], "changed": [], "fixed": []},
            "walkthrough": {
                "reasoning": assistant_msgs[0][:500] if assistant_msgs else "",
                "decisions": decisions[:5],
                "files": [{"path": f, "change": "referenced"} for f in file_refs],
                "notes": "",
            },
            "result": "unknown",
            "insights": "",
        }
        self._save_compact(result)
        return result

    def _save_compact(self, record: Dict[str, Any]) -> Path:
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H%M%S")
        goal_raw = record.get("goal", "unknown")[:24].lower()
        goal_slug = re.sub(r'[^a-z0-9]+', '-', goal_raw).strip('-')
        file_id = hashlib.sha256(str(record).encode()).hexdigest()[:8]
        subfolder = COMPACTS_DIR / date_str
        subfolder.mkdir(parents=True, exist_ok=True)
        filename = f"{time_str}-{goal_slug}-{file_id}.yaml"
        filepath = subfolder / filename
        import yaml
        with open(filepath, "w", encoding="utf-8") as f:
            yaml.dump(record, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        logger.info(f"Compact saved: {filepath}")
        return filepath
