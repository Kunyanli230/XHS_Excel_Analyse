from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from ui.models.run import RunContext
from ui.view_models.post_policy import AdviceReviewView, map_advice_review


class RunPhase(StrEnum):
    EMPTY = "empty"
    RUNNING = "running"
    CLIENT_CONFIRMATION = "client_confirmation"
    POLICY_REVIEW = "policy_review"
    ADVICE_REVIEW = "advice_review"
    ACTION_REQUIRED = "action_required"
    COMPLETED = "completed"
    UNSUPPORTED_INTERRUPT = "unsupported_interrupt"
    FAILED = "failed"


@dataclass(frozen=True)
class UploadInput:
    brief_name: str
    brief_bytes: bytes
    talent_name: str
    talent_bytes: bytes


@dataclass(frozen=True)
class PolicyDecision:
    action: str
    expected_interrupt_id: str
    feedback: str = ""


@dataclass(frozen=True)
class ClientAnswer:
    answers: str
    expected_interrupt_id: str


@dataclass(frozen=True)
class ClientConfirmationView:
    interrupt_id: str
    questions: tuple[str, ...]
    message: str


@dataclass(frozen=True)
class PolicyCriterionView:
    field: str
    operator: str
    value: Any
    weight: float | None
    reason: str


@dataclass(frozen=True)
class PolicyReviewView:
    interrupt_id: str
    name: str
    hard_criteria: tuple[PolicyCriterionView, ...]
    scoring_criteria: tuple[PolicyCriterionView, ...]
    manual_checks: tuple[str, ...]
    rationale: str
    revision_count: int


@dataclass(frozen=True)
class WorkflowView:
    phase: RunPhase
    run_id: str | None = None
    thread_id: str | None = None
    client_confirmation: ClientConfirmationView | None = None
    policy_review: PolicyReviewView | None = None
    advice_review: AdviceReviewView | None = None
    message: str = ""
    error: str | None = None
    busy: bool = False


def map_workflow(context: RunContext | None) -> WorkflowView:
    if context is None:
        return WorkflowView(phase=RunPhase.EMPTY)
    if context.busy:
        return WorkflowView(
            phase=RunPhase.RUNNING,
            run_id=context.run_id,
            thread_id=context.thread_id,
            message="正在处理",
            busy=True,
        )
    if context.interrupt_type == "policy_review":
        return _policy_view(context)
    if context.interrupt_type == "client_confirmation":
        confirmation = ClientConfirmationView(
            interrupt_id=str(context.interrupt_id or ""),
            questions=tuple(str(item) for item in context.interrupt_payload.get("questions") or []),
            message=str(context.interrupt_payload.get("message") or "等待客户确认"),
        )
        return WorkflowView(
            phase=RunPhase.CLIENT_CONFIRMATION,
            run_id=context.run_id,
            thread_id=context.thread_id,
            client_confirmation=confirmation,
            message=confirmation.message,
            error=context.last_error,
        )
    if context.interrupt_type:
        return WorkflowView(
            phase=RunPhase.UNSUPPORTED_INTERRUPT,
            run_id=context.run_id,
            thread_id=context.thread_id,
            message="当前步骤暂不可操作",
            error=context.last_error,
        )
    status = str(context.latest_state.get("workflow_status") or "")
    if status in {"advice_ready", "advice_needs_review"}:
        return WorkflowView(
            phase=RunPhase.ADVICE_REVIEW,
            run_id=context.run_id,
            thread_id=context.thread_id,
            advice_review=map_advice_review(context.latest_state),
            message="等待最终审核",
            error=context.last_error,
        )
    if status == "export_complete":
        return WorkflowView(
            phase=RunPhase.COMPLETED,
            run_id=context.run_id,
            thread_id=context.thread_id,
            message="交付表已生成",
            error=context.last_error,
        )
    portfolio_error = context.latest_state.get("portfolio_error")
    error = context.last_error
    if isinstance(portfolio_error, dict):
        error = str(portfolio_error.get("message") or portfolio_error.get("type") or error or "需要补充信息")
    return WorkflowView(
        phase=RunPhase.ACTION_REQUIRED,
        run_id=context.run_id,
        thread_id=context.thread_id,
        message="需要处理",
        error=error,
    )


def _policy_view(context: RunContext) -> WorkflowView:
    policy = context.interrupt_payload.get("policy") or {}
    hard: list[PolicyCriterionView] = []
    scoring: list[PolicyCriterionView] = []
    for raw in policy.get("criteria") or []:
        item = PolicyCriterionView(
            field=str(raw.get("field") or ""),
            operator=str(raw.get("operator") or ""),
            value=raw.get("value"),
            weight=float(raw["weight"]) if isinstance(raw.get("weight"), (int, float)) else None,
            reason=str(raw.get("reason") or ""),
        )
        (hard if raw.get("hard") else scoring).append(item)
    review = PolicyReviewView(
        interrupt_id=str(context.interrupt_id or ""),
        name=str(policy.get("name") or "筛选策略"),
        hard_criteria=tuple(hard),
        scoring_criteria=tuple(scoring),
        manual_checks=tuple(str(item) for item in policy.get("manual_checks") or []),
        rationale=str(policy.get("rationale") or ""),
        revision_count=int(context.latest_state.get("policy_revision_count") or 0),
    )
    return WorkflowView(
        phase=RunPhase.POLICY_REVIEW,
        run_id=context.run_id,
        thread_id=context.thread_id,
        policy_review=review,
        message="等待审核",
        error=context.last_error,
    )
