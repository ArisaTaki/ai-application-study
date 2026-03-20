from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, TypeAlias, TypedDict


PromptGroup: TypeAlias = str
# Prompt 的分组路径，例如 `system/kaguya`。

PromptPath: TypeAlias = str
# Prompt 文件相对路径，例如 `system/kaguya/production.md`。

VariantName: TypeAlias = str
# A/B 测试里的变体名，例如 `ab_5_shot`。

CaseId: TypeAlias = str
# 测试用例唯一标识，例如 `case_1`。

JSONPrimitive: TypeAlias = str | int | float | bool | None
# JSON 里允许出现的基础值类型。

JSONValue: TypeAlias = JSONPrimitive | list["JSONValue"] | dict[str, "JSONValue"]
# 通用 JSON 值类型，用来替代宽泛的 Any。

CaseInput: TypeAlias = dict[str, JSONValue]
# 通用测试输入结构；在进入具体业务前先用 JSON 风格字典承接原始数据。

PromptVariables: TypeAlias = dict[str, object]
# Prompt 模板渲染时使用的变量表。

PromptDomain: TypeAlias = Literal["system", "summary", "judge", "unknown"]
# Prompt 顶层领域类型，对应 prompts 目录下的一级分类。


class SystemCaseInput(TypedDict):
    """`system/*` 分组下的测试输入结构。"""

    user_input: str
    # 当前轮用户输入文本。


class SummaryCaseInput(TypedDict):
    """`summary/*` 分组下的测试输入结构。"""

    conversation: str
    # 需要被总结的完整对话内容。


SupportedCaseInput: TypeAlias = SystemCaseInput | SummaryCaseInput
# 当前项目内已经明确支持的测试输入类型。


def validate_case_input(group: PromptGroup, case_input: CaseInput) -> SupportedCaseInput:
    """按 group 校验测试输入结构，尽早发现 case JSON 格式错误。"""
    if group.startswith("system/"):
        user_input = case_input.get("user_input")
        if not isinstance(user_input, str):
            raise ValueError("system/* case_input 必须包含字符串类型的 user_input")
        return {"user_input": user_input}

    if group.startswith("summary/"):
        conversation = case_input.get("conversation")
        if not isinstance(conversation, str):
            raise ValueError("summary/* case_input 必须包含字符串类型的 conversation")
        return {"conversation": conversation}

    raise ValueError(f"Unsupported prompt group for case validation: {group}")


@dataclass(slots=True)
class ChatMessage:
    """聊天消息的标准结构。"""

    role: Literal["system", "user", "assistant"]
    # 消息角色；当前项目只允许 system / user / assistant。

    content: str
    # 消息正文。


@dataclass(slots=True)
class PromptReference:
    """对某个 prompt 文件的轻量引用。"""

    relative_path: PromptPath
    # 相对于 `src/app/prompts/` 的路径。


@dataclass(slots=True)
class PromptMetadata:
    """Prompt 文件的语义化元数据。"""

    domain: PromptDomain
    # Prompt 所属的一级领域，例如 system / summary / judge。

    group: PromptGroup
    # Prompt 所属分组，例如 `system/kaguya`。

    family: str
    # Prompt 的二级目录名，通常表示角色或业务族，例如 `kaguya` / `dialogue`。

    filename: str
    # Prompt 文件名，包含扩展名。

    stem: str
    # Prompt 文件名去掉扩展名后的结果。

    extension: str
    # Prompt 文件扩展名，例如 `.md`。

    is_production: bool
    # 是否为正式版 prompt；通常文件名为 `production` 时为 True。

    is_ab_variant: bool
    # 是否为 A/B 测试变体；通常文件名以 `ab_` 开头时为 True。

    variant_name: str | None = None
    # 变体名；如果是 A/B 测试文件则为具体变体名，否则为 None。


def build_prompt_metadata(prompt: PromptReference) -> PromptMetadata:
    """根据 prompt 相对路径推断元数据。"""
    path = Path(prompt.relative_path)
    parts = path.parts

    domain = parts[0] if parts else "unknown"
    normalized_domain: PromptDomain
    if domain in {"system", "summary", "judge"}:
        normalized_domain = domain
    else:
        normalized_domain = "unknown"

    group = str(path.parent).replace("\\", "/")
    family = path.parent.name if path.parent.name else ""
    filename = path.name
    stem = path.stem
    extension = path.suffix
    is_production = stem == "production"
    is_ab_variant = stem.startswith("ab_")
    variant_name = stem if is_ab_variant else None

    return PromptMetadata(
        domain=normalized_domain,
        group=group,
        family=family,
        filename=filename,
        stem=stem,
        extension=extension,
        is_production=is_production,
        is_ab_variant=is_ab_variant,
        variant_name=variant_name,
    )


@dataclass(slots=True)
class PromptRenderRequest:
    """Prompt 渲染请求。"""

    prompt: PromptReference
    # 要读取和渲染的 prompt 文件。

    variables: PromptVariables = field(default_factory=dict)
    # 用来替换模板占位符的变量。


@dataclass(slots=True)
class PromptVariant:
    """A/B 测试中某个 prompt 变体的完整描述。"""

    name: VariantName
    # 变体名，通常由文件名去掉扩展名得到。

    relative_path: PromptPath
    # 变体文件的相对路径。

    content: str
    # 变体对应的完整 prompt 文本。

    metadata: PromptMetadata
    # 由路径推断出的 prompt 元数据，便于做治理、筛选和后续扩展。


@dataclass(slots=True)
class EngineChatRequest:
    """Engine 层标准输入。"""

    user_input: str
    # 当前轮用户输入。

    history: str = ""
    # 供模型参考的历史对话文本。

    long_term_memory: str = ""
    # 长期记忆或用户画像等补充上下文。


@dataclass(slots=True)
class EngineChatResult:
    """Engine 层标准输出。"""

    text: str
    # 模型返回的最终文本内容。

    error: str | None = None
    # 调用失败时的错误码；成功时为 None。
