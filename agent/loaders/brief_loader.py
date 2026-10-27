"""BriefLoader：读取甲方需求单（表单式 Excel，A 列是标签，B 列是内容）。

按标签查找而不是按单元格坐标查找：表单将来加一行、删一行都不用改代码。
"""
from __future__ import annotations

from pathlib import Path

import openpyxl

from agent.domain import Brief, LoadReport, parse_number

# 表单标签 -> Brief 字段。标签必须和需求单里写的一字不差。
_LABEL_MAP: dict[str, str] = {
    "甲方品牌": "brand",
    "投放产品": "product",
    "产品定价": "product_price",
    "投放目标": "objective",
    "核心卖点": "selling_points",
    "目标人群": "target_audience",
    "总预算": "total_budget",
    "投放周期": "campaign_period",
    "核心KPI": "kpi",
    "内容方向": "content_direction",
    "合规要求": "compliance",
    "达人要求": "creator_requirements",
    "其他排除": "exclusions",
    "备注": "notes",
}

# 后续节点真正要用的字段，缺了要记进报告（不中断，流程后面有追问机制）
_REQUIRED = ["brand", "product", "selling_points", "target_audience", "total_budget", "kpi"]


class BriefLoader:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def load(self, report: LoadReport | None = None) -> Brief:
        report = report or LoadReport()
        if not self.path.exists():
            report.add(f"需求单文件不存在：{self.path}")
            return Brief()

        ws = openpyxl.load_workbook(self.path, data_only=True).active
        raw: dict[str, str] = {}
        for row in ws.iter_rows(min_col=1, max_col=2):
            label, value = row[0].value, row[1].value
            if label is None or value is None:
                continue
            raw[str(label).strip()] = str(value).strip()

        brief = Brief(raw=raw)
        for label, attr in _LABEL_MAP.items():
            text = raw.get(label)
            if text is None:
                continue
            if attr == "total_budget":
                setattr(brief, attr, parse_number(text))
            else:
                setattr(brief, attr, text)

        for attr in _REQUIRED:
            if not getattr(brief, attr):
                report.add(f"需求单缺少必填项「{attr}」，需要与客户确认")
        return brief
