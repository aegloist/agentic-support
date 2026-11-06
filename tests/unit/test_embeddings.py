import httpx
import pytest

from app.config.settings import Settings
from app.core.exceptions import LLMProviderError
from app.providers.embeddings import (
    BgeM3EmbeddingProvider,
    HashEmbeddingProvider,
    OpenAICompatibleEmbeddingProvider,
    build_embedding_provider,
)


class _FakeSentenceTransformer:
    def get_sentence_embedding_dimension(self) -> int:
        return 4

    def encode(self, texts, normalize_embeddings=True, show_progress_bar=False):
        vectors = []
        for text in texts:
            hit = 1.0 if "return" in text.lower() else 0.0
            vectors.append([hit, 0.0, 0.0, 0.0])
        return vectors


def _settings(**overrides) -> Settings:
    data = {
        "app_env": "development",
        "local_embedding_enabled": True,
        "local_embedding_force": False,
        "embedding_dim": 512,
    }
    data.update(overrides)
    return Settings(**data)


@pytest.mark.asyncio
async def test_injected_bge_m3_encodes() -> None:
    provider = BgeM3EmbeddingProvider(_settings(), model=_FakeSentenceTransformer())
    assert provider.available
    assert provider.backend == "bge-small-en-v1.5"
    assert provider.dim == 4
    vectors = await provider.embed(["seven-day return", "shipping"])
    assert vectors[0][0] == 1.0
    assert vectors[1][0] == 0.0


@pytest.mark.asyncio
async def test_testing_env_skips_bge_m3_download() -> None:
    provider = BgeM3EmbeddingProvider(_settings(app_env="testing"))
    assert provider.available is False
    with pytest.raises(LLMProviderError):
        await provider.embed(["ping"])


@pytest.mark.asyncio
async def test_factory_uses_injected_bge_m3() -> None:
    provider = build_embedding_provider(_settings(), model=_FakeSentenceTransformer())
    assert provider.backend == "bge-small-en-v1.5"


@pytest.mark.asyncio
async def test_factory_falls_back_to_hash_in_testing() -> None:
    provider = build_embedding_provider(_settings(app_env="testing"))
    assert isinstance(provider, HashEmbeddingProvider)
    assert provider.backend == "hash"
    vectors = await provider.embed(["custom return"])
    assert len(vectors[0]) == 512


@pytest.mark.asyncio
async def test_backend_follows_local_model_id() -> None:
    provider = BgeM3EmbeddingProvider(
        _settings(local_embedding_model="BAAI/bge-m3"),
        model=_FakeSentenceTransformer(),
    )
    assert provider.backend == "bge-m3"


@pytest.mark.asyncio
async def test_remote_embedding_dimension_mismatch_fails_without_retry() -> None:
    calls = 0

    async def respond(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(
            200,
            json={"data": [{"index": 0, "embedding": [0.0] * 384}]},
        )

    settings = _settings(
        embedding_api_key="test-key",
        embedding_base_url="https://embeddings.example.test/v1",
        embedding_dim=512,
    )
    client = httpx.AsyncClient(
        base_url=settings.embedding_base_url,
        transport=httpx.MockTransport(respond),
    )
    provider = OpenAICompatibleEmbeddingProvider(settings, client=client)
    try:
        with pytest.raises(LLMProviderError, match="384 dims, expected 512.*EMBEDDING_DIM"):
            await provider.embed(["returns"])
    finally:
        await client.aclose()

    assert calls == 1
