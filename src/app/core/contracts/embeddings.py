from typing import Protocol


class EmbeddingModel(Protocol):
    """Embedding 模型的抽象契约。"""

    def embed_query(self, text: str) -> list[float]:
        """对单条查询文本生成向量。"""

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """对多条文档文本批量生成向量。"""
