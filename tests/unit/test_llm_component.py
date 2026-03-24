"""Week 2 — LLMComponent and EmbeddingComponent tests."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from argus.settings.settings import Settings, LLMSettings, EmbeddingSettings


# ── LLMComponent ──────────────────────────────────────────────────────────────

def test_llm_component_builds_openai():
    """LLMComponent instantiates ChatOpenAI when mode=openai."""
    from argus.components.llm.llm_component import LLMComponent
    s = Settings(llm=LLMSettings(mode="openai", model="gpt-4o"))
    with patch("langchain_openai.ChatOpenAI") as MockChatOpenAI:
        MockChatOpenAI.return_value = MagicMock()
        llm = LLMComponent(s)
        assert llm.mode == "openai"
        assert llm.model_name == "gpt-4o"


def test_llm_component_raises_on_unknown_mode():
    """LLMComponent raises ValueError for unsupported mode."""
    from argus.components.llm.llm_component import LLMComponent
    s = Settings(llm=LLMSettings(mode="unknown_provider"))
    with pytest.raises(ValueError, match="Unknown LLM mode"):
        LLMComponent(s)


@pytest.mark.asyncio
async def test_achat_returns_string():
    """achat returns the content string from the LLM response."""
    from argus.components.llm.llm_component import LLMComponent
    s = Settings(llm=LLMSettings(mode="openai"))
    mock_response = MagicMock()
    mock_response.content = "Campaign ROAS was 4.2x"

    with patch("langchain_openai.ChatOpenAI") as MockChatOpenAI:
        mock_client = AsyncMock()
        mock_client.ainvoke = AsyncMock(return_value=mock_response)
        MockChatOpenAI.return_value = mock_client
        llm = LLMComponent(s)
        result = await llm.achat([{"role": "user", "content": "What was ROAS?"}])
        assert result == "Campaign ROAS was 4.2x"


@pytest.mark.asyncio
async def test_acomplete_wraps_achat():
    """acomplete is a convenience wrapper over achat."""
    from argus.components.llm.llm_component import LLMComponent
    s = Settings(llm=LLMSettings(mode="openai"))
    mock_response = MagicMock()
    mock_response.content = "Answer"

    with patch("langchain_openai.ChatOpenAI") as MockChatOpenAI:
        mock_client = AsyncMock()
        mock_client.ainvoke = AsyncMock(return_value=mock_response)
        MockChatOpenAI.return_value = mock_client
        llm = LLMComponent(s)
        result = await llm.acomplete("Summarise this campaign.")
        assert result == "Answer"
        # Verify it was called with a single user message
        called_messages = mock_client.ainvoke.call_args[0][0]
        assert called_messages[-1].content == "Summarise this campaign."


# ── EmbeddingComponent ────────────────────────────────────────────────────────

def test_embedding_component_loads():
    """EmbeddingComponent loads with correct dimensions."""
    from argus.components.embedding.embedding_component import EmbeddingComponent
    s = Settings(embedding=EmbeddingSettings(
        model_name="nomic-ai/nomic-embed-text-v1.5",
        dimensions=768,
    ))
    mock_model = MagicMock()
    with patch("sentence_transformers.SentenceTransformer", return_value=mock_model):
        emb = EmbeddingComponent(s)
        assert emb.dimensions == 768
        assert emb.model_name == "nomic-ai/nomic-embed-text-v1.5"
        assert emb.model is mock_model


@pytest.mark.asyncio
async def test_embed_returns_list_of_floats():
    """embed() returns a list of floats of the correct dimension."""
    import numpy as np
    from argus.components.embedding.embedding_component import EmbeddingComponent
    s = Settings(embedding=EmbeddingSettings(dimensions=768))

    mock_model = MagicMock()
    mock_model.encode.return_value = np.zeros(768)

    with patch("sentence_transformers.SentenceTransformer", return_value=mock_model):
        emb = EmbeddingComponent(s)
        vector = await emb.embed("test query")
        assert isinstance(vector, list)
        assert len(vector) == 768


@pytest.mark.asyncio
async def test_embed_batch_returns_matrix():
    """embed_batch() returns a list of vectors."""
    import numpy as np
    from argus.components.embedding.embedding_component import EmbeddingComponent
    s = Settings(embedding=EmbeddingSettings(dimensions=768))

    mock_model = MagicMock()
    mock_model.encode.return_value = np.zeros((3, 768))

    with patch("sentence_transformers.SentenceTransformer", return_value=mock_model):
        emb = EmbeddingComponent(s)
        vectors = await emb.embed_batch(["a", "b", "c"])
        assert len(vectors) == 3


def test_di_resolves_llm_and_embedding():
    """DI container resolves LLMComponent and EmbeddingComponent as singletons."""
    from argus.di import get_injector
    from argus.components.llm.llm_component import LLMComponent
    from argus.components.embedding.embedding_component import EmbeddingComponent

    mock_model = MagicMock()
    with patch("sentence_transformers.SentenceTransformer", return_value=mock_model), \
         patch("langchain_openai.ChatOpenAI", return_value=MagicMock()):
        injector = get_injector()
        llm = injector.get(LLMComponent)
        emb = injector.get(EmbeddingComponent)
        assert isinstance(llm, LLMComponent)
        assert isinstance(emb, EmbeddingComponent)
        # Verify singletons — same instance returned twice
        assert injector.get(LLMComponent) is llm
        assert injector.get(EmbeddingComponent) is emb
