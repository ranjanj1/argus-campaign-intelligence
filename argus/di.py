from __future__ import annotations

from injector import Injector, Module, provider, singleton

from argus.settings.settings import Settings
from argus.settings.settings_loader import load_settings
from argus.components.llm.llm_component import LLMComponent
from argus.components.embedding.embedding_component import EmbeddingComponent
from argus.components.vector_store.vector_store_component import VectorStoreComponent
from argus.components.graph_store.graph_store_component import GraphStoreComponent
from argus.components.prompt_manager.prompt_manager import PromptManager
from argus.components.cache.semantic_cache import SemanticCache
from argus.components.ingest.ingest_component import IngestComponent
from argus.components.guardrails.guardrail_component import GuardrailComponent


class ArgusModule(Module):
    """
    DI bindings for singleton application components.

    Note: skills.py and auth.py are stateless utilities — they call
    get_settings() directly and do not need DI providers.

    Components registered so far:
      ✅ Settings
      ✅ LLMComponent
      ✅ EmbeddingComponent
      ✅ VectorStoreComponent
      ✅ GraphStoreComponent
      ✅ PromptManager
      ✅ SemanticCache
      ✅ IngestComponent
      ✅ GuardrailComponent
    """

    def __init__(self) -> None:
        self._settings = load_settings()

    @provider
    @singleton
    def provide_settings(self) -> Settings:
        return self._settings

    @provider
    @singleton
    def provide_llm(self, settings: Settings) -> LLMComponent:
        return LLMComponent(settings)

    @provider
    @singleton
    def provide_embedding(self, settings: Settings) -> EmbeddingComponent:
        return EmbeddingComponent(settings)

    @provider
    @singleton
    def provide_vector_store(
        self, settings: Settings, embedder: EmbeddingComponent
    ) -> VectorStoreComponent:
        return VectorStoreComponent(settings, embedder)

    @provider
    @singleton
    def provide_graph_store(self, settings: Settings) -> GraphStoreComponent:
        return GraphStoreComponent(settings)

    @provider
    @singleton
    def provide_prompt_manager(self) -> PromptManager:
        return PromptManager()

    @provider
    @singleton
    def provide_semantic_cache(
        self, settings: Settings, embedder: EmbeddingComponent
    ) -> SemanticCache:
        return SemanticCache(settings, embedder)

    @provider
    @singleton
    def provide_ingest(
        self,
        settings: Settings,
        embedder: EmbeddingComponent,
        vector_store: VectorStoreComponent,
        graph_store: GraphStoreComponent,
    ) -> IngestComponent:
        return IngestComponent(settings, embedder, vector_store, graph_store)

    @provider
    @singleton
    def provide_guardrails(self, settings: Settings) -> GuardrailComponent:
        return GuardrailComponent(settings.guardrails)


_injector: Injector | None = None


def get_injector() -> Injector:
    global _injector
    if _injector is None:
        _injector = Injector([ArgusModule()])
    return _injector


# Convenience accessor — used by route handlers and ARQ worker
def get_settings() -> Settings:
    return get_injector().get(Settings)
