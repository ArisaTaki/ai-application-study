from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableSerializable
from langchain_openai import ChatOpenAI

from app.config.settings import load_settings
from app.core.prompts import KAGUYA_SYSTEM_PROMPT
from app.core.schemas import EngineChatRequest, EngineChatResult


class OpenAIChatModel:
    """基于 ChatOpenAI 的具体聊天模型实现。"""

    def __init__(self, system_prompt: str | None = None, temperature: float = 0.7):
        settings = load_settings()

        self.api_key = settings.api_key
        self.model = settings.model
        self.api_base_url = settings.api_base_url
        self.langchain_available = settings.langchain_available

        self.system_prompt = system_prompt or KAGUYA_SYSTEM_PROMPT
        self.temperature = temperature

        self.llm: ChatOpenAI | None = None
        self.prompt: ChatPromptTemplate | None = None
        self.out_parser: StrOutputParser | None = None
        self.chain: RunnableSerializable[dict[str, str], str] | None = None
        self.template: str = ""

        self._initialize()

    def _initialize(self) -> None:
        if not self.api_key or not self.langchain_available:
            print("警告：缺少API Key或者LangChain不可用")
            return

        try:
            self.llm = self._build_llm()
            self.template = self._build_template()
            self.prompt = ChatPromptTemplate.from_template(self.template)
            self.out_parser = StrOutputParser()
            self.chain = self.prompt | self.llm | self.out_parser
            print("√ LangChain LCEL链初始化成功")
        except Exception as exc:
            print(f"警告：LangChain 初始化失败：{exc}")
            self.llm = None
            self.prompt = None
            self.out_parser = None
            self.chain = None
            self.template = ""

    def _build_llm(self) -> ChatOpenAI:
        if self.api_base_url:
            return ChatOpenAI(
                model=self.model,
                temperature=self.temperature,
                base_url=self.api_base_url,
            )
        return ChatOpenAI(model=self.model, temperature=self.temperature)

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
