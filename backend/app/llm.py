import json
import logging
import os
import re
from typing import List

import boto3

try:
    import openai
except Exception:
    openai = None

from .config import (
    ANTHROPIC_VERSION,
    BEDROCK_CLAUDE_MODEL,
    BEDROCK_REGION,
    CLAUDE_MAX_TOKENS,
    CLAUDE_TEMPERATURE,
    LLM_PROVIDER,
    AWS_ACCESS_KEY_ID,
    AWS_SECRET_ACCESS_KEY,
    AWS_SESSION_TOKEN,
)

logger = logging.getLogger(__name__)

_bedrock_client = None


def _get_bedrock_client():
    global _bedrock_client
    if _bedrock_client is None:
        _bedrock_client = boto3.client(
            "bedrock-runtime",
            region_name=BEDROCK_REGION,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            aws_session_token=AWS_SESSION_TOKEN,
        )
    return _bedrock_client


def _collect_bedrock_stream(response) -> str:
    """
    Consume a Bedrock streaming response and return the concatenated text.
    Mirrors the pattern from bedrock_collect_stream_bedrock in the user's snippet.
    """
    body = response.get("body")
    collected_chunks: List[str] = []

    if body is None:
        return ""

    for event in body:
        if "chunk" not in event:
            continue
        raw_bytes = event["chunk"]["bytes"]
        data = (
            raw_bytes.decode("utf-8")
            if isinstance(raw_bytes, (bytes, bytearray))
            else raw_bytes
        )
        try:
            payload = json.loads(data)
        except json.JSONDecodeError:
            logger.error("JSON decoding failed for Bedrock chunk.")
            continue

        delta = payload.get("delta", {})
        text = delta.get("text")
        if text:
            collected_chunks.append(text)

    final_text = "".join(collected_chunks).strip()
    return final_text


def _invoke_claude(prompt: str, chat_session_id: str = "") -> str:
    """
    Call Bedrock Claude 3.5 with streaming response, following the provided pattern.
    """
    client = _get_bedrock_client()

    body = json.dumps(
        {
            "anthropic_version": ANTHROPIC_VERSION,
            "messages": [
                {"role": "user", "content": [{"type": "text", "text": prompt}]}
            ],
            "max_tokens": CLAUDE_MAX_TOKENS,
            "temperature": CLAUDE_TEMPERATURE,
        }
    )

    logger.info(
        "Using chat session ID for Bedrock Claude 3.5 chat completion: %s",
        chat_session_id,
    )

    try:
        response = client.invoke_model_with_response_stream(
            modelId=BEDROCK_CLAUDE_MODEL,
            body=body,
            contentType="application/json",
            accept="application/json",
        )
        logger.info("API request sent, processing streaming response.")
        return _collect_bedrock_stream(response)
    except Exception:
        logger.exception("Unexpected error in Bedrock Claude invocation")
        raise


def _post_process_answer(answer: str) -> str:
    """
    Post-process the answer to ensure URLs are included when service names are mentioned.
    """
    # URL mappings for common service names
    url_mappings = {
        "Informa IT Service Hub": "https://informa.service-now.com/iportal?id=sc_home",
        "IT Service Hub": "https://informa.service-now.com/iportal?id=sc_home",
    }

    # Check if answer mentions service names but doesn't include the URL
    answer_lower = answer.lower()
    for term, url in url_mappings.items():
        term_lower = term.lower()
        if term_lower in answer_lower and url not in answer:
            # Try to inject the URL near the first mention
            # Find the first occurrence and add URL after it
            pattern = re.compile(re.escape(term), re.IGNORECASE)
            match = pattern.search(answer)
            if match:
                pos = match.end()
                # Insert URL right after the term
                answer = answer[:pos] + f" ({url})" + answer[pos:]

    return answer


def generate_answer(question: str, context_chunks: List[str]) -> str:
    """
    Send a prompt to the configured LLM and return the answer text.
    The function builds an instruction that tells the model
    to rely only on the given context.
    """
    prompt = _build_rag_prompt(context_chunks, question)

    provider = LLM_PROVIDER.lower()

    if provider == "openai":
        if openai is None:
            raise RuntimeError("openai library is required")

        openai.api_key = os.getenv("OPENAI_API_KEY")
        model = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")

        resp = openai.ChatCompletion.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant answering only from the provided context.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            max_tokens=400,
            temperature=0.0,
        )

        answer = resp["choices"][0]["message"]["content"].strip()
        return _post_process_answer(answer)

    if provider == "claude":
        answer = _invoke_claude(prompt)
        return _post_process_answer(answer)

    # Default: return concatenated context (safe fallback)
    return "\n\n".join(context_chunks)


def _build_rag_prompt(context_chunks: List[str], question: str) -> str:
    ctx = "\n\n".join([f"Context {i + 1}:\n{c}" for i, c in enumerate(context_chunks)])

    # Known URL mappings for common service names
    url_mappings = {
        "Informa IT Service Hub": "https://informa.service-now.com/iportal?id=sc_home",
        "IT Service Hub": "https://informa.service-now.com/iportal?id=sc_home",
        "ServiceNow": "https://informa.service-now.com/iportal?id=sc_home",
    }

    # Add URL mappings to context if relevant terms appear
    additional_info = ""
    ctx_lower = ctx.lower()
    for term, url in url_mappings.items():
        if term.lower() in ctx_lower:
            additional_info += f"\nNote: When '{term}' is mentioned, it refers to: {url}\n"

    prompt = (
        "Use ONLY the context below to answer the question. "
        "If the answer cannot be found in the context, say you don't know.\n\n"
        "IMPORTANT: When providing step-by-step instructions, ALWAYS include any URLs or links "
        "that appear in the context. If the context mentions 'Informa IT Service Hub' or similar "
        "service names, include the full URL as a clickable link in your answer.\n\n"
        f"{ctx}\n\n"
        f"{additional_info}\n\n"
        f"User question: {question}\n\n"
        "Answer with clear step-by-step instructions, including all URLs/links mentioned in the context:"
    )

    return prompt
