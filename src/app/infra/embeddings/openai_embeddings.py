from langchain_openai import OpenAIEmbeddings

from app.config.settings import load_settings


def build_openai_embeddings(model: str = "text-embedding-3-small") -> OpenAIEmbeddings:
    """构造默认 OpenAI embeddings 实例。"""
    settings = load_settings()

    if settings.api_base_url:
        return OpenAIEmbeddings(model=model, base_url=settings.api_base_url)
    return OpenAIEmbeddings(model=model)
