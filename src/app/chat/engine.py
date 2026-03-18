from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from typing import Any

from app.config.settings import Settings
from app.chat.prompts import KAGUYA_SYSTEM_PROMPT

class Engine:
    def __init__(self, system_prompt: str | None = None, temperature: float = 0.7):
        # 导入settings数据
        settings = Settings()

        # 将settings数据绑定到self上
        self.api_key = settings.api_key
        self.model = settings.model
        self.api_base_url = settings.api_base_url
        self.langchain_available = settings.langchain_available

        # 允许外部覆盖 system prompt / temperature，默认仍兼容现有 Kaguya 逻辑
        self.system_prompt = system_prompt or KAGUYA_SYSTEM_PROMPT
        self.temperature = temperature

        # 先声明LangChain需要的三个东西：llm，prompt，output_parser
        self.llm: ChatOpenAI | None = None
        self.prompt: ChatPromptTemplate | None = None
        self.out_parser: StrOutputParser | None = None
        # chain 就是把llm，prompt，output_parser组合起来
        self.chain: Any | None = None
        # template 就是prompt的模板
        self.template: str = ""

        self._initialize()

    def _initialize(self) -> None:
        """初始化模型与 LCEL 链。"""
        if not self.api_key or not self.langchain_available:
            print("警告：缺少API Key或者LangChain不可用")
            return

        try:
            # 先初始化llm
            self.llm = self._build_llm()
            # 再初始化template
            self.template = self._build_template()
            # 再初始化prompt，通过template创建
            self.prompt = ChatPromptTemplate.from_template(self.template)
            # 再初始化output_parser
            self.out_parser = StrOutputParser()
            # 最后初始化chain
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
        return (
            f"系统设定：\n{self.system_prompt}\n\n"
            "长期记忆：\n{long_term_memory}\n\n"
            "对话历史：\n{history}\n\n"
            "当前用户输入：\n{input}\n\n"
            "kaguya："
        )

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