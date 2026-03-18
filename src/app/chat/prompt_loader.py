from pathlib import Path

# 获取prompts所在的路径
BASE_DIR = Path(__file__).resolve().parents[1]
PROMPTS_DIR = BASE_DIR / "prompts"

# 加载prompt文件
def load_prompt(relative_path: str) -> str:
    """读取 Prompt 文件内容"""
    path = PROMPTS_DIR / relative_path
    return path.read_text(encoding="utf-8").strip()

# 渲染prompt文件
def render_prompt(relative_path: str, **kwargs) -> str:
    """读取 Prompt 文件并且做简单变量替换"""
    raw = load_prompt(relative_path)

    # 把{{ var }} 转换为 $var，方便 Template 使用
    # 比如 kwargs是：{"name": "kaguya", "context": "你好！是kaguya哟！"}
    # 那么 {{name}} 就会被替换为 kaguya，{{context}} 就会被替换为 你好！是kaguya哟！
    for key, value in kwargs.items():
        placeholder = "{{" + key + "}}"
        raw = raw.replace(placeholder, str(value))
    return raw