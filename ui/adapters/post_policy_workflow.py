from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from datetime import datetime, timezone
from uuid import uuid4

from agent.export_table import export_recommendations
from agent.nodes.advice import make_advice_node
from agent.nodes.portfolio import make_portfolio_handoff_node
from ui.models.errors import WorkflowConflictError
from ui.models.run import RunContext
from ui.view_models.post_policy import FinalReviewDecision


class PostPolicyWorkflowAdapter:
    """协调报价、内容建议、人工审核与导出并保留上游证据。"""

    def __init__(self, *, exporter: Callable = export_recommendations,
                 portfolio_node_factory: Callable = make_portfolio_handoff_node,
                 advice_node_factory: Callable = make_advice_node,
                 id_factory: Callable[[], str] | None = None) -> None:
        """注入业务节点与文件导出边界。"""
        self.exporter = exporter
        self.portfolio_node_factory = portfolio_node_factory
        self.advice_node_factory = advice_node_factory
        self.id_factory = id_factory or (lambda: uuid4().hex)

    def advance(self, context: RunContext) -> RunContext:
        """从已完成审核推进至报价与内容建议。"""
        state = context.latest_state
        if state.get("recommendations") or context.interrupt_type:
            return context
        if state.get("workflow_status") in {"portfolio_repricing", "portfolio_generating"} or not (state.get("portfolio_plan") or {}).get("lines") or state.get("portfolio_error"):
            state["workflow_status"] = "portfolio_generating"
            state.update(self.portfolio_node_factory(context.clients.portfolio)(state))
        if state.get("portfolio_error") or not (state.get("portfolio_plan") or {}).get("lines"):
            return context
        state["workflow_status"] = "advice_generating"
        state.update(self.advice_node_factory(context.clients.advice, output_dir=context.files.run_dir)(state))
        state["review_status"] = "pending"
        return context

    def review(self, context: RunContext, decision: FinalReviewDecision) -> RunContext:
        """按当前任务及报价版本记录最终审核决定。"""
        self._validate(context, decision)
        if decision.action == "reprice":
            self._reject(context, decision.feedback.strip())
            return self.advance(context)
        state = context.latest_state
        entry = {"decision": "approved", "source": "streamlit", "reviewed_at": self._now(),
                 "portfolio_revision": decision.expected_revision}
        state.update(review_status="approved", human_review=entry)
        state.setdefault("human_review_history", []).append(deepcopy(entry))
        return self._export(context)

    def retry(self, context: RunContext) -> RunContext:
        """仅重试当前失败阶段，避免重复评分与审批。"""
        state = context.latest_state
        status = str(state.get("workflow_status") or "")
        if status == "export_failed" and state.get("review_status") == "approved":
            return self._export(context)
        if context.interrupt_type or status not in {"advice_generating", "portfolio_generating", "portfolio_repricing"}:
            raise WorkflowConflictError("当前步骤无需重试")
        return self.advance(context)

    def replan(self, context: RunContext, feedback: str) -> RunContext:
        """使用补充意见恢复未形成可执行方案的报价阶段。"""
        if context.interrupt_type or context.latest_state.get("recommendations"):
            raise WorkflowConflictError("当前不在方案调整阶段")
        if not feedback.strip():
            raise WorkflowConflictError("修改意见不能为空")
        self._reject(context, feedback.strip())
        return self.advance(context)

    def _reject(self, context: RunContext, feedback: str) -> None:
        """归档旧建议并使其审批与下载路径失效。"""
        state = context.latest_state
        revision = int((state.get("portfolio_plan") or {}).get("revision") or 0)
        state.setdefault("human_review_history", []).append({
            "decision": "rejected", "source": "streamlit", "reviewed_at": self._now(),
            "portfolio_revision": revision, "feedback": feedback,
        })
        if state.get("recommendations"):
            state.setdefault("advice_history", []).append({
                "portfolio_revision": revision, "recommendations": deepcopy(state["recommendations"]),
                "preview_path": state.get("advice_preview_path"), "pricing_feedback": feedback,
            })
        state["portfolio_feedback"] = {"comments": feedback, "feedback_id": self.id_factory()}
        for field in ("recommendations", "human_review", "final_export_path", "final_export_error",
                      "advice_preview_path", "advice_preview_error"):
            state.pop(field, None)
        state["review_status"] = "pending"
        state["workflow_status"] = "portfolio_repricing"

    def _export(self, context: RunContext) -> RunContext:
        """独立重试文件导出并保留已经完成的审批。"""
        state = context.latest_state
        path = context.files.run_dir / f"recommendations_approved_{self.id_factory()}.xlsx"
        try:
            exported = self.exporter(state["recommendations"], path, review_status="approved")
        except Exception as exc:
            state.update(workflow_status="export_failed", final_export_error=str(exc))
            context.last_error = "交付表导出失败，请重试"
            return context
        state.update(final_export_path=str(exported), final_export_error=None, workflow_status="export_complete")
        state["next_step"] = {"name": "complete", "status": "complete", "implemented": True}
        context.last_error = None
        return context

    def _validate(self, context: RunContext, decision: FinalReviewDecision) -> None:
        """拒绝跨任务、过期版本和重复审批请求。"""
        state = context.latest_state
        if context.interrupt_type or state.get("workflow_status") not in {"advice_ready", "advice_needs_review"}:
            raise WorkflowConflictError("当前不在最终审核阶段")
        if decision.expected_run_id != context.run_id:
            raise WorkflowConflictError("审核请求不属于当前任务")
        revision = int((state.get("portfolio_plan") or {}).get("revision") or 0)
        if decision.expected_revision != revision:
            raise WorkflowConflictError("审核请求已失效")
        if state.get("review_status") not in {None, "pending"}:
            raise WorkflowConflictError("当前方案已处理")
        if not state.get("recommendations"):
            raise WorkflowConflictError("当前没有可审核的建议")
        if decision.action not in {"approve", "reprice"}:
            raise WorkflowConflictError("不支持的审核操作")
        if decision.action == "reprice" and not decision.feedback.strip():
            raise WorkflowConflictError("修改意见不能为空")

    @staticmethod
    def _now() -> str:
        """以统一时区记录审核时间。"""
        return datetime.now(timezone.utc).isoformat()
