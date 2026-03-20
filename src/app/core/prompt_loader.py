from pathlib import Path

from app.core.schemas import PromptPath, PromptReference, PromptRenderRequest

# 获取prompts所在的路径
BASE_DIR = Path(__file__).resolve().parents[1]
PROMPTS_DIR = BASE_DIR / "prompts"


def _resolve_prompt_path(prompt: PromptReference | PromptPath) -> Path:
    relative_path = prompt.relative_path if isinstance(prompt, PromptReference) else prompt
    return PROMPTS_DIR / relative_path


# 加载prompt文件
def load_prompt(prompt: PromptReference | PromptPath) -> str:
    """读取 Prompt 文件内容"""
    path = _resolve_prompt_path(prompt)
    return path.read_text(encoding="utf-8").strip()


# 渲染prompt文件
def render_prompt(request: PromptRenderRequest) -> str:
    """读取 Prompt 文件并且做简单变量替换"""
    raw = load_prompt(request.prompt)

    # 把{{ var }} 转换为 $var，方便 Template 使用
    # 比如 kwargs是：{"name": "kaguya", "context": "你好！是kaguya哟！"}
    # 那么 {{name}} 就会被替换为 kaguya，{{context}} 就会被替换为 你好！是kaguya哟！
    for key, value in request.variables.items():
        placeholder = "{{" + key + "}}"
        raw = raw.replace(placeholder, str(value))
    return raw
