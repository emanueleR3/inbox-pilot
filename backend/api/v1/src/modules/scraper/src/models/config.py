"""Configuration constants for the scraper module."""

# ------------------------------------------------------
#  LLM CONFIGURATION
# ------------------------------------------------------
LLM_MODEL = "gpt-4o-mini"
LLM_TEMPERATURE = 0
CLEANING_BATCH_SIZE = 16

# ------------------------------------------------------
#  EMBEDDING CONFIGURATION
# ------------------------------------------------------
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_BATCH_SIZE = 64

# ------------------------------------------------------
#  CHUNKING CONFIGURATION
# ------------------------------------------------------
MAX_CHARS = 3000
OVERLAP_CHARS = 200
THRESHOLD_NO_CHUNKING = 3500
MIN_CHARS = 300

# ------------------------------------------------------
#  QDRANT CONFIGURATION
# ------------------------------------------------------
QDRANT_BATCH_SIZE = 64
DEFAULT_VECTOR_SIZE = 1536
