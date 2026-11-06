# 07 · Configuration Reference

> In one sentence: all runtime configuration lives in `Settings`; secrets use `SecretStr`; tests override environment variables via conftest.

## Chapter Contents

1. [Loading](#loading)
2. [Settings Variables](#settings-variables)
3. [Capability Switches](#capability-switches)

Covers: `app/config/settings.py`, `.env.example`, `tests/conftest.py`.

## Loading

### Code Summary

```python
# app/config/settings.py
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    deepseek_api_key: SecretStr = SecretStr("")
    deepseek_model: str = "deepseek-chat"  # DeepSeek-V3 on the API

    @property
    def llm_configured(self) -> bool:
        return bool(self.deepseek_api_key.get_secret_value())

    @property
    def cross_encoder_configured(self) -> bool:
        return self.cross_encoder_enabled and (
            self.app_env != "testing" or self.cross_encoder_force
        )
```

`get_settings()` is wrapped in `lru_cache`. After changing environment variables in tests, you must call `clear_settings_cache()`.

`APP_ENV=development|testing|production`. `tests/conftest.py` forces `APP_ENV=testing` and clears the LLM/Embedding keys; the test environment does not download the Cross-Encoder.

## Settings Variables

### Application

| Variable | Default | Description |
|---|---|---|
| `APP_ENV` | `development` | log verbosity, whether admin requires a token |
| `LOG_LEVEL` | `INFO` | INFO recommended in production |
| `API_V1_PREFIX` | `/api/v1` | |

### Models

| Variable | Default | Description |
|---|---|---|
| `LLM_API_KEY` | empty | empty means Fake LLM |
| `LLM_BASE_URL` | `https://api.deepseek.com` | OpenAI-compatible |
| `LLM_MODEL` | `deepseek-chat` | |
| `LLM_TIMEOUT_SECONDS` | `30` | read timeout |
| `LLM_MAX_RETRIES` | `3` | retryable errors only |
| `EMBEDDING_API_KEY` / `BASE_URL` | empty | both must be set to use the remote OpenAI-compatible endpoint |
| `EMBEDDING_MODEL` | `bge-small-en-v1.5` | used only by the remote gateway |
| `EMBEDDING_DIM` | `384` | must match the vector store dimension; local `bge-small-en-v1.5` is 384 |
| `LOCAL_EMBEDDING_ENABLED` | true | production recall uses local `BAAI/bge-small-en-v1.5` |
| `LOCAL_EMBEDDING_MODEL` | `BAAI/bge-small-en-v1.5` | sentence-transformers bi-encoder; reranking is the separate `bge-reranker-*` family |
| `LOCAL_EMBEDDING_DEVICE` | empty (auto cuda/mps/cpu) | |
| `LOCAL_EMBEDDING_FORCE` | false | still loads weights under testing |
| `CROSS_ENCODER_ENABLED` | true | production reranking via Cross-Encoder |
| `CROSS_ENCODER_MODEL` | `BAAI/bge-reranker-base` | sentence-transformers CrossEncoder |
| `CROSS_ENCODER_DEVICE` | empty (auto cuda/mps/cpu) | |
| `CROSS_ENCODER_MAX_LENGTH` | 512 | |
| `CROSS_ENCODER_FORCE` | false | still loads weights under testing (for evaluation) |
| `UNSTRUCTURED_ENABLED` | true | production ingest goes through Unstructured |
| `UNSTRUCTURED_STRATEGY` | `auto` | PDF/images: `auto` / `fast` / `hi_res` / `ocr_only` |
| `UNSTRUCTURED_OCR_LANGUAGES` | `chi_sim+eng` | Tesseract language packs, `+` or comma separated |
| `UNSTRUCTURED_FORCE` | false | still uses Unstructured under testing (requires `.[docs]`) |
| `MCP_ENABLED` | true | registers local MCP tools |
| `MCP_REMOTE_URL` | empty | when non-empty, adds HTTP remote MCP |

### Retrieval and Agent

| Variable | Default | Description |
|---|---|---|
| `RETRIEVAL_TOP_K_SIMPLE` | 3 | single |
| `RETRIEVAL_TOP_K_COMPLEX` | 8 | multi |
| `RRF_K` | 60 | paper default, not a tuning conclusion |
| `RERANK_TOP_N` | 5 | |
| `MAX_RETRIEVAL_HOPS` | 3 | Self-RAG |
| `MAX_AGENT_STEPS` | 8 | |
| `MAX_TOOL_CALLS` | 6 | |
| `TOKEN_BUDGET` | 128000 | |
| `COMPRESS_SOFT_RATIO` | 0.50 | |
| `COMPRESS_HARD_RATIO` | 0.70 | |
| `AUTO_COMPACT_RATIO` | 0.85 | |
| `RATE_LIMIT_PER_MINUTE` | 60 | per `user_id` |
| `RETRIEVAL_CACHE_TTL_SECONDS` | 60 | policy questions |
| `ADMIN_API_TOKEN` | empty | required in production to enable admin |
| `KNOWLEDGE_DIR` | `knowledge` | supports `.md` `.pdf` `.docx` `.pptx` `.html` and common image extensions |

Full template: `.env.example` at the repository root.

## Capability Switches

| Condition | Behavior |
|---|---|
| No DeepSeek key | `FakeLLMProvider` |
| No embedding gateway and local dense model not loaded | `HashEmbeddingProvider` (CI placeholder) |
| `.[rerank]` not installed or weights fail to load | lexical rerank fallback; evaluation will not show `hybrid+cross-encoder` |
| `.[docs]` not installed, testing, and no `UNSTRUCTURED_FORCE` | Markdown heading chunking fallback; non-`.md` files skipped |
| Hugging Face timeout (mainland China) | set `HF_ENDPOINT=https://hf-mirror.com` |
| `MCP_ENABLED=false` | only the 15 business tools |
| No Redis | in-process rate limiting/caching |
| No Qdrant | in-memory vectors |

Container assembly: `build_container` in `app/services/container.py`.

---

Previous chapter [06](06-api-reference.md) · Next chapter [08 · Reliability](08-reliability.md)

The generic `LLM_*` variables take precedence over the legacy `DEEPSEEK_*` names. Keep one set configured. A provider must support the chat-completions endpoint and JSON object responses. No live generation provider has been verified in this checkout. `/capabilities` reports the selected model and whether retrieval is using a hash fallback.
