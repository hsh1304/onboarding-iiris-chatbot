import json
import os
from typing import List

import boto3

from .config import BEDROCK_REGION, BEDROCK_EMBED_MODEL, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_SESSION_TOKEN

# Optional fallback to local model
LOCAL_MODEL = False


if os.getenv("USE_LOCAL_EMBEDDINGS", "false").lower() == "true":
    LOCAL_MODEL = True


if LOCAL_MODEL:
    from sentence_transformers import SentenceTransformer
    _local_model = SentenceTransformer("all-MiniLM-L6-v2")


_bedrock_client = None


def _get_bedrock_client():
    global _bedrock_client
    if _bedrock_client is None:
        _bedrock_client = boto3.client("bedrock-runtime", region_name=BEDROCK_REGION, aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY, aws_session_token=AWS_SESSION_TOKEN)
    return _bedrock_client


def _embed_single(text: str) -> List[float]:
    client = _get_bedrock_client()
    body = json.dumps({"inputText": text})

    resp = client.invoke_model(
        modelId=BEDROCK_EMBED_MODEL,
        body=body,
        accept="application/json",
        contentType="application/json",
    )

    payload = json.loads(resp["body"].read())
    embedding = payload.get("embedding") or payload.get("embeddings", [None])[0]
    if embedding is None:
        raise RuntimeError(f"Bedrock response missing embedding: {payload}")
    return embedding


def embed_texts(texts: List[str]) -> List[List[float]]:
    """Return list of embeddings for the given list of texts using Bedrock Titan."""
    if LOCAL_MODEL:
        return _local_model.encode(texts).tolist()

    return [_embed_single(t) for t in texts]


def embed_query(text: str) -> List[float]:
    """Return embedding for the given text."""
    return embed_texts([text])[0]