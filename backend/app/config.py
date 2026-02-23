import os


CONFLUENCE_BASE_URL = os.getenv("CONFLUENCE_BASE_URL", "https://your-domain.atlassian.net/wiki")
CONFLUENCE_EMAIL = os.getenv("CONFLUENCE_EMAIL")
CONFLUENCE_API_TOKEN = os.getenv("CONFLUENCE_API_TOKEN")


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") # Optional, used for embeddings and generation by default


# Behavior tuning
TOP_K = int(os.getenv("TOP_K", "4"))
RELEVANCE_THRESHOLD = float(os.getenv("RELEVANCE_THRESHOLD", "0.45"))
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "500")) # characters approximate


# LLM selection
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "claude") # "openai" or "claude" or "local"
BEDROCK_CLAUDE_MODEL = os.getenv(
    "BEDROCK_CLAUDE_MODEL",
    "arn:aws:bedrock:us-east-1:751269371226:inference-profile/us.anthropic.claude-3-5-haiku-20241022-v1:0",
)
CLAUDE_MAX_TOKENS = int(os.getenv("CLAUDE_MAX_TOKENS", "2000"))
CLAUDE_TEMPERATURE = float(os.getenv("CLAUDE_TEMPERATURE", "0.0"))
ANTHROPIC_VERSION = os.getenv("ANTHROPIC_VERSION", "bedrock-2023-05-31")

# Local file ingestion
PDF_PATH = os.getenv(
    "PDF_PATH",
    "/app/app/data/IQ-Access Requests and Resources for IIRIS Leadinsights Services Team-151225-094203.pdf",
)

# Bedrock embeddings
BEDROCK_REGION = os.getenv("BEDROCK_REGION", "us-east-1")
BEDROCK_EMBED_MODEL = os.getenv(
    "BEDROCK_EMBED_MODEL",
    "amazon.titan-embed-text-v2:0",
)
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "")
AWS_SESSION_TOKEN = os.getenv("AWS_SESSION_TOKEN", "")