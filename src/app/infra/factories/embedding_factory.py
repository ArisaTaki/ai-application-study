from langchain_openai import OpenAIEmbeddings

from app.infra.embeddings.openai_embeddings import build_openai_embeddings


def build_embeddings(model: str = "text-embedding-3-small") -> OpenAIEmbeddings:
    """构造默认 embedding 实现。"""
    return build_openai_embeddings(model=model)
