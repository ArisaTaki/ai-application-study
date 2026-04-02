from abc import ABC, abstractmethod

from app.config.schemas import EmbeddingModelConfig


class BaseEmbeddingAdapter(ABC):
    """Embedding 模型适配器基类，约束统一初始化流程。"""

    def __init__(self, config: EmbeddingModelConfig):
        self.config = config
        self._initialize()

    def _initialize(self) -> None:
        if not self.config.api_key or not self.config.enabled:
            self._reset_runtime()
            print("警告：缺少API Key或者Embedding能力不可用")
            return

        try:
            self._build_runtime()
        except Exception as exc:
            self._reset_runtime()
            print(f"警告：Embedding 初始化失败：{exc}")

    @abstractmethod
    def _build_runtime(self) -> None:
        """构造底层 embedding 运行时对象。"""

    @abstractmethod
    def _reset_runtime(self) -> None:
        """在初始化失败时重置运行时状态。"""
