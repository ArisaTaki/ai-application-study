from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableSerializable
from langchain_openai import ChatOpenAI

from app.config.schemas import ChatModelConfig
from app.core.schemas import EngineChatRequest, EngineChatResult
from app.infra.llms.base import BaseChatModelAdapter


class OpenAIChatModel(BaseChatModelAdapter):
    """基于 ChatOpenAI 的具体聊天模型实现。"""

    def __init__(self, config: ChatModelConfig, system_prompt: str | None = None):
        self.llm: ChatOpenAI | None = None
        self.prompt: ChatPromptTemplate | None = None
        self.out_parser: StrOutputParser | None = None
        self.chain: RunnableSerializable[dict[str, str], str] | None = None
        self.template: str = ""

        super().__init__(config=config, system_prompt=system_prompt)

    def _build_runtime(self) -> None:
        self.llm = self._build_llm()
        self.template = self._build_template()
        self.prompt = ChatPromptTemplate.from_template(self.template)
        self.out_parser = StrOutputParser()
        self.chain = self.prompt | self.llm | self.out_parser

    def _reset_runtime(self) -> None:
        self.llm = None
        self.prompt = None
        self.out_parser = None
        self.chain = None
        self.template = ""

    def _build_llm(self) -> ChatOpenAI:
        if self.config.base_url:
            return ChatOpenAI(
                model=self.config.model,
                temperature=self.config.temperature,
                base_url=self.config.base_url,
            )
        return ChatOpenAI(
            model=self.config.model,
            temperature=self.config.temperature,
        )

    def _build_template(self) -> str:
        return (
            f"系统设定：\n{self.system_prompt}\n\n"
            "长期记忆：\n{long_term_memory}\n\n"
            "对话历史：\n{history}\n\n"
            "当前用户输入：\n{input}\n\n"
            "kaguya："
        )

    def run(self, request: EngineChatRequest) -> EngineChatResult:
        if not self.chain:
            return EngineChatResult(
                text="模型未初始化成功",
                error="engine_not_initialized",
            )

        output = self.chain.invoke(
            {
                "input": request.user_input,
                "history": request.history,
                "long_term_memory": request.long_term_memory,
            }
        )
        return EngineChatResult(text=output)
