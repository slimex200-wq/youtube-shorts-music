"""LLM abstraction layer.

Two implementations:
- ClaudeCliClient: subprocess `claude -p`, uses Max plan OAuth quota (no API billing)
- AnthropicApiClient: direct Anthropic SDK, billed per token

Default is ClaudeCliClient so the app runs on Max without API charges.
Switch via env LLM_MODE=api to use the SDK path.
"""
import base64
import json
import logging
import os
import subprocess
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Protocol

from config import BASE_DIR

logger = logging.getLogger(__name__)

USAGE_LOG_PATH = BASE_DIR / "config" / "llm_usage.jsonl"


class LLMClient(Protocol):
    def complete(
        self,
        system: str,
        user: str,
        model: str = "haiku",
        max_tokens: int = 2048,
        timeout: int = 180,
    ) -> str: ...

    def complete_vision(
        self,
        system: str,
        user_text: str,
        image_data: bytes,
        image_media_type: str,
        model: str = "haiku",
        max_tokens: int = 2048,
        timeout: int = 180,
    ) -> str: ...


class LLMError(RuntimeError):
    pass


def _append_usage(record: dict) -> None:
    try:
        USAGE_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with USAGE_LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError as e:
        logger.warning("Failed to append usage log: %s", e)


@dataclass
class ClaudeCliClient:
    binary: str = "claude"

    def complete(
        self,
        system: str,
        user: str,
        model: str = "haiku",
        max_tokens: int = 2048,
        timeout: int = 180,
    ) -> str:
        env = os.environ.copy()
        env.pop("ANTHROPIC_API_KEY", None)

        cmd = [
            self.binary,
            "-p",
            "--system-prompt", system,
            "--output-format", "json",
            "--model", model,
            "--no-session-persistence",
        ]

        try:
            proc = subprocess.run(
                cmd,
                input=user,
                capture_output=True,
                text=True,
                encoding="utf-8",
                env=env,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as e:
            raise LLMError(f"claude CLI timed out after {timeout}s") from e
        except FileNotFoundError as e:
            raise LLMError(f"claude CLI not found: {self.binary}") from e

        if proc.returncode != 0:
            raise LLMError(
                f"claude CLI exit {proc.returncode}: {proc.stderr.strip()[:500]}"
            )

        try:
            envelope = json.loads(proc.stdout)
        except json.JSONDecodeError as e:
            raise LLMError(
                f"Failed to parse claude envelope: {e}\n{proc.stdout[:500]}"
            ) from e

        if envelope.get("is_error"):
            raise LLMError(
                f"claude CLI returned error: {envelope.get('result', '')[:500]}"
            )

        usage = envelope.get("usage", {}) or {}
        _append_usage({
            "at": datetime.now(timezone.utc).isoformat(),
            "backend": "cli",
            "model": model,
            "cost_usd": envelope.get("total_cost_usd", 0),
            "duration_ms": envelope.get("duration_ms", 0),
            "input_tokens": usage.get("input_tokens", 0),
            "output_tokens": usage.get("output_tokens", 0),
            "cache_read_tokens": usage.get("cache_read_input_tokens", 0),
            "cache_creation_tokens": usage.get("cache_creation_input_tokens", 0),
        })

        return envelope.get("result", "") or ""

    def complete_vision(
        self,
        system: str,
        user_text: str,
        image_data: bytes,
        image_media_type: str,
        model: str = "haiku",
        max_tokens: int = 2048,
        timeout: int = 180,
    ) -> str:
        suffix = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}.get(
            image_media_type, ".png"
        )
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(image_data)
            tmp_path = tmp.name

        env = os.environ.copy()
        env.pop("ANTHROPIC_API_KEY", None)

        cmd = [
            self.binary,
            "-p",
            "--system-prompt", system,
            "--output-format", "json",
            "--model", model,
            "--no-session-persistence",
            tmp_path,
        ]

        try:
            proc = subprocess.run(
                cmd,
                input=user_text,
                capture_output=True,
                text=True,
                encoding="utf-8",
                env=env,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as e:
            raise LLMError(f"claude CLI vision timed out after {timeout}s") from e
        finally:
            Path(tmp_path).unlink(missing_ok=True)

        if proc.returncode != 0:
            raise LLMError(
                f"claude CLI vision exit {proc.returncode}: {proc.stderr.strip()[:500]}"
            )

        try:
            envelope = json.loads(proc.stdout)
        except json.JSONDecodeError as e:
            raise LLMError(
                f"Failed to parse claude vision envelope: {e}\n{proc.stdout[:500]}"
            ) from e

        if envelope.get("is_error"):
            raise LLMError(
                f"claude CLI vision error: {envelope.get('result', '')[:500]}"
            )

        usage = envelope.get("usage", {}) or {}
        _append_usage({
            "at": datetime.now(timezone.utc).isoformat(),
            "backend": "cli_vision",
            "model": model,
            "cost_usd": envelope.get("total_cost_usd", 0),
            "duration_ms": envelope.get("duration_ms", 0),
            "input_tokens": usage.get("input_tokens", 0),
            "output_tokens": usage.get("output_tokens", 0),
            "cache_read_tokens": usage.get("cache_read_input_tokens", 0),
            "cache_creation_tokens": usage.get("cache_creation_input_tokens", 0),
        })

        return envelope.get("result", "") or ""


@dataclass
class AnthropicApiClient:
    api_key: str
    _model_aliases: dict = field(default_factory=lambda: {
        "haiku": "claude-haiku-4-5-20251001",
        "sonnet": "claude-sonnet-4-20250514",
        "opus": "claude-opus-4-20250514",
    })

    def __post_init__(self) -> None:
        import anthropic

        self._client = anthropic.Anthropic(api_key=self.api_key)

    def complete(
        self,
        system: str,
        user: str,
        model: str = "haiku",
        max_tokens: int = 2048,
        timeout: int = 180,
    ) -> str:
        resolved = self._model_aliases.get(model, model)
        try:
            msg = self._client.messages.create(
                model=resolved,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
                timeout=timeout,
            )
        except Exception as e:
            raise LLMError(f"Anthropic API call failed: {e}") from e

        usage = getattr(msg, "usage", None)
        _append_usage({
            "at": datetime.now(timezone.utc).isoformat(),
            "backend": "api",
            "model": resolved,
            "input_tokens": getattr(usage, "input_tokens", 0) if usage else 0,
            "output_tokens": getattr(usage, "output_tokens", 0) if usage else 0,
        })

        return msg.content[0].text

    def complete_vision(
        self,
        system: str,
        user_text: str,
        image_data: bytes,
        image_media_type: str,
        model: str = "haiku",
        max_tokens: int = 2048,
        timeout: int = 180,
    ) -> str:
        resolved = self._model_aliases.get(model, model)
        b64 = base64.standard_b64encode(image_data).decode("ascii")
        user_content = [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": image_media_type,
                    "data": b64,
                },
            },
            {"type": "text", "text": user_text},
        ]
        try:
            msg = self._client.messages.create(
                model=resolved,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user_content}],
                timeout=timeout,
            )
        except Exception as e:
            raise LLMError(f"Anthropic vision API call failed: {e}") from e

        usage = getattr(msg, "usage", None)
        _append_usage({
            "at": datetime.now(timezone.utc).isoformat(),
            "backend": "api_vision",
            "model": resolved,
            "input_tokens": getattr(usage, "input_tokens", 0) if usage else 0,
            "output_tokens": getattr(usage, "output_tokens", 0) if usage else 0,
        })

        return msg.content[0].text


_cached_client: Optional[LLMClient] = None


def default_client() -> LLMClient:
    """Return the configured LLM client. Respects LLM_MODE env (claude_cli|api)."""
    global _cached_client
    if _cached_client is not None:
        return _cached_client

    mode = os.environ.get("LLM_MODE", "claude_cli").lower()
    if mode == "api":
        key = os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise LLMError("LLM_MODE=api requires ANTHROPIC_API_KEY")
        _cached_client = AnthropicApiClient(api_key=key)
    else:
        _cached_client = ClaudeCliClient()

    return _cached_client


def reset_default_client() -> None:
    """Test hook — clears the cached client so a new mode takes effect."""
    global _cached_client
    _cached_client = None
