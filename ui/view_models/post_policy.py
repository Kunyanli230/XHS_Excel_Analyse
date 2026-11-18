from __future__ import annotations

from dataclasses import dataclass
from typing import Any


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


@dataclass(frozen=True)
class FinalReviewDecision:
    action: str
    expected_revision: int
    feedback: str = ""


def map_advice_review(state: dict[str, Any]) -> AdviceReviewView:
    summary = state.get("audit_summary") or {}
    plan = state.get("portfolio_plan") or {}
    budget = plan.get("budget") or {}
    return AdviceReviewView(
        audit=AuditSummaryView(
            input_count=_integer(summary.get("input_count")),
            recommended_count=_integer(summary.get("recommended_count")),
            rejected_count=_integer(summary.get("rejected_count")),
            pending_count=_integer(summary.get("pending_count")),
        ),
        candidates=tuple(_candidate(item) for item in state.get("audited_talents") or [] if isinstance(item, dict)),
        portfolio=PortfolioView(
            revision=_integer(plan.get("revision")),
            status=str(plan.get("status") or ""),
            budget_limit=_number(budget.get("limit")),
            total_suggested=_number(budget.get("total_suggested")),
            total_upper=_number(budget.get("total_upper")),
            lines=tuple(_portfolio_line(item) for item in plan.get("lines") or [] if isinstance(item, dict)),
            warnings=_strings(plan.get("warnings")),
        ),
        recommendations=tuple(
            _recommendation(item)
            for item in state.get("recommendations") or []
            if isinstance(item, dict)
        ),
        preview_available=bool(state.get("advice_preview_path")),
        preview_error=str(state["advice_preview_error"]) if state.get("advice_preview_error") else None,
        workflow_status=str(state.get("workflow_status") or ""),
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
        risk_flags=tuple(str(key) for key, value in flags.items() if value) if isinstance(flags, dict) else (),
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
    return int(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else 0


def _number(value: Any) -> float:
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else 0.0


def _optional_number(value: Any) -> float | None:
    return _number(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None
