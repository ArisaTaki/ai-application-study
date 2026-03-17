from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from typing import Any

from app.config.settings import Settings
from app.chat.prompts import KAGUYA_SYSTEM_PROMPT

class Engine:
    def __init__(self, system_prompt: str | None = None, temperature: float = 0.7):
        settings = Settings()

        self.api_key = settings.api_key
        self.model = settings.model
        self.api_base_url = settings.api_base_url
        self.langchain_available = settings.langchain_available

        # 允许外部覆盖 system prompt / temperature，默认仍兼容现有 Kaguya 逻辑
        self.system_prompt = system_prompt or KAGUYA_SYSTEM_PROMPT
        self.temperature = temperature

        self.llm: ChatOpenAI | None = None
        self.prompt: ChatPromptTemplate | None = None
        self.out_parser: StrOutputParser | None = None
        self.chain: Any | None = None
        self.template: str = ""

        self._initialize()

    def _initialize(self) -> None:
        """初始化模型与 LCEL 链。"""
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
        except Exception as e:
            print(f"警告：LangChain 初始化失败：{e}")
            self.llm = None
            self.prompt = None
            self.out_parser = None
            self.chain = None
            self.template = ""

    def _build_llm(self) -> ChatOpenAI:
        """构造底层 LLM 实例。"""
        kwargs = {
            "model": self.model,
            "temperature": self.temperature,
            "api_key": self.api_key,
        }
        if self.api_base_url:
            kwargs["base_url"] = self.api_base_url

        return ChatOpenAI(**kwargs)

    def _build_template(self) -> str:
        """构造统一提示词模板。"""
        return f"""{self.system_prompt}
        {{long_term_memory}}
        对话历史：{{history}}
        用户：{{input}}
        kaguya："""

    def chat(self, user_input: str, history: str = "", long_term_memory: str = "") -> str:
        """执行一次对话调用。"""
        if not self.chain:
            return "模型未初始化成功"

        return self.chain.invoke(
            {
                "input": user_input,
                "history": history,
                "long_term_memory": long_term_memory,
            }
        )