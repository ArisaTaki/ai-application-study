# AI Application Study

这是一个用于学习 AI 应用开发的 Python 项目仓库，当前主要用于练习：

- Python 基础项目结构
- LangChain 基础调用
- Prompt Template
- LCEL 链式写法
- 后续将逐步加入 Chroma、RAG、Memory、Agent 等内容

## 当前功能

目前已经实现：

- 基础项目结构拆分
- 使用 `ChatOpenAI` 调用模型
- 使用 `ChatPromptTemplate` 构建提示词
- 使用 LCEL (`prompt | llm | parser`) 组织调用链
- 基础聊天入口 `main.py`

## 项目结构

```text
src/
├─ main.py
└─ app/
   ├─ __init__.py
   ├─ chat/
   │  ├─ __init__.py
   │  ├─ engine.py
   │  └─ prompts.py
   └─ config/
      ├─ __init__.py
      └─ settings.py
```

环境准备

先创建虚拟环境并激活：

```bash
python3 -m venv .venv
source .venv/bin/activate
```

安装依赖：

```bash
pip install -r requirements.txt
```

环境变量

在项目根目录创建 .env 文件：

```bash
cp -r .env.example .env
```

# AI Application Study

这是一个用于学习 **AI 应用开发** 的 Python 项目仓库。  
当前主要用于练习：

- Python 项目结构
- LangChain 基础调用
- Prompt Template
- LCEL（LangChain Expression Language）
- LLM API 调用

后续将逐步加入：

- Chroma 向量数据库
- RAG（Retrieval-Augmented Generation）
- Memory（长期记忆）
- Agent
- 工具调用（Tools）

---

## 项目结构

```text
src/
├─ main.py
└─ app/
   ├─ __init__.py
   ├─ chat/
   │  ├─ __init__.py
   │  ├─ engine.py
   │  └─ prompts.py
   └─ config/
      ├─ __init__.py
      └─ settings.py
```

结构说明：

| 目录                     | 作用         |
| ------------------------ | ------------ |
| `main.py`                | 程序入口     |
| `app/chat`               | 聊天引擎     |
| `app/chat/prompts.py`    | Prompt 模板  |
| `app/config/settings.py` | 环境变量配置 |

---

## 环境准备

推荐使用 **Python 3.10+**

创建虚拟环境：

```bash
python3 -m venv .venv
```

激活虚拟环境：

Mac / Linux

```bash
source .venv/bin/activate
```

Windows

```bash
.venv\Scripts\activate
```

---

## 安装依赖

```bash
pip install -r requirements.txt
```

---

## 环境变量配置

在项目根目录创建 `.env` 文件：

```env
OPENAI_API_KEY=your_api_key
OPENAI_BASE_URL=your_api_base_url
OPENAI_MODEL=your_model_name
LANGCHAIN_AVAILABLE=true
```

说明：

| 变量                  | 作用               |
| --------------------- | ------------------ |
| `OPENAI_API_KEY`      | LLM API Key        |
| `OPENAI_BASE_URL`     | API 网关地址       |
| `OPENAI_MODEL`        | 使用的模型         |
| `LANGCHAIN_AVAILABLE` | 是否启用 LangChain |

---

## 运行项目

在项目根目录执行：

```bash
python3 src/main.py
```

---

## 当前实现

目前已经完成：

- Python 模块化项目结构
- LangChain ChatOpenAI 调用
- Prompt Template
- LCEL 链式调用

核心调用链：

```text
prompt | llm | parser
```

---

## 下一步学习计划

计划逐步加入：

### 1️⃣ 多轮对话

```text
history memory
```

### 2️⃣ 长期记忆

```text
vector store memory
```

### 3️⃣ 向量数据库

```text
Chroma
```

### 4️⃣ RAG

```text
embedding
retriever
rag chain
```

### 5️⃣ Agent

```text
tools
agent reasoning
```

---

## 学习目标

通过这个仓库逐步掌握：

- Python AI 项目结构
- LangChain 应用开发
- RAG 架构
- Agent 架构
- LLM 应用开发

---

## License

MIT
