import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Any

# ===================
# 1. 路径基础配置
# ===================

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
APP_DIR = SRC_DIR / "app"
PROMPTS_ROOT = APP_DIR / "prompts"
TEST_CASES_ROOT = PROJECT_ROOT / "tests" / "prompt_cases"
OUTPUT_DIR = PROJECT_ROOT / "tests" / "outputs"

# 让脚本可以import src 下的模块
sys.path.append(str(SRC_DIR))

from app.chat.prompt_loader import load_prompt
from app.chat.engine import Engine

# ===================
# 2. 数据结构定义
# ===================

@dataclass
class PromptVariant:
    name: str
    relative_path: str
    content: str

# ===================
# 3. 发现 prompt group 下的 ab版本
# ===================

def discover_prompt_variants(group: str) -> list[PromptVariant]:
    """
    根据group（比如system/kaguya）自动发现该目录下所有ab_*.md文件
    """
    group_dir = PROMPTS_ROOT / group

    if not group_dir.exists():
        raise FileNotFoundError(f"Prompt group directory not found: {group_dir}")
    
    if not group_dir.is_dir():
        raise ValueError(f"Prompt group is not a directory: {group_dir}")
    
    variants = []
    for path in sorted(group_dir.glob("ab_*.md")):
        variant_name = path.stem # ab_v1, ab_v2, ...
        relative_path = str(path.relative_to(PROMPTS_ROOT))
        content = load_prompt(relative_path)
        variants.append(
            PromptVariant(
                name = variant_name,
                relative_path = relative_path,
                content = content
            )
        )
    
    if not variants:
        raise ValueError(f"No ab_*.md variants found in {group_dir}")
    
    return variants

# ===================
# 4. 自动匹配测试样本文件
# ===================

def resolve_test_case_file(group: str) -> Path:
    """
    group = system/kaguya
    -> tests/prompt_cases/system/kaguya.json
    """
    case_file = TEST_CASES_ROOT / f"{group}.json"

    if not case_file.exists():
        raise FileNotFoundError(f"Test case file not found: {case_file}")

    return case_file

def load_test_cases(case_file: Path) -> list[dict]:
    with open(case_file, "r", encoding="utf-8") as f:
        return json.load(f)

# ===================
# 5. 这里是模型调用
# ===================

# Deleted call_llm function as per instructions

def build_engine_for_variant(variant: PromptVariant, temperature: float | None = None) -> Engine:
    """
    为某个 prompt 版本预先构建 Engine。

    这样每个 variant 只初始化一次模型链，避免在每个 case 上重复初始化。
    """
    return Engine(
        system_prompt=variant.content,
        temperature=temperature if temperature is not None else 0.7,
    )


def run_with_engine(engine: Engine, messages: list[dict[str, str]]) -> str:
    """
    使用已经初始化好的 Engine 执行一次调用。

    约定：
    - 第一条 system message 仅用于构建 Engine，因此这里不再重复传入。
    - 最后一条 user message 作为当前用户输入。
    - 其他消息尽量拼接到 history 中。
    """
    history_parts: list[str] = []
    user_input = ""

    for i, message in enumerate(messages):
        role = message.get("role", "")
        content = message.get("content", "")

        if role == "system" and i == 0:
            continue

        if role == "user" and i == len(messages) - 1:
            user_input = content
            continue

        if role in {"system", "user", "assistant"}:
            history_parts.append(f"{role}: {content}")

    if not user_input and messages:
        user_input = messages[-1].get("content", "")

    history = "\n".join(history_parts)

    return engine.chat(
        user_input=user_input,
        history=history,
        long_term_memory="",
    )


# ===================
# 6. Adapter：决定不同group怎么喂模型
# ===================

def run_system_group_case(engine: Engine, variant: PromptVariant, case_input: dict[str, Any]) -> str:
    """
    适用于system/* 场景
    - prompt 文件内容作为 system prompt
    - case_input 里面提取user_input
    """
    user_input = case_input["user_input"]
    
    messages = [
        {"role": "system", "content": variant.content},
        {"role": "user", "content": user_input},
    ]
    
    return run_with_engine(engine=engine, messages=messages)

def run_summary_group_case(engine: Engine, variant: PromptVariant, case_input: dict[str, Any]) -> str:
    """
    适用于summary/* 场景
    当前假设 summary prompt 不做模板变量替换，
    直接把prompt内容 + conversation 拼接为user_message。
    TODO: 后续可以支持模板变量替换 比如 {{conversation}}
    """
    conversation = case_input["conversation"]

    prompt_text = f"{variant.content}\n\n对话内容：\n{conversation}"
    messages = [
        {"role": "user", "content": prompt_text},
    ]
    return run_with_engine(engine=engine, messages=messages)

def get_group_runner(group: str) -> Callable[[Engine, PromptVariant, dict[str, Any]], str]:
    """
    根据group前缀，决定用哪个adapter
    """
    if group.startswith("system/"):
        return run_system_group_case
    elif group.startswith("summary/"):
        return run_summary_group_case

    raise ValueError(f"No adapter found for group: {group}")

# ===================
# 7. 运行某个group的全部的A/B 测试
# ===================

def run_group_ab_test(group: str, temperature: float | None = None) -> list[dict]:
    variants = discover_prompt_variants(group)
    case_file = resolve_test_case_file(group)
    cases = load_test_cases(case_file)
    runner = get_group_runner(group)

    # 每个 prompt variant 只初始化一次 Engine，避免按 case 重复初始化
    engines: dict[str, Engine] = {
        variant.name: build_engine_for_variant(variant, temperature)
        for variant in variants
    }

    results = []
    
    for case in cases:
        case_id = case["id"]
        case_input = case["input"]

        result_item = {
            "case_id": case_id,
            "case_input": case_input,
            "outputs": {}
        }
        
        for variant in variants:
            engine = engines[variant.name]
            output = runner(engine, variant, case_input)
            result_item["outputs"][variant.name] = {
                "prompt_path": variant.relative_path,
                "output": output,
            }
        
        results.append(result_item)
    
    return results

# ===================
# 8. 结果输出
# ===================

def save_results_to_markdown(group: str, results: list[dict], temperature: float | None) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_group_name = group.replace("/", "__")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"{safe_group_name}_ab_test_{timestamp}.md"
    
    lines = []
    lines.append(f"# Prompt A/B Test Results - {group}")
    lines.append("")
    lines.append(f"- 生成时间：{timestamp}")
    lines.append(f"- temperature：{temperature}")
    lines.append("")

    for item in results:
        lines.append(f"## {item['case_id']}")
        lines.append("")

        lines.append("### 输入")
        lines.append("")
        lines.append("```json")
        lines.append(json.dumps(item["case_input"], ensure_ascii=False, indent=2))
        lines.append("```")
        lines.append("")

        for variant_name, payload in item["outputs"].items():
            lines.append(f"### 输出 - {variant_name}")
            lines.append("")
            lines.append(f"- prompt: `{payload['prompt_path']}`")
            lines.append("")
            lines.append(payload["output"])
            lines.append("")

        lines.append("---")
        lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path

# ===================
# 9. 命令行入口
# ===================

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Prompt A/B tests by prompt group")
    parser.add_argument(
        "--group",
        required=True,
        help="Prompt group path, e.g. system/kaguya or summary/dialogue",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=None,
        help="Temperature for LLM generation (default: None)",
    )
    return parser.parse_args()

def main():
    args = parse_args()
    results = run_group_ab_test(group=args.group, temperature=args.temperature)
    output_path = save_results_to_markdown(
        group=args.group, 
        results=results, 
        temperature=args.temperature
        )
    print(f"A/B test finished. Results saved to: {output_path}")

if __name__ == "__main__":
    main()
