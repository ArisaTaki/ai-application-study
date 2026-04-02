from typing import Literal

from app.config.schemas import EmbeddingModelConfig
from app.config.settings import load_settings
from app.core.contracts.embeddings import EmbeddingModel
from app.infra.embeddings.openai_embeddings import OpenAIEmbeddingModel


def build_embeddings(
    use_case: Literal["rag", "memory"] = "rag",
    config: EmbeddingModelConfig | None = None,
) -> EmbeddingModel:
    """构造默认 embedding 实现。"""
    resolved_config = config or load_settings().embedding_model_config(use_case=use_case)

    if resolved_config.provider != "openai":
        raise ValueError(f"Unsupported embedding provider: {resolved_config.provider}")

    return OpenAIEmbeddingModel(config=resolved_config)
