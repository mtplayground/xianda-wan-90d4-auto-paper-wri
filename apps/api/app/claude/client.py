import json
from dataclasses import dataclass
from functools import lru_cache
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from app.claude.prompts import RenderedPrompt
from app.config import ClaudeConfig, get_settings

ANTHROPIC_VERSION = "2023-06-01"


class ClaudeClientError(RuntimeError):
    pass


@dataclass(frozen=True)
class ClaudeMessage:
    text: str
    model: str
    stop_reason: str | None
    input_tokens: int | None
    output_tokens: int | None
    raw: dict[str, Any]


class ClaudeClient:
    def __init__(self, config: ClaudeConfig) -> None:
        self._config = config

    def complete_prompt(
        self,
        prompt: RenderedPrompt,
        *,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> ClaudeMessage:
        return self.create_message(
            system=prompt.system,
            user=prompt.user,
            max_tokens=max_tokens,
            temperature=temperature,
        )

    def create_message(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> ClaudeMessage:
        if not system.strip():
            raise ClaudeClientError("Claude system prompt must not be blank")
        if not user.strip():
            raise ClaudeClientError("Claude user prompt must not be blank")

        resolved_max_tokens = (
            self._config.max_tokens if max_tokens is None else max_tokens
        )
        resolved_temperature = (
            self._config.temperature if temperature is None else temperature
        )
        if resolved_max_tokens < 1:
            raise ClaudeClientError("Claude max_tokens must be greater than 0")
        if resolved_temperature < 0 or resolved_temperature > 1:
            raise ClaudeClientError("Claude temperature must be between 0 and 1")

        request_body = {
            "model": self._config.model,
            "max_tokens": resolved_max_tokens,
            "temperature": resolved_temperature,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }

        response = self._post_json("/v1/messages", request_body)
        return self._parse_message_response(response)

    def _post_json(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        url = urljoin(self._config.base_url.rstrip("/") + "/", path.lstrip("/"))
        data = json.dumps(body).encode("utf-8")
        request = Request(
            url,
            data=data,
            method="POST",
            headers={
                "anthropic-version": ANTHROPIC_VERSION,
                "content-type": "application/json",
                "x-api-key": self._config.api_key,
            },
        )
        try:
            with urlopen(request, timeout=self._config.timeout_seconds) as response:
                payload = response.read()
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise ClaudeClientError(
                f"Claude API request failed with HTTP {exc.code}: {detail}"
            ) from exc
        except URLError as exc:
            raise ClaudeClientError(f"Claude API request failed: {exc.reason}") from exc
        except TimeoutError as exc:
            raise ClaudeClientError("Claude API request timed out") from exc

        try:
            decoded = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ClaudeClientError("Claude API response was not valid JSON") from exc
        if not isinstance(decoded, dict):
            raise ClaudeClientError("Claude API response had an unexpected shape")
        return decoded

    def _parse_message_response(self, response: dict[str, Any]) -> ClaudeMessage:
        model = response.get("model")
        if not isinstance(model, str) or not model:
            raise ClaudeClientError("Claude API response did not include a model")

        content = response.get("content")
        if not isinstance(content, list):
            raise ClaudeClientError("Claude API response content was not a list")

        text_parts: list[str] = []
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "text" and isinstance(block.get("text"), str):
                text_parts.append(block["text"])
        text = "\n".join(part for part in text_parts if part).strip()
        if not text:
            raise ClaudeClientError("Claude API response did not include text content")

        usage = response.get("usage")
        input_tokens: int | None = None
        output_tokens: int | None = None
        if isinstance(usage, dict):
            if isinstance(usage.get("input_tokens"), int):
                input_tokens = usage["input_tokens"]
            if isinstance(usage.get("output_tokens"), int):
                output_tokens = usage["output_tokens"]

        stop_reason = response.get("stop_reason")
        return ClaudeMessage(
            text=text,
            model=model,
            stop_reason=stop_reason if isinstance(stop_reason, str) else None,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            raw=response,
        )


@lru_cache
def get_claude_client() -> ClaudeClient:
    return ClaudeClient(get_settings().require_claude())
