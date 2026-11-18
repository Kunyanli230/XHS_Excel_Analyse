from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Any

from ui.view_models.labels import BAND_LABELS, STANCE_LABELS, RISK_LABELS, KPI_LABELS, KPI_STATUS_LABELS, business_warning


@dataclass(frozen=True)
class AuditSummaryView:
    input_count: int
    recommended_count: int
    rejected_count: int
    pending_count: int


@dataclass(frozen=True)
class CandidateView:
    xhs_id: str
    nickname: str
    band: str
    score: float | None
    stance: str
    tag: str
    sentence: str
    audit_status: str
    release_status: str
    data_incomplete: bool

    @property
    def band_label(self) -> str:
        """返回顾问可读的档位。"""
        return BAND_LABELS.get(self.band, "待评估")

    @property
    def stance_label(self) -> str:
        """将后台判断映射为中文结论。"""
        return "待处理" if self.release_status == "held_for_review" else STANCE_LABELS.get(self.stance, "待处理")


@dataclass(frozen=True)
class KpiView:
    """保存用于方案复核的效果估算。"""
    label: str
    target: float | None
    estimated: float | None
    status_label: str


@dataclass(frozen=True)
class PortfolioLineView:
    xhs_id: str
    nickname: str
    format: str
    format_label: str
    quantity: int
    unit_price_low: float
    unit_price_suggested: float
    unit_price_high: float
    total_suggested: float
    risk_flags: tuple[str, ...]


@dataclass(frozen=True)
class PortfolioView:
    revision: int
    status: str
    budget_limit: float
    total_suggested: float
    total_upper: float
    lines: tuple[PortfolioLineView, ...]
    warnings: tuple[str, ...]
    kpis: tuple[KpiView, ...] = ()
    conditional_names: tuple[str, ...] = ()


@dataclass(frozen=True)
class RecommendationView:
    xhs_id: str
    nickname: str
    format: str
    format_label: str
    quantity: int
    unit_price: float
    total_price: float
    tag: str
    sentence: str
    angle: str
    sub_angle: str
    details: str
    warnings: tuple[str, ...]
    remarks: tuple[str, ...]
    advice_status: str
    advice_error: str | None


@dataclass(frozen=True)
class AdviceReviewView:
    audit: AuditSummaryView
    candidates: tuple[CandidateView, ...]
    portfolio: PortfolioView
    recommendations: tuple[RecommendationView, ...]
    preview_available: bool
    preview_error: str | None
    workflow_status: str
    unverified_checks: tuple[str, ...] = ()
    approved: bool = False
    can_approve: bool = False


@dataclass(frozen=True)
class FinalReviewDecision:
    action: str
    expected_revision: int
    feedback: str = ""
    expected_run_id: str = ""


def map_advice_review(state: dict[str, Any]) -> AdviceReviewView:
    """将后端结果投影成只读审核视图。"""
    summary = state.get("audit_summary") or {}
    plan = state.get("portfolio_plan") or {}
    budget = plan.get("budget") or {}
    candidates = tuple(_candidate(item) for item in state.get("audited_talents") or [] if isinstance(item, dict))
    pending = sum(item.stance_label == "待处理" for item in candidates)
    status = str(state.get("workflow_status") or "")
    return AdviceReviewView(
        audit=AuditSummaryView(
            input_count=_integer(summary.get("entered_count", summary.get("input_count", len(candidates)))),
            recommended_count=_integer(summary.get("usable_recommendations", summary.get("recommended_count", sum(item.stance_label == "推荐" for item in candidates)))),
            rejected_count=_integer(summary.get("rejected_count", sum(item.stance_label == "不推荐" for item in candidates))),
            pending_count=_integer(summary.get("held_count", summary.get("pending_count", pending))),
        ),
        candidates=candidates,
        portfolio=PortfolioView(
            revision=_integer(plan.get("revision")),
            status=str(plan.get("status") or ""),
            budget_limit=_number(budget.get("limit", (state.get("brief") or {}).get("total_budget"))),
            total_suggested=_number(budget.get("total_suggested")),
            total_upper=_number(budget.get("total_upper")),
            lines=tuple(_portfolio_line(item) for item in plan.get("lines") or [] if isinstance(item, dict)),
            warnings=tuple(dict.fromkeys(business_warning(item) for item in _strings(plan.get("warnings")))),
            kpis=tuple(KpiView(KPI_LABELS.get(key, "其他指标"), _optional_number(item.get("target")),
                              _optional_number(item.get("estimate")),
                              KPI_STATUS_LABELS.get(str(item.get("status")), "待核实"))
                       for key, item in (plan.get("kpi_checks") or {}).items() if isinstance(item, dict)),
            conditional_names=tuple(str(item.get("nickname") or item.get("xhs_id") or "待核价达人")
                                    for item in plan.get("conditional_candidates") or [] if isinstance(item, dict)),
        ),
        recommendations=tuple(
            _recommendation(item)
            for item in state.get("recommendations") or []
            if isinstance(item, dict)
        ),
        preview_available=bool(state.get("advice_preview_path")),
        preview_error=str(state["advice_preview_error"]) if state.get("advice_preview_error") else None,
        workflow_status=status,
        unverified_checks=_checks(state.get("audit_unverified_checks")),
        approved=state.get("review_status") == "approved",
        can_approve=bool(state.get("recommendations")) and status in {"advice_ready", "advice_needs_review"}
                    and state.get("review_status") in {None, "pending"},
    )


def _candidate(item: dict[str, Any]) -> CandidateView:
    return CandidateView(
        xhs_id=str(item.get("xhs_id") or ""),
        nickname=str(item.get("nickname") or ""),
        band=str(item.get("band") or ""),
        score=_optional_number(item.get("score")),
        stance=str(item.get("stance") or ""),
        tag=str(item.get("tag") or ""),
        sentence=str(item.get("sentence") or ""),
        audit_status=str(item.get("audit_status") or ""),
        release_status=str(item.get("release_status") or ""),
        data_incomplete=bool(item.get("data_incomplete")),
    )


def _portfolio_line(item: dict[str, Any]) -> PortfolioLineView:
    format_name = str(item.get("format") or "")
    flags = item.get("risk_flags") or {}
    return PortfolioLineView(
        xhs_id=str(item.get("xhs_id") or ""),
        nickname=str(item.get("nickname") or ""),
        format=format_name,
        format_label={"image": "图文", "video": "视频"}.get(format_name, format_name),
        quantity=_integer(item.get("quantity")),
        unit_price_low=_number(item.get("unit_price_low")),
        unit_price_suggested=_number(item.get("unit_price_suggested")),
        unit_price_high=_number(item.get("unit_price_high")),
        total_suggested=_number(item.get("line_cost_suggested")),
        risk_flags=tuple(dict.fromkeys(RISK_LABELS.get(str(key), "待核实") for key, value in flags.items() if value)) if isinstance(flags, dict) else (),
    )


def _recommendation(item: dict[str, Any]) -> RecommendationView:
    format_name = str(item.get("format") or "")
    return RecommendationView(
        xhs_id=str(item.get("xhs_id") or ""),
        nickname=str(item.get("nickname") or (item.get("talent") or {}).get("nickname") or ""),
        format=format_name,
        format_label={"image_text": "图文", "video": "视频"}.get(format_name, format_name),
        quantity=_integer(item.get("quantity")),
        unit_price=_number(item.get("unit_price")),
        total_price=_number(item.get("total_price")),
        tag=str(item.get("tag") or (item.get("evaluation") or {}).get("tag") or ""),
        sentence=str(item.get("sentence") or (item.get("evaluation") or {}).get("sentence") or ""),
        angle=str(item.get("angle") or ""),
        sub_angle=str(item.get("sub_angle") or ""),
        details=str(item.get("details") or ""),
        warnings=_strings(item.get("warnings")),
        remarks=_strings(item.get("remarks")),
        advice_status=str(item.get("advice_status") or ""),
        advice_error=str(item["advice_error"]) if item.get("advice_error") else None,
    )


def _strings(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(str(item) for item in value if str(item).strip())


def _integer(value: Any) -> int:
    return int(value) if isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(value) else 0


def _number(value: Any) -> float:
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(value) else 0.0


def _optional_number(value: Any) -> float | None:
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(value) else None


def _checks(value: Any) -> tuple[str, ...]:
    """提取人工核对事项而不展示内部结构。"""
    return tuple(str(item.get("description") or item.get("text") or item.get("check") or item.get("message") or "待人工核对")
                 if isinstance(item, dict) else str(item) for item in value or [])
