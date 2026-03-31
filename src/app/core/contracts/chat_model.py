from typing import Protocol

from app.core.schemas import EngineChatRequest, EngineChatResult


class ChatModel(Protocol):
    """聊天模型的抽象契约。"""

    def run(self, request: EngineChatRequest) -> EngineChatResult:
        """执行一次结构化聊天调用。"""
