from __future__ import annotations

from collections.abc import Callable
from typing import Any
from uuid import uuid4

from agent.advice_review import approve_and_export, regenerate_after_rejection, reject_for_repricing
from agent.nodes.advice import make_advice_node
from agent.nodes.portfolio import make_portfolio_handoff_node
from ui.adapters.langgraph_workflow import WorkflowConflictError
from ui.models.run import RunContext
from ui.view_models.post_policy import FinalReviewDecision


class PostPolicyWorkflowAdapter:
    def __init__(
        self,
        *,
        approver: Callable[..., bool] = approve_and_export,
        rejector: Callable[..., bool] = reject_for_repricing,
        regenerator: Callable[..., bool] = regenerate_after_rejection,
        portfolio_node_factory: Callable[..., Any] = make_portfolio_handoff_node,
        advice_node_factory: Callable[..., Any] = make_advice_node,
        id_factory: Callable[[], str] | None = None,
    ) -> None:
        self.approver = approver
        self.rejector = rejector
        self.regenerator = regenerator
        self.portfolio_node_factory = portfolio_node_factory
        self.advice_node_factory = advice_node_factory
        self.id_factory = id_factory or (lambda: uuid4().hex)

    def review(self, context: RunContext, decision: FinalReviewDecision) -> RunContext:
        self._validate(context, decision)
        identifier = self.id_factory()
        try:
            if decision.action == "approve":
                self.approver(
                    context.latest_state,
                    context.files.run_dir,
                    source="streamlit",
                    export_id=identifier,
                )
            else:
                self.rejector(
                    context.latest_state,
                    decision.feedback.strip(),
                    source="streamlit",
                    feedback_id=identifier,
                )
                reprice = self.portfolio_node_factory(context.clients.portfolio)
                advise = self.advice_node_factory(
                    context.clients.advice,
                    output_dir=context.files.run_dir,
                )
                self.regenerator(
                    context.latest_state,
                    reprice_node=reprice,
                    advice_node=advise,
                )
        except Exception as exc:
            context.last_error = str(exc)
            raise
        context.last_error = context.latest_state.get("final_export_error")
        return context

    def _validate(self, context: RunContext, decision: FinalReviewDecision) -> None:
        status = str(context.latest_state.get("workflow_status") or "")
        if status not in {"advice_ready", "advice_needs_review"}:
            raise WorkflowConflictError("当前不在最终审核阶段")
        revision = int((context.latest_state.get("portfolio_plan") or {}).get("revision") or 0)
        if decision.expected_revision != revision:
            raise WorkflowConflictError("审核请求已失效")
        if context.latest_state.get("review_status") not in {None, "pending"}:
            raise WorkflowConflictError("当前方案已处理")
        if decision.action not in {"approve", "reprice"}:
            raise WorkflowConflictError("不支持的审核操作")
        if decision.action == "reprice" and not decision.feedback.strip():
            raise WorkflowConflictError("修改意见不能为空")
