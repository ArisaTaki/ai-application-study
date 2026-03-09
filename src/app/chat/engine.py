from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from app.config.settings import Settings
from app.chat.prompts import KAGUYA_SYSTEM_PROMPT

class Engine:
    def __init__(self):
        settings = Settings()

        self.api_key = settings.api_key
        self.model = settings.model
        self.api_base_url = settings.api_base_url
        self.langchain_available = settings.langchain_available

        self.llm = None
        self.chain = None

        if self.api_key and self.langchain_available:
            try:
                # 1. 初始化模型
                # 通过Langchain的chatOpenAI组件，利用第三方API平台
                kwargs = {
                    "model": self.model,
                    "temperature": 0.7,
                    "api_key": self.api_key,
                }
                if self.api_base_url:
                    kwargs["base_url"] = self.api_base_url
                    
                self.llm = ChatOpenAI(**kwargs)

                # 2. 定义AI人格和行为准则（提示词模板）
                self.template = """{system_prompt}
                                {{long_term_memory}}
                                对话历史：{{history}}
                                用户：{{input}}
                                kaguya：""".format(system_prompt=KAGUYA_SYSTEM_PROMPT)
                
                # 3. 创建提示词模板和链（LCEL 表达式）
                self.prompt = ChatPromptTemplate.from_template(self.template)
                self.out_parser = StrOutputParser()
                # 构建链：chain = prompt | model | output_parser
                self.chain = self.prompt | self.llm | self.out_parser
                print("√ LangChain LCEL链初始化成功")
            except Exception as e:
                print("警告： LangChain 初始化失败，将使用传统方式：{}".format(e))
                self.llm = None
                self.chain = None
        else:
            print("警告：缺少API Key或者LangChain不可用")

    def chat(self, user_input: str, history: str = "", long_term_memory: str = "") -> str:
        if not self.chain:
            return "模型未初始化成功"    
        return self.chain.invoke({
            "input": user_input,
            "history": history,
            "long_term_memory": long_term_memory,
        })
        