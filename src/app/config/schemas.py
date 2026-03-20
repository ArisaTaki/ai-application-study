from dataclasses import dataclass
import os


@dataclass(slots=True)
class AppSettings:
    """项目运行时使用的统一配置对象。"""

    api_key: str | None
    # 调用模型时使用的 API Key；本地未配置时可能为 None。

    model: str
    # 当前默认使用的模型名称。

    api_base_url: str | None
    # 可选的 OpenAI 兼容服务地址；未配置时走官方默认地址。

    langchain_available: bool
    # 是否允许初始化 LangChain 调用链；便于本地临时关闭模型调用。

    @classmethod
    def from_env(cls) -> "AppSettings":
        """从环境变量读取配置，并构造成结构化设置对象。"""
        return cls(
            api_key=os.getenv("OPENAI_API_KEY"),
            model=os.getenv("OPENAI_MODEL", "gpt-5-nano-2025-08-07"),
            api_base_url=os.getenv("OPENAI_BASE_URL"),
            langchain_available=os.getenv("LANGCHAIN_AVAILABLE", "true").lower() == "true",
        )
