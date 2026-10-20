"""Chat assistant (Task 4 AI feature): Claude on Amazon Bedrock.

Each question goes through three steps:

1. A Bedrock Guardrail checks the question. Harmful content and prompt
   attacks are blocked; email addresses, phone numbers and similar details
   are masked, so they never reach the model.
2. Claude answers, using only the instructions and knowledge files in
   ``backend/chatbot/``.
3. The same guardrail checks the answer before it is shown.

The server keeps no conversation: the browser sends the recent messages with
each question. Message text is never logged.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import anthropic
from botocore.exceptions import BotoCoreError, ClientError
from flask import Blueprint, current_app, jsonify

from .helpers import error_response, json_body_or_error, unknown_fields_error


chat = Blueprint("chat", __name__)

CHATBOT_DIR = Path(__file__).with_name("chatbot")

DEFAULT_MODEL_ID = "anthropic.claude-opus-5-5"

# Limits keep each request small and stop the chat being used to send
# documents to the model.
MAX_MESSAGES = 20
MAX_USER_CHARS = 1000
MAX_ASSISTANT_CHARS = 4000
MAX_TOTAL_CHARS = 12000  # stays under the 16 KB request size limit

REFUSAL_REPLY = (
    "I can't help with that. I can answer questions about T Levels, "
    "placements at Amazon, and this website."
)
EMPTY_REPLY = (
    "Sorry, I couldn't answer that. Try asking in a different way, or check "
    "TLevels.gov.uk."
)


def build_system_prompt(directory: Path = CHATBOT_DIR) -> str:
    """Instructions followed by every knowledge file, in a fixed order.

    The text is identical on every request, so Bedrock can cache it.
    """

    parts = [(directory / "instructions.md").read_text(encoding="utf-8").strip()]
    parts.append("Reference material:")
    for path in sorted((directory / "knowledge").glob("*.md")):
        parts.append(f"<document name=\"{path.name}\">\n"
                     f"{path.read_text(encoding='utf-8').strip()}\n</document>")
    return "\n\n".join(parts)


class ChatUnavailable(RuntimeError):
    """The model or guardrail could not be reached."""


def _contains_blocked_action(value: Any) -> bool:
    """True if any policy in a guardrail assessment blocked the content.

    Masked personal details are reported as "ANONYMIZED", which is allowed.
    """

    if isinstance(value, dict):
        if value.get("action") == "BLOCKED":
            return True
        return any(_contains_blocked_action(v) for v in value.values())
    if isinstance(value, list):
        return any(_contains_blocked_action(v) for v in value)
    return False


class ChatService:
    def __init__(self, model_client, guardrail_client, model_id: str,
                 guardrail_id: str, guardrail_version: str, system_prompt: str):
        self.model_client = model_client
        self.guardrail_client = guardrail_client
        self.model_id = model_id
        self.guardrail_id = guardrail_id
        self.guardrail_version = guardrail_version
        self.system_prompt = system_prompt

    def _guard(self, source: str, text: str) -> Tuple[bool, str]:
        """Return (blocked, text to use) for an INPUT or OUTPUT check."""

        try:
            result = self.guardrail_client.apply_guardrail(
                guardrailIdentifier=self.guardrail_id,
                guardrailVersion=self.guardrail_version,
                source=source,
                content=[{"text": {"text": text}}],
            )
        except (ClientError, BotoCoreError) as exc:
            raise ChatUnavailable("The guardrail could not be reached.") from exc

        if result.get("action") != "GUARDRAIL_INTERVENED":
            return False, text
        guarded = "".join(o.get("text", "") for o in result.get("outputs", []))
        return _contains_blocked_action(result.get("assessments", [])), guarded

    def reply(self, messages: List[Dict[str, str]]) -> Dict[str, str]:
        blocked, question = self._guard("INPUT", messages[-1]["content"])
        if blocked:
            # The guardrail's blocked message, which includes wellbeing
            # signposting.
            return {"status": "blocked", "reply": question}
        messages = messages[:-1] + [{"role": "user", "content": question}]

        try:
            response = self.model_client.messages.create(
                model=self.model_id,
                max_tokens=16000,
                # Short, factual chat answers don't need deep thinking.
                output_config={"effort": "low"},
                system=[{
                    "type": "text",
                    "text": self.system_prompt,
                    "cache_control": {"type": "ephemeral"},
                }],
                messages=messages,
            )
        except anthropic.RateLimitError as exc:
            raise ChatUnavailable("The assistant is busy.") from exc
        except (anthropic.APIStatusError, anthropic.APIConnectionError) as exc:
            raise ChatUnavailable("The model could not be reached.") from exc

        current_app.logger.info(
            "chat reply: stop_reason=%s input_tokens=%s cache_read=%s output_tokens=%s",
            response.stop_reason,
            response.usage.input_tokens,
            getattr(response.usage, "cache_read_input_tokens", None),
            response.usage.output_tokens,
        )

        if response.stop_reason == "refusal":
            return {"status": "refused", "reply": REFUSAL_REPLY}

        answer = "".join(b.text for b in response.content if b.type == "text").strip()
        if not answer:
            return {"status": "answered", "reply": EMPTY_REPLY}

        blocked, answer = self._guard("OUTPUT", answer)
        if blocked:
            return {"status": "blocked", "reply": answer}
        return {"status": "answered", "reply": answer}


def _validate_messages(payload: Any) -> Tuple[Optional[List[Dict[str, str]]], List[str]]:
    if not isinstance(payload, dict):
        return None, ["The request body must be a JSON object."]

    errors: List[str] = []
    unknown = unknown_fields_error(payload, {"messages"})
    if unknown:
        errors.append(unknown)

    messages = payload.get("messages")
    if not isinstance(messages, list) or not 1 <= len(messages) <= MAX_MESSAGES:
        return None, errors + [f"messages must be a list of 1 to {MAX_MESSAGES} messages."]

    cleaned: List[Dict[str, str]] = []
    total = 0
    for index, message in enumerate(messages):
        expected_role = "user" if index % 2 == 0 else "assistant"
        if (
            not isinstance(message, dict)
            or set(message) != {"role", "content"}
            or message["role"] != expected_role
            or not isinstance(message["content"], str)
        ):
            errors.append(
                "messages must alternate user and assistant, starting with "
                "user, and each must have only role and content."
            )
            break
        content = message["content"].strip()
        limit = MAX_USER_CHARS if expected_role == "user" else MAX_ASSISTANT_CHARS
        if not 1 <= len(content) <= limit:
            errors.append(f"Each {expected_role} message must be 1 to {limit} characters.")
            break
        total += len(content)
        cleaned.append({"role": expected_role, "content": content})

    if not errors and cleaned[-1]["role"] != "user":
        errors.append("The last message must be from the user.")
    if not errors and total > MAX_TOTAL_CHARS:
        errors.append("The conversation is too long. Start a new chat.")

    return (None, errors) if errors else (cleaned, [])


@chat.post("/api/chat")
def send_chat_message():
    """Answer a question about T Levels. No account needed."""

    service = current_app.extensions.get("chat_service")
    if service is None:
        return error_response("The chat assistant is not available.", 503)

    payload, error = json_body_or_error()
    if error:
        return error

    messages, errors = _validate_messages(payload)
    if errors:
        return error_response("Validation failed.", 400, errors)

    try:
        result = service.reply(messages)
    except ChatUnavailable as exc:
        current_app.logger.warning("Chat unavailable: %s (%s)", exc, exc.__cause__.__class__.__name__)
        return error_response("The chat assistant is not available right now. Please try again later.", 503)

    return jsonify(result), 200
