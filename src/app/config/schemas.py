from dataclasses import dataclass
import os
from typing import Literal, TypeAlias


ModelUseCase: TypeAlias = Literal["chat", "judge", "rag", "memory", "agent"]


@dataclass(slots=True)
class ChatModelConfig:
    """聊天模型运行时配置。"""

    provider: str
    # 模型供应商标识，例如 openai。

    model: str
    # 实际使用的模型名称。

    api_key: str | None
    # 调用模型时使用的 API Key。

    base_url: str | None
    # 模型服务地址；未配置时使用默认地址。

    temperature: float = 0.7
    # 默认采样温度。

    enabled: bool = True
    # 当前模型能力是否启用。


@dataclass(slots=True)
class EmbeddingModelConfig:
    """Embedding 模型运行时配置。"""

    provider: str
    # Embedding 供应商标识，例如 openai。

    model: str
    # 实际使用的 embedding 模型名称。

    api_key: str | None
    # 调用 embedding 服务时使用的 API Key。

    base_url: str | None
    # embedding 服务地址；未配置时使用默认地址。

    enabled: bool = True
    # 当前 embedding 能力是否启用。


@dataclass(slots=True)
class AppSettings:
    """项目运行时使用的统一配置对象。"""

    api_key: str | None
    # 调用模型时使用的 API Key；本地未配置时可能为 None。

    default_model: str
    # 默认模型名称，其他业务场景未单独指定时使用。

    chat_model: str
    # chat 场景默认模型。

    judge_model: str
    # judge 场景默认模型。

    rag_model: str
    # RAG 场景默认模型。

    memory_model: str
    # memory 场景默认模型。

    agent_model: str
    # agent 场景默认模型。

    api_base_url: str | None
    # 可选的 OpenAI 兼容服务地址；未配置时走官方默认地址。

    provider: str
    # 默认模型供应商，当前先支持 openai。

    embedding_provider: str
    # 默认 embedding 供应商，当前先支持 openai。

    default_embedding_model: str
    # 默认 embedding 模型名称。

    rag_embedding_model: str
    # RAG 场景默认 embedding 模型。

    memory_embedding_model: str
    # memory 场景默认 embedding 模型。

    langchain_available: bool
    # 是否允许初始化 LangChain 调用链；便于本地临时关闭模型调用。

    @classmethod
    def from_env(cls) -> "AppSettings":
        """从环境变量读取配置，并构造成结构化设置对象。"""
        default_model = os.getenv("OPENAI_MODEL", "gpt-5-nano-2025-08-07")
        default_embedding_model = os.getenv(
            "OPENAI_EMBEDDING_MODEL",
            "text-embedding-3-small",
        )
        return cls(
            api_key=os.getenv("OPENAI_API_KEY"),
            default_model=default_model,
            chat_model=os.getenv("OPENAI_CHAT_MODEL", default_model),
            judge_model=os.getenv("OPENAI_JUDGE_MODEL", default_model),
            rag_model=os.getenv("OPENAI_RAG_MODEL", default_model),
            memory_model=os.getenv("OPENAI_MEMORY_MODEL", default_model),
            agent_model=os.getenv("OPENAI_AGENT_MODEL", default_model),
            api_base_url=os.getenv("OPENAI_BASE_URL"),
            provider=os.getenv("LLM_PROVIDER", "openai"),
            embedding_provider=os.getenv("EMBEDDING_PROVIDER", "openai"),
            default_embedding_model=default_embedding_model,
            rag_embedding_model=os.getenv(
                "OPENAI_RAG_EMBEDDING_MODEL",
                default_embedding_model,
            ),
            memory_embedding_model=os.getenv(
                "OPENAI_MEMORY_EMBEDDING_MODEL",
                default_embedding_model,
            ),
            langchain_available=os.getenv("LANGCHAIN_AVAILABLE", "true").lower() == "true",
        )

    def chat_model_config(
        self,
        use_case: ModelUseCase = "chat",
        temperature: float = 0.7,
    ) -> ChatModelConfig:
        """按业务场景生成聊天模型配置。"""
        model_by_use_case = {
            "chat": self.chat_model,
            "judge": self.judge_model,
            "rag": self.rag_model,
            "memory": self.memory_model,
            "agent": self.agent_model,
        }
        return ChatModelConfig(
            provider=self.provider,
            model=model_by_use_case[use_case],
            api_key=self.api_key,
            base_url=self.api_base_url,
            temperature=temperature,
            enabled=self.langchain_available,
        )

    def embedding_model_config(
        self,
        use_case: Literal["rag", "memory"] = "rag",
    ) -> EmbeddingModelConfig:
        """按业务场景生成 embedding 模型配置。"""
        model_by_use_case = {
            "rag": self.rag_embedding_model,
            "memory": self.memory_embedding_model,
        }
        return EmbeddingModelConfig(
            provider=self.embedding_provider,
            model=model_by_use_case[use_case],
            api_key=self.api_key,
            base_url=self.api_base_url,
            enabled=self.langchain_available,
        )
