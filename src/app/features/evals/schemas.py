from dataclasses import asdict, dataclass, field
from pathlib import Path

from app.core.schemas import CaseId, CaseInput, PromptMetadata, PromptPath, VariantName


@dataclass(slots=True)
class JudgeScore:
    """Judge 对单个变体给出的分项评分。"""

    instruction_following: int | None = None
    # 指令遵循度评分。

    clarity: int | None = None
    # 表达清晰度评分。

    overall_quality: int | None = None
    # 综合质量评分。

    def to_dict(self) -> dict[str, int]:
        """转换为仅包含有效评分项的字典。"""
        payload: dict[str, int] = {}
        if self.instruction_following is not None:
            payload["instruction_following"] = self.instruction_following
        if self.clarity is not None:
            payload["clarity"] = self.clarity
        if self.overall_quality is not None:
            payload["overall_quality"] = self.overall_quality
        return payload


@dataclass(slots=True)
class PromptRunOutput:
    """单个 prompt 变体在一次 case 执行后的输出。"""

    prompt_path: PromptPath
    # 生成该输出所使用的 prompt 文件路径。

    prompt_metadata: PromptMetadata
    # 由 prompt 路径推断出的元数据，便于做管理和结果分析。

    output: str
    # 模型对该 case 的实际回复。


@dataclass(slots=True)
class JudgeEvaluation:
    """Judge 模型对一组候选输出的评审结果。"""

    winner: VariantName | None
    # 胜出的变体名；解析失败或不合法时为 None。

    reason: str
    # Judge 给出的胜出原因说明。

    scores: dict[VariantName, JudgeScore] = field(default_factory=dict)
    # 每个变体的细分评分明细。

    raw_output: str | None = None
    # Judge 模型的原始输出，便于调试解析问题。

    parse_error: bool = False
    # 是否发生了解析失败。

    def to_dict(self) -> dict[str, object]:
        """转换为适合 JSON 序列化的普通字典。"""
        return {
            "winner": self.winner,
            "reason": self.reason,
            "scores": {
                variant_name: score.to_dict()
                for variant_name, score in self.scores.items()
            },
            "raw_output": self.raw_output,
            "parse_error": self.parse_error,
        }


@dataclass(slots=True)
class ABTestCase:
    """A/B 测试里的单条输入样例。"""

    id: CaseId
    # 用例 ID。

    input: CaseInput
    # 这条用例的输入内容。


@dataclass(slots=True)
class ABTestCaseResult:
    """单条测试样例在整轮 A/B 跑完后的聚合结果。"""

    case_id: CaseId
    # 当前结果对应的用例 ID。

    case_input: CaseInput
    # 当前用例输入，保留原样便于落盘与排查。

    outputs: dict[VariantName, PromptRunOutput] = field(default_factory=dict)
    # 各个变体对应的输出结果。

    evaluation: JudgeEvaluation | None = None
    # 可选的自动评审结果；未开启 judge 时为空。

    def to_dict(self) -> dict[str, object]:
        """转换为适合 JSON 序列化的普通字典。"""
        return {
            "case_id": self.case_id,
            "case_input": self.case_input,
            "outputs": {
                variant_name: asdict(output)
                for variant_name, output in self.outputs.items()
            },
            **(
                {"evaluation": self.evaluation.to_dict()}
                if self.evaluation is not None
                else {}
            ),
        }


@dataclass(slots=True)
class ABTestOutputPaths:
    """同一轮 A/B 测试输出文件的路径集合。"""

    markdown: Path
    # Markdown 报告路径。

    json: Path
    # JSON 结果路径。

    csv: Path
    # CSV 结果路径。

    def to_dict(self) -> dict[str, Path]:
        """转换为便于遍历打印的字典结构。"""
        return {
            "markdown": self.markdown,
            "json": self.json,
            "csv": self.csv,
        }
