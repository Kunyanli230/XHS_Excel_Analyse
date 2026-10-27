"""节点适配层：把 loader 的领域对象转成 GraphState 的增量更新。

LangGraph 的节点约定：接收 state，返回「要合并进 state 的那部分」。
这里只做转换和组装，业务逻辑都在 loader 里——所以这个文件永远很短。
"""
from __future__ import annotations

from agent.domain import LoadReport
from agent.loaders import BriefLoader, TalentLoader


def load_inputs(state: dict) -> dict:
    """图上第一个节点：读取需求清单 & 达人列表。"""
    report = LoadReport()

    brief = BriefLoader(state["brief_path"]).load(report)
    talents = TalentLoader(state["talent_path"]).load(report)

    return {
        "brief_raw": dict(brief.raw),
        "brief": brief.to_dict(),
        "talents": [t.to_dict() for t in talents],
        "issues": report.issues,
    }
