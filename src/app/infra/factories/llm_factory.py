from app.config.schemas import ChatModelConfig, ModelUseCase
from app.config.settings import load_settings
from app.core.contracts.chat_model import ChatModel
from app.infra.llms.openai_chat_model import OpenAIChatModel


def build_chat_model(
    use_case: ModelUseCase = "chat",
    system_prompt: str | None = None,
    temperature: float = 0.7,
    config: ChatModelConfig | None = None,
) -> ChatModel:
    """构造默认聊天模型实现。"""
    resolved_config = config or load_settings().chat_model_config(
        use_case=use_case,
        temperature=temperature,
    )

    if resolved_config.provider != "openai":
        raise ValueError(f"Unsupported chat model provider: {resolved_config.provider}")

    return OpenAIChatModel(config=resolved_config, system_prompt=system_prompt)
