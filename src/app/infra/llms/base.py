from abc import ABC, abstractmethod

from app.config.schemas import ChatModelConfig
from app.core.prompts import KAGUYA_SYSTEM_PROMPT
from app.core.schemas import EngineChatRequest, EngineChatResult


class BaseChatModelAdapter(ABC):
    """聊天模型适配器基类，约束统一初始化与调用流程。"""

    def __init__(self, config: ChatModelConfig, system_prompt: str | None = None):
        self.config = config
        self.system_prompt = system_prompt or KAGUYA_SYSTEM_PROMPT

        self._initialize()

    def _initialize(self) -> None:
        if not self.config.api_key or not self.config.enabled:
            self._reset_runtime()
            print("警告：缺少API Key或者LangChain不可用")
            return

        try:
            self._build_runtime()
            print("√ LangChain LCEL链初始化成功")
        except Exception as exc:
            self._reset_runtime()
            print(f"警告：LangChain 初始化失败：{exc}")

    @abstractmethod
    def _build_runtime(self) -> None:
        """构造底层运行时对象，例如 client / prompt / chain。"""

    @abstractmethod
    def _reset_runtime(self) -> None:
        """在初始化失败时重置运行时状态。"""

    @abstractmethod
    def run(self, request: EngineChatRequest) -> EngineChatResult:
        """执行一次结构化聊天调用。"""
