from langchain_openai import OpenAIEmbeddings

from app.config.schemas import EmbeddingModelConfig
from app.infra.embeddings.base import BaseEmbeddingAdapter


class OpenAIEmbeddingModel(BaseEmbeddingAdapter):
    """基于 OpenAIEmbeddings 的具体 embedding 实现。"""

    def __init__(self, config: EmbeddingModelConfig):
        self.client: OpenAIEmbeddings | None = None
        super().__init__(config=config)

    def _build_runtime(self) -> None:
        if self.config.base_url:
            self.client = OpenAIEmbeddings(
                model=self.config.model,
                base_url=self.config.base_url,
            )
            return

        self.client = OpenAIEmbeddings(model=self.config.model)

    def _reset_runtime(self) -> None:
        self.client = None

    def embed_query(self, text: str) -> list[float]:
        if self.client is None:
            raise RuntimeError("Embedding 模型未初始化成功")
        return self.client.embed_query(text)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if self.client is None:
            raise RuntimeError("Embedding 模型未初始化成功")
        return self.client.embed_documents(texts)
