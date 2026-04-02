# 这个脚本的作用：
# 1. 自动读取某个 prompt 分组（比如 system/kaguya）下的多个 A/B 版本 prompt
# 2. 自动读取对应的测试用例 JSON
# 3. 分别调用模型跑一遍，拿到不同 prompt 的输出结果
# 4. 最后把结果输出成 Markdown / JSON / CSV 三种格式，方便人工或程序比较
#
# 如果你有 TypeScript 背景，可以把这个文件理解成：
# - 一个 Node.js 脚本入口
# - 里面包含了一些“类型定义 + 工具函数 + 主流程函数 + CLI入口”
# - 最后通过 main() 串起来执行

import argparse  # 命令行参数解析，类似 Node.js 里读取 process.argv 但更规范
import csv  # Python 标准库，用来生成 CSV 文件
import json  # Python 标准库，用来读写 JSON
import sys  # 提供 Python 运行时相关能力，这里主要用来改 import 路径
from datetime import datetime  # 处理日期时间，这里用来生成输出文件时间戳
from pathlib import Path  # Path 用面向对象方式处理文件路径，比字符串拼路径更稳
from typing import Callable, cast  # 类型标注工具：Callable 表示函数类型

# ===================
# 1. 路径基础配置
# ===================

# Path(__file__) 表示“当前这个 .py 文件本身的路径”
# resolve() 会把它变成绝对路径
# parents[1] 表示往上找两层目录
# 你可以把这里理解成：根据当前脚本位置，反推出整个项目根目录
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# 项目里的 src 目录
SRC_DIR = PROJECT_ROOT / "src"

# src/app 目录
APP_DIR = SRC_DIR / "app"

# prompt 文件根目录，比如 src/app/prompts
PROMPTS_ROOT = APP_DIR / "prompts"

# 测试用例目录，比如 tests/prompt_cases
TEST_CASES_ROOT = PROJECT_ROOT / "tests" / "prompt_cases"

# 输出目录，比如 tests/outputs
OUTPUT_DIR = PROJECT_ROOT / "tests" / "outputs"

# 让脚本可以 import src 下的模块。
# 这是因为当前文件在 scripts/ 目录下，默认不一定能直接 import 到 src/app/...。
# 类比 TypeScript：有点像你手动补充 tsconfig 的路径别名解析范围。
sys.path.append(str(SRC_DIR))

# load_prompt：根据相对路径读取 prompt 文件内容
from app.core.prompt_loader import load_prompt
from app.core.contracts.chat_model import ChatModel
from app.core.schemas import (
    build_prompt_metadata,
    ChatMessage,
    EngineChatRequest,
    PromptGroup,
    PromptReference,
    PromptVariant,
    SummaryCaseInput,
    SupportedCaseInput,
    SystemCaseInput,
    validate_case_input,
)

from app.infra.factories.llm_factory import build_chat_model

# ABTestJudge：A/B 测试评审服务。它会复用底层 Engine，让 LLM 对多个候选输出做比较和打分。
from app.features.evals.service import ABTestJudgeService
from app.features.evals.schemas import (
    ABTestCase,
    ABTestCaseResult,
    ABTestOutputPaths,
    PromptRunOutput,
)

# ===================
# 3. 发现 prompt group 下的 ab版本
# ===================

def discover_prompt_variants(group: PromptGroup) -> list[PromptVariant]:
    """
    根据group（比如system/kaguya）自动发现该目录下所有ab_*.md文件
    """
    group_dir = PROMPTS_ROOT / group

    if not group_dir.exists():
        raise FileNotFoundError(f"Prompt group directory not found: {group_dir}")
    
    if not group_dir.is_dir():
        raise ValueError(f"Prompt group is not a directory: {group_dir}")
    
    # 这里先准备一个空列表，后面把扫描到的 PromptVariant 依次放进去
    variants = []
    # glob("ab_*.md")：匹配目录下所有 ab_ 开头、.md 结尾的文件
    # sorted(...)：排序，保证每次扫描结果顺序稳定
    for path in sorted(group_dir.glob("ab_*.md")):
        # path.stem 表示“去掉扩展名后的文件名”
        # 例如 ab_v1.md -> ab_v1
        variant_name = path.stem  # ab_v1, ab_v2, ...
        # 转成相对于 PROMPTS_ROOT 的路径
        # 例如 /.../prompts/system/kaguya/ab_v1.md
        # 会变成 system/kaguya/ab_v1.md
        relative_path = str(path.relative_to(PROMPTS_ROOT))
        # 读取这个 prompt 文件的具体内容
        content = load_prompt(PromptReference(relative_path))
        # 把这一个 prompt 版本包装成 PromptVariant 对象，塞进列表里
        variants.append(
            PromptVariant(
                name=variant_name,
                relative_path=relative_path,
                content=content,
                metadata=build_prompt_metadata(PromptReference(relative_path)),
            )
        )
    
    if not variants:
        raise ValueError(f"No ab_*.md variants found in {group_dir}")
    
    return variants

# ===================
# 4. 自动匹配测试样本文件
# ===================

def resolve_test_case_file(group: PromptGroup) -> Path:
    """
    根据 group 自动推导测试用例文件路径。

    例如：
    group = "system/kaguya"
    会映射到：
    tests/prompt_cases/system/kaguya.json
    """
    case_file = TEST_CASES_ROOT / f"{group}.json"

    if not case_file.exists():
        raise FileNotFoundError(f"Test case file not found: {case_file}")

    return case_file

def load_test_cases(case_file: Path, group: PromptGroup) -> list[ABTestCase]:
    # open(..., "r") 表示只读模式读取文件
    # encoding="utf-8" 表示按 UTF-8 编码读取，避免中文乱码
    with open(case_file, "r", encoding="utf-8") as f:
        # json.load(f) 会把 JSON 文件内容直接转成 Python 对象
        # 如果 JSON 顶层是数组，这里通常就会得到 list[dict]
        raw_cases = json.load(f)

    cases: list[ABTestCase] = []
    for item in raw_cases:
        case_id = item.get("id")
        case_input = item.get("input")

        if not isinstance(case_id, str):
            raise ValueError(f"测试用例缺少合法的字符串 id: {item}")

        if not isinstance(case_input, dict):
            raise ValueError(f"测试用例缺少合法的 input 对象: {item}")

        cases.append(
            ABTestCase(
                id=case_id,
                input=validate_case_input(group, case_input),
            )
        )

    return cases

# ===================
# 5. 这里是模型调用
# ===================

# 这里没有直接写 call_llm() 这种函数，而是统一通过聊天模型来调用。
# 这样做的好处是：
# - 模型初始化逻辑集中管理
# - 温度、prompt、记忆等参数更容易统一封装
# - 后续更容易替换底层实现

def build_chat_model_for_variant(
    variant: PromptVariant, temperature: float | None = None
) -> ChatModel:
    """
    为某个 prompt 版本预先构建聊天模型。

    这样每个 variant 只初始化一次模型链，避免在每个 case 上重复初始化。
    """
    # 这里把“某个 prompt 版本的内容”塞进聊天模型里，作为 system prompt
    # temperature 如果外部没传，就默认用 0.7
    return build_chat_model(
        use_case="chat",
        system_prompt=variant.content,
        temperature=temperature if temperature is not None else 0.7,
    )


def run_with_engine(chat_model: ChatModel, messages: list[ChatMessage]) -> str:
    """
    使用已经初始化好的聊天模型执行一次调用。

    约定：
    - 第一条 system message 仅用于构建聊天模型，因此这里不再重复传入。
    - 最后一条 user message 作为当前用户输入。
    - 其他消息尽量拼接到 history 中。
    """
    # history_parts：先收集“历史消息”的文本片段
    # 最后再用 "\n" 拼成一个完整 history 字符串
    history_parts: list[str] = []
    # user_input：当前这一轮用户真正输入给模型的话
    user_input = ""

    # enumerate(messages) 会同时拿到：
    # - i：下标
    # - message：当前这条消息对象
    for i, message in enumerate(messages):
        role = message.role
        content = message.content

        # 第一条 system message 已经在构建聊天模型时用过了
        # 这里就不再重复塞给 history，避免重复
        if role == "system" and i == 0:
            continue

        # 如果当前消息是“最后一条 user 消息”
        # 我们把它视为“当前用户输入”，而不是历史
        if role == "user" and i == len(messages) - 1:
            user_input = content
            continue

        # 其余 system/user/assistant 消息都视为历史内容
        # 这里统一拼成类似："user: 你好" 这样的格式
        if role in {"system", "user", "assistant"}:
            history_parts.append(f"{role}: {content}")

    # 兜底逻辑：如果上面没有识别出 user_input
    # 就直接拿最后一条消息的 content，避免传空
    if not user_input and messages:
        user_input = messages[-1].content

    # 把历史片段列表拼成一个多行字符串
    history = "\n".join(history_parts)

    # 真正调用聊天模型
    # 这里 long_term_memory 先传空字符串，说明这版脚本暂时还没接长期记忆
    return chat_model.run(
        EngineChatRequest(
            user_input=user_input,
            history=history,
            long_term_memory="",
        )
    ).text


# ===================
# 6. Adapter：决定不同group怎么喂模型
# ===================

def run_system_group_case(
    chat_model: ChatModel,
    variant: PromptVariant,
    case_input: SupportedCaseInput,
) -> str:
    """
    适用于system/* 场景
    - prompt 文件内容作为 system prompt
    - case_input 里面提取user_input
    """
    # 从测试用例里取出 user_input 字段
    system_case_input = cast(SystemCaseInput, case_input)
    user_input = system_case_input["user_input"]
    
    # 这里手动组装成消息列表
    # 类比前端里构造一个 messages 数组传给聊天接口
    messages = [
        ChatMessage(role="system", content=variant.content),
        ChatMessage(role="user", content=user_input),
    ]
    
    # 交给通用执行函数处理
    return run_with_engine(chat_model=chat_model, messages=messages)

def run_summary_group_case(
    chat_model: ChatModel,
    variant: PromptVariant,
    case_input: SupportedCaseInput,
) -> str:
    """
    适用于summary/* 场景
    当前假设 summary prompt 不做模板变量替换，
    直接把prompt内容 + conversation 拼接为user_message。
    TODO: 后续可以支持模板变量替换 比如 {{conversation}}
    """
    # summary 类测试通常会给一整段 conversation
    summary_case_input = cast(SummaryCaseInput, case_input)
    conversation = summary_case_input["conversation"]

    # 这里是最简单的做法：
    # 直接把 prompt 模板文本 + 对话内容 拼在一起
    prompt_text = f"{variant.content}\n\n对话内容：\n{conversation}"
    # 然后把拼好的整段内容作为 user 消息发给模型
    messages = [
        ChatMessage(role="user", content=prompt_text),
    ]
    return run_with_engine(chat_model=chat_model, messages=messages)

def get_group_runner(group: PromptGroup) -> Callable[[ChatModel, PromptVariant, SupportedCaseInput], str]:
    """
    根据group前缀，决定用哪个adapter
    """
    if group.startswith("system/"):
        # system/* 走 system adapter
        return run_system_group_case
    elif group.startswith("summary/"):
        # summary/* 走 summary adapter
        return run_summary_group_case

    raise ValueError(f"No adapter found for group: {group}")

# ===================
# 7. 运行某个group的全部的A/B 测试
# ===================

def run_group_ab_test(
    group: PromptGroup,
    temperature: float | None = None,
    judge: bool = False,
) -> list[ABTestCaseResult]:
    # 先找到这个 group 下的所有 prompt 版本
    variants = discover_prompt_variants(group)
    # 找到对应测试用例文件
    case_file = resolve_test_case_file(group)
    # 把测试用例 JSON 读进来
    cases = load_test_cases(case_file, group)
    # 根据 group 类型，选择合适的执行适配器
    runner = get_group_runner(group)
    # 如果开启了 judge，就初始化一个评审服务。
    # 这里先不把业务 temperature 透传进去，因为 judge 一般希望尽量稳定，
    # 会在 ABTestJudgeService 内部使用自己的默认 temperature（通常接近 0）。
    judge_service = ABTestJudgeService() if judge else None

    # 每个 prompt variant 只初始化一次 Engine，避免按 case 重复初始化
    chat_models: dict[str, ChatModel] = {
        variant.name: build_chat_model_for_variant(variant, temperature)
        for variant in variants
    }

    # 最终结果列表：每个 case 会生成一条结果
    results: list[ABTestCaseResult] = []
    
    # 外层循环：遍历每一个测试用例
    for case in cases:
        # result_item：记录“这个 case 在各个 prompt 版本下的输出”
        case_id = case.id
        case_input = case.input

        result_item = ABTestCaseResult(case_id=case_id, case_input=case_input)
        
        # 内层循环：让每个 prompt 版本都跑一遍当前 case
        for variant in variants:
            # 取出这个 variant 对应的聊天模型（已经提前初始化好了）
            chat_model = chat_models[variant.name]
            # 真正执行一次模型调用
            output = runner(chat_model, variant, case_input)
            # 把该 variant 的输出结果记录下来
            result_item.outputs[variant.name] = PromptRunOutput(
                prompt_path=variant.relative_path,
                prompt_metadata=variant.metadata,
                output=output,
            )

        if judge_service is not None:
            result_item.evaluation = judge_service.evaluate(
                group=group,
                case_id=case_id,
                case_input=case_input,
                outputs=result_item.outputs,
            )
        
        # 当前 case 的所有版本都跑完后，加入总结果
        results.append(result_item)
    
    return results

# ===================
# 8. 结果输出
# ===================

# 结果输出相关函数
# 这里会把同一批测试结果同时保存成多种格式

def _build_result_base_path(group: str) -> tuple[str, Path]:
    """构造输出文件的基础路径（不含扩展名）。"""
    # 用当前时间生成一个时间戳，避免文件重名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # safe_group_name：把 system/kaguya 这种路径里的 / 替换掉
    # 否则文件名里直接带 / 会有问题
    safe_group_name = group.replace("/", "__")

    # 确保输出目录存在；不存在就自动创建
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 例如：system__kaguya_ab_test_20260318_090000
    base_name = f"{safe_group_name}_ab_test_{timestamp}"
    base_path = OUTPUT_DIR / base_name
    return timestamp, base_path



def save_results_to_markdown(
    group: PromptGroup,
    results: list[ABTestCaseResult],
    temperature: float | None,
    output_path: Path | None = None,
    timestamp: str | None = None,
) -> Path:
    # 如果外部没有传 output_path / timestamp，就自己现算一份默认输出路径
    if output_path is None or timestamp is None:
        timestamp, base_path = _build_result_base_path(group)
        output_path = base_path.with_suffix(".md")

    # lines 用来逐行收集 Markdown 文本内容
    lines = []
    lines.append(f"# Prompt A/B Test Results - {group}")
    lines.append("")
    lines.append(f"- 生成时间：{timestamp}")
    lines.append(f"- temperature：{temperature}")
    lines.append("")

    # 遍历每个 case，把输入和不同 variant 的输出写进 Markdown
    for item in results:
        lines.append(f"## {item.case_id}")
        lines.append("")

        lines.append("### 输入")
        lines.append("")
        lines.append("```json")
        lines.append(json.dumps(item.case_input, ensure_ascii=False, indent=2))
        lines.append("```")
        lines.append("")

        for variant_name, payload in item.outputs.items():
            lines.append(f"### 输出 - {variant_name}")
            lines.append("")
            lines.append(f"- prompt: `{payload.prompt_path}`")
            lines.append(f"- domain: `{payload.prompt_metadata.domain}`")
            lines.append(f"- group: `{payload.prompt_metadata.group}`")
            lines.append(f"- family: `{payload.prompt_metadata.family}`")
            lines.append(f"- production: `{payload.prompt_metadata.is_production}`")
            lines.append(f"- ab_variant: `{payload.prompt_metadata.is_ab_variant}`")
            lines.append("")
            lines.append(payload.output)
            lines.append("")

        # 如果这个 case 开启了自动评审，就把评审结果也写进 Markdown
        if item.evaluation is not None:
            lines.append("### 自动评估")
            lines.append("")
            lines.append("```json")
            lines.append(json.dumps(item.evaluation.to_dict(), ensure_ascii=False, indent=2))
            lines.append("```")
            lines.append("")

        lines.append("---")
        lines.append("")

    # 把所有行拼成一个完整字符串后写入 .md 文件
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path



def save_results_to_json(
    group: PromptGroup,
    results: list[ABTestCaseResult],
    temperature: float | None,
    output_path: Path | None = None,
    timestamp: str | None = None,
) -> Path:
    # 如果外部没有传 output_path / timestamp，就自己现算一份默认输出路径
    if output_path is None or timestamp is None:
        timestamp, base_path = _build_result_base_path(group)
        output_path = base_path.with_suffix(".json")

    # JSON 格式更适合后续再做程序处理
    payload = {
        "group": group,
        "generated_at": timestamp,
        "temperature": temperature,
        "results": [item.to_dict() for item in results],
    }
    # ensure_ascii=False：保留中文，不转成 \uXXXX
    # indent=2：缩进 2 个空格，方便阅读
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path



def save_results_to_csv(
    group: PromptGroup,
    results: list[ABTestCaseResult],
    temperature: float | None,
    output_path: Path | None = None,
    timestamp: str | None = None,
) -> Path:
    # 如果外部没有传 output_path / timestamp，就自己现算一份默认输出路径
    if output_path is None or timestamp is None:
        timestamp, base_path = _build_result_base_path(group)
        output_path = base_path.with_suffix(".csv")

    # CSV 格式适合拿去 Excel / Numbers / 表格工具里看
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        # 先写表头（header）
        writer.writerow([
            "group",
            "generated_at",
            "temperature",
            "case_id",
            "variant_name",
            "prompt_path",
            "case_input_json",
            "output",
            "judge_winner",
            "judge_reason",
        ])

        # 再逐条写入数据行
        for item in results:
            case_id = item.case_id
            case_input_json = json.dumps(item.case_input, ensure_ascii=False)

            # evaluation 是 case 级别结果，所以同一个 case 下的多行 CSV 会重复带上 winner / reason
            # 这是正常的，因为 CSV 本来就是扁平结构
            evaluation = item.evaluation
            judge_winner = evaluation.winner if evaluation is not None else None
            judge_reason = evaluation.reason if evaluation is not None else None

            for variant_name, payload in item.outputs.items():
                writer.writerow(
                    [
                        group,
                        timestamp,
                        temperature,
                        case_id,
                        variant_name,
                        payload.prompt_path,
                        case_input_json,
                        payload.output,
                        judge_winner,
                        judge_reason,
                    ]
                )

    return output_path



def save_results(
    group: PromptGroup,
    results: list[ABTestCaseResult],
    temperature: float | None,
) -> ABTestOutputPaths:
    # 先生成这一批结果共用的时间戳和基础文件名
    timestamp, base_path = _build_result_base_path(group)

    md_path = save_results_to_markdown(
        group=group,
        results=results,
        temperature=temperature,
        output_path=base_path.with_suffix(".md"),
        timestamp=timestamp,
    )
    json_path = save_results_to_json(
        group=group,
        results=results,
        temperature=temperature,
        output_path=base_path.with_suffix(".json"),
        timestamp=timestamp,
    )
    csv_path = save_results_to_csv(
        group=group,
        results=results,
        temperature=temperature,
        output_path=base_path.with_suffix(".csv"),
        timestamp=timestamp,
    )

    # 返回三种输出文件路径，方便 main() 统一打印
    return ABTestOutputPaths(
        markdown=md_path,
        json=json_path,
        csv=csv_path,
    )

# ===================
# 9. 命令行入口
# ===================

# 命令行入口相关
# 这样你就可以在终端里通过 python scripts/run_prompt_ab_test.py --group ... 来执行
def parse_args() -> argparse.Namespace:
    # argparse.ArgumentParser 就是“命令行参数解析器”
    parser = argparse.ArgumentParser(description="Run Prompt A/B tests by prompt group")
    # --group：必填，表示要测试哪个 prompt 分组
    parser.add_argument(
        "--group",
        required=True,
        help="Prompt group path, e.g. system/kaguya or summary/dialogue",
    )
    # --temperature：可选，控制模型生成随机度
    parser.add_argument(
        "--temperature",
        type=float,
        default=None,
        help="Temperature for LLM generation (default: None)",
    )
    # --judge：可选开关
    # 加了这个参数，就会在 A/B 输出完成之后，再调用 judge 专用 LLM 做自动评审
    parser.add_argument(
        "--judge",
        action="store_true",
        help="Use judge LLM to score outputs (default: False)",
    )
    return parser.parse_args()

# main() 是主流程入口
def main():
    # 第一步：解析命令行参数
    args = parse_args()
    # 第二步：执行 A/B 测试主流程
    results = run_group_ab_test(
        group=args.group,
        temperature=args.temperature,
        judge=args.judge,
    )
    # 第三步：把结果保存成多种格式
    output_paths = save_results(
        group=args.group,
        results=results,
        temperature=args.temperature,
    )
    # 第四步：把输出文件路径打印到终端
    print("A/B test finished. Results saved to:")
    for file_type, path in output_paths.to_dict().items():
        print(f"- {file_type}: {path}")

# Python 里的标准脚本入口判断
# 意思是：只有当这个文件被“直接运行”时，才执行 main()
# 如果它只是被别的文件 import，就不会自动执行
if __name__ == "__main__":
    main()
