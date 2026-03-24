from __future__ import annotations

from typing import List

from pydantic import BaseModel, ConfigDict, Field
from pydantic_settings import BaseSettings


class LLMSettings(BaseModel):
    mode: str = "openai"          # openai | gemini | bedrock | ollama
    model: str = "gpt-4o"
    temperature: float = 0.1
    max_tokens: int = 2048


class EmbeddingSettings(BaseModel):
    provider: str = "huggingface"
    model_name: str = "nomic-ai/nomic-embed-text-v1.5"
    dimensions: int = 768


class PGVectorSettings(BaseModel):
    host: str = "localhost"
    port: int = 5432
    database: str = "argus"
    user: str = "argus"
    password: str = "argus"
    tables: List[str] = [
        "campaign_performance",
        "ad_copy_library",
        "audience_segments",
        "client_strategy_briefs",
        "monthly_reports",
        "budget_allocations",
    ]

    @property
    def url(self) -> str:
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"

    @property
    def sync_url(self) -> str:
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"


class Neo4jSettings(BaseModel):
    uri: str = "bolt://localhost:7687"
    user: str = "neo4j"
    password: str = "argus"


class RedisSettings(BaseModel):
    host: str = "localhost"
    port: int = 6379
    session_ttl: int = 1800           # 30 minutes
    session_max_messages: int = 20
    cache_ttl: int = 3600             # semantic cache 1 hour
    cache_similarity_threshold: float = 0.92

    @property
    def url(self) -> str:
        return f"redis://{self.host}:{self.port}"


class RateLimitSettings(BaseModel):
    requests_per_minute: int = 20
    requests_per_day: int = 500


class TokenBudgetSettings(BaseModel):
    total_context: int = 120_000      # gpt-4o context window
    system_prompt_reserve: int = 2_000
    history_reserve: int = 8_000
    chunks_reserve: int = 20_000
    # remainder is available for LLM output


class GuardrailSettings(BaseModel):
    # Master switch — set to false to bypass all guardrails
    enabled: bool = True

    # ── Input checks ──────────────────────────────────────────────────────────
    input_toxicity: bool = True
    input_toxicity_threshold: float = 0.75   # fraction of toxic tokens to block

    ban_topics: bool = True
    ban_topics_list: List[str] = Field(default_factory=lambda: [
        "competitor", "lawsuit", "litigation", "confidential",
        "hack", "exploit", "bypass", "jailbreak",
    ])

    anonymize_pii: bool = True   # replaces email/phone/SSN in query before processing

    token_limit: bool = True
    token_limit_max: int = 10_000   # max input tokens; blocks if exceeded

    # ── Output checks ─────────────────────────────────────────────────────────
    output_toxicity: bool = True
    output_toxicity_threshold: float = 0.70

    client_isolation: bool = True   # block if any retrieved chunk belongs to another client


class AuthSettings(BaseModel):
    enabled: bool = True
    # HS256 local signing — set JWT_SECRET in .env; defaults to dev key
    jwt_secret: str = "dev-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    # Default identity injected when auth is disabled (develop profile)
    default_skill: str = "all_campaigns"
    default_client_id: str = "internal"


class Settings(BaseSettings):
    llm: LLMSettings = LLMSettings()
    embedding: EmbeddingSettings = EmbeddingSettings()
    pgvector: PGVectorSettings = PGVectorSettings()
    neo4j: Neo4jSettings = Neo4jSettings()
    redis: RedisSettings = RedisSettings()
    rate_limit: RateLimitSettings = RateLimitSettings()
    token_budget: TokenBudgetSettings = TokenBudgetSettings()
    auth: AuthSettings = AuthSettings()
    guardrails: GuardrailSettings = GuardrailSettings()

    model_config = ConfigDict(extra="ignore")
