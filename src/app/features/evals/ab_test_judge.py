import json

from app.core.engine import Engine
from app.core.prompt_loader import load_prompt
from app.core.schemas import (
    CaseInput,
    EngineChatRequest,
    PromptGroup,
    PromptReference,
    VariantName,
)
from app.features.evals.schemas import JudgeEvaluation, JudgeScore, PromptRunOutput


class ABTestJudge:
    """
    AB测试评审器

    它的作用不是生成普通聊天回答
    而是：
    1. 加载judge用的prompt
    2. 构建评审内容输入
    3. 调用core层的Engine
    4. 解析模型输出
    5. 转换为json评审结果
    """

    JUDGE_PROMPT_PATH = "judge/ab_test/production.md"
    
    def __init__(self, judge_prompt_path: str | None = None, temperature: float | None = None) -> None:
        self.judge_prompt_path = judge_prompt_path or self.JUDGE_PROMPT_PATH
        judge_prompt_text = load_prompt(PromptReference(self.judge_prompt_path))
        self.engine = Engine(
            system_prompt=judge_prompt_text,
            temperature=temperature if temperature is not None else 0.0,
        )

    def evaluate(
        self,
        group: PromptGroup,
        case_id: str,
        case_input: CaseInput,
        outputs: dict[VariantName, PromptRunOutput],
    ) -> JudgeEvaluation:
        """
        单个case的多个 A/B输出做评审。

        参数：
        - group：当前测试分组，比如说”system/kaguya"
        - case_id：当前测试样例的id
        - case_input：当前测试的输入
        - outputs： 不同variant的输出结果

        outputs的结构类似于：
        {
            "ab_v1": {
                "prompt_path": "system/kaguya/ab_v1.md",
                "output": "你好，我是..."
            },
            "ab_v2": {
                "prompt_path": "system/kaguya/ab_v2.md",
                "output": "您好，我是..."
            }
        }

        返回一个结构化的字典，比如：
        {
            "winner": "ab_v2",
            "reason": "ab_v2 更自然且更符合角色设定",
            "scores": {
                "ab_v1": {...},
                "ab_v2": {...}
            },
            "raw_output": "模型原始输出"
        }
        """
        # 1. 先把评审需要的信息拼成一个给judge模型砍的大字符串
        judge_input = self._build_judge_input(
            group=group,
            case_id=case_id,
            case_input=case_input,
            outputs=outputs
        )
        
        # 2. 调用底层Engine，这里不需要History和长期记忆，所以全部传空
        raw_output = self.engine.run(
            EngineChatRequest(
                user_input=judge_input,
                history="",
                long_term_memory="",
            )
        ).text

        # 3. 解析judge 模型返回内容
        parsed_result = self._parser_judge_output(
            raw_output=raw_output,
            variant_names=list(outputs.keys())
        )

        # 4. 无论解析还是失败，把原始输出带上，方便调试。
        parsed_result.raw_output = raw_output
        return parsed_result

    def _build_judge_input(
        self,
        group: PromptGroup,
        case_id: str,
        case_input: CaseInput,
        outputs: dict[VariantName, PromptRunOutput],
    ) -> str:
        """
        构造judge 模型需要的user_input。
        这里的思路很简单：
        把“题目 + 各个候选答案” 拼成一段结构清晰的文本
        让judge prompt 去评审
        """

        lines: list[str] = []

        lines.append("请评审以下A/B测试结果")
        lines.append("")
        lines.append(f"测试分组：{group}")
        lines.append(f"测试用例ID：{case_id}")
        lines.append("")
        lines.append("【测试输入】：")
        lines.append("```json")
        lines.append(json.dumps(case_input, ensure_ascii=False, indent=2))
        lines.append("```")
        lines.append("")

        lines.append("【各候选答案】：")

        # 逐个variant 把输入塞进去
        for variant_name, payload in outputs.items():
            lines.append(f"### {variant_name}")
            lines.append(f"prompt_path: {payload.prompt_path}")
            lines.append("output:")
            lines.append(payload.output)
            lines.append("")
        lines.append("请严格按照 system prompt里面要求的json格式返回。")

        return "\n".join(lines)

    def _parser_judge_output(
        self,
        raw_output: str,
        variant_names: list[VariantName],
    ) -> JudgeEvaluation:
        """
        解析 judge的模型输出。

        理想情况下，judge prompt会要求模型只输出json。
        但是还是要有兜底机制：
        1. 尝试直接 json.loads(raw_output)
        2. 如果失败，再尝试从文本中提取最外层json
        3. 如果还是失败，就返回一个fallback结果

        variant_names 是用来做winner校验的，避免模型返回一个不存在的名字。
        """

        #1. 直接完整json解析
        try:
            parsed = json.loads(raw_output)
            return self._normalize_result(parsed, variant_names)
        except Exception:
            pass

        #2. 尝试从输出文本中截取json对象
        extracted_json = self._extract_json_object(raw_output)
        if extracted_json is not None:
            try:
                parsed = json.loads(extracted_json)
                return self._normalize_result(parsed, variant_names)
            except Exception:
                pass
        
        #3. 彻底失败的时候给一个兜底结构
        return JudgeEvaluation(
            winner=None,
            reason="无法解析judge输出",
            scores={},
            parse_error=True,
        )

    def _normalize_result(
        self,
        parsed: dict[str, object],
        variant_names: list[VariantName],
    ) -> JudgeEvaluation:
        """
        对解析出来的结果做标准化

        主要工作：
        1. 保证返回的字段存在
        2. 校验winner 是否在合法variant 列表里
        3. 尽量把结果整理成统一结构
        """
        winner = parsed.get("winner")
        reason = parsed.get("reason", "")
        scores = parsed.get("scores", {})

        # winner不合法？就置空
        if not isinstance(winner, str) or winner not in variant_names:
            winner = None

        if not isinstance(reason, str):
            reason = ""
        
        # scores不是字典，也就兜底成空
        if not isinstance(scores, dict):
            normalized_scores: dict[VariantName, JudgeScore] = {}
        else:
            normalized_scores = self._normalize_scores(scores, variant_names)
        
        return JudgeEvaluation(
            winner=winner,
            reason=reason,
            scores=normalized_scores,
            parse_error=False,
        )

    def _normalize_scores(
        self,
        raw_scores: dict[object, object],
        variant_names: list[VariantName],
    ) -> dict[VariantName, JudgeScore]:
        """把 judge 输出的 scores 字段标准化为结构化评分对象。"""
        normalized_scores: dict[VariantName, JudgeScore] = {}

        for raw_variant_name, raw_score_payload in raw_scores.items():
            if not isinstance(raw_variant_name, str) or raw_variant_name not in variant_names:
                continue

            if not isinstance(raw_score_payload, dict):
                continue

            normalized_scores[raw_variant_name] = JudgeScore(
                instruction_following=self._parse_optional_int(
                    raw_score_payload.get("instruction_following")
                ),
                clarity=self._parse_optional_int(raw_score_payload.get("clarity")),
                overall_quality=self._parse_optional_int(
                    raw_score_payload.get("overall_quality")
                ),
            )

        return normalized_scores

    def _parse_optional_int(self, value: object) -> int | None:
        """把 judge 返回的评分项解析成整数；无效值返回 None。"""
        return value if isinstance(value, int) else None
    
    def _extract_json_object(self, text: str) -> str | None:
        """
        从文本中提取最外层的json对象
        """
        # 找到第一个{和最后一个}
        start = text.find("{")
        end = text.rfind("}")
        
        if start == -1 or end == -1 or start >= end:
            return None
        
        return text[start:end+1]
