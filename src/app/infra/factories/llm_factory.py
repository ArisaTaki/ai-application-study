from app.core.contracts.chat_model import ChatModel
from app.infra.llms.openai_chat_model import OpenAIChatModel


def build_chat_model(
    system_prompt: str | None = None,
    temperature: float = 0.7,
) -> ChatModel:
    """构造默认聊天模型实现。"""
    return OpenAIChatModel(system_prompt=system_prompt, temperature=temperature)
