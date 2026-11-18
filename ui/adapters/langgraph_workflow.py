from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from typing import Any
from uuid import uuid4

from langgraph.types import Command

from agent.graph import build_graph
from agent.llm_routing import ModuleLLMClients
from ui.models.run import RunContext, RunFiles
from ui.view_models.workflow import ClientAnswer, PolicyDecision


class WorkflowConflictError(RuntimeError):
    pass


class LangGraphWorkflowAdapter:
    def __init__(
        self,
        *,
        client_factory: Callable[[], Any] = ModuleLLMClients.from_env,
        graph_factory: Callable[..., Any] = build_graph,
        thread_factory: Callable[[], str] | None = None,
    ) -> None:
        self.client_factory = client_factory
        self.graph_factory = graph_factory
        self.thread_factory = thread_factory or (lambda: f"ui-{uuid4().hex}")

    def start(self, run_id: str, files: RunFiles) -> RunContext:
        clients = self.client_factory()
        graph = self.graph_factory(
            clients.requirements,
            evaluation_llm_client=clients.evaluation,
            audit_llm_client=clients.audit,
            portfolio_llm_client=clients.portfolio,
            advice_llm_client=clients.advice,
            advice_output_dir=files.run_dir,
        )
        thread_id = self.thread_factory()
        config = {
            "configurable": {"thread_id": thread_id},
            "recursion_limit": 64,
        }
        state = graph.invoke(
            {
                "brief_path": str(files.brief_path),
                "talent_path": str(files.talent_path),
                "policy_revision_count": 0,
            },
            config=config,
        )
        interrupt_type, payload, interrupt_id = self._interrupt(state, thread_id)
        return RunContext(
            run_id=run_id,
            thread_id=thread_id,
            graph=graph,
            clients=clients,
            config=config,
            files=files,
            latest_state=state,
            interrupt_type=interrupt_type,
            interrupt_payload=payload,
            interrupt_id=interrupt_id,
        )

    def resume_policy(self, context: RunContext, decision: PolicyDecision) -> RunContext:
        self._validate_policy_decision(context, decision)
        resume = {"action": decision.action}
        if decision.action == "revise":
            resume["feedback"] = decision.feedback.strip()
        try:
            state = context.graph.invoke(Command(resume=resume), config=context.config)
        except Exception as exc:
            context.last_error = str(exc)
            raise
        context.consumed_interrupt_ids.add(decision.expected_interrupt_id)
        context.latest_state = state
        context.last_error = None
        interrupt_type, payload, interrupt_id = self._interrupt(state, context.thread_id)
        context.interrupt_type = interrupt_type
        context.interrupt_payload = payload
        context.interrupt_id = interrupt_id
        return context

    def resume_client_confirmation(self, context: RunContext, answer: ClientAnswer) -> RunContext:
        self._validate_client_answer(context, answer)
        try:
            state = context.graph.invoke(
                Command(resume={"answers": answer.answers.strip()}),
                config=context.config,
            )
        except Exception as exc:
            context.last_error = str(exc)
            raise
        context.consumed_interrupt_ids.add(answer.expected_interrupt_id)
        context.latest_state = state
        context.last_error = None
        interrupt_type, payload, interrupt_id = self._interrupt(state, context.thread_id)
        context.interrupt_type = interrupt_type
        context.interrupt_payload = payload
        context.interrupt_id = interrupt_id
        return context

    def _validate_policy_decision(self, context: RunContext, decision: PolicyDecision) -> None:
        if context.interrupt_type != "policy_review":
            raise WorkflowConflictError("当前不在筛选策略审核阶段")
        if not context.interrupt_id or decision.expected_interrupt_id != context.interrupt_id:
            raise WorkflowConflictError("审核请求已失效")
        if decision.expected_interrupt_id in context.consumed_interrupt_ids:
            raise WorkflowConflictError("审核请求已处理")
        if decision.action not in {"approve", "revise"}:
            raise WorkflowConflictError("不支持的审核操作")
        if decision.action == "revise" and not decision.feedback.strip():
            raise WorkflowConflictError("修改意见不能为空")

    def _validate_client_answer(self, context: RunContext, answer: ClientAnswer) -> None:
        if context.interrupt_type != "client_confirmation":
            raise WorkflowConflictError("当前不在客户补充阶段")
        if not context.interrupt_id or answer.expected_interrupt_id != context.interrupt_id:
            raise WorkflowConflictError("补充请求已失效")
        if answer.expected_interrupt_id in context.consumed_interrupt_ids:
            raise WorkflowConflictError("补充请求已处理")
        if not answer.answers.strip():
            raise WorkflowConflictError("客户答复不能为空")

    def _interrupt(self, state: dict[str, Any], thread_id: str) -> tuple[str | None, dict[str, Any], str | None]:
        interrupts = state.get("__interrupt__") or []
        if not interrupts:
            return None, {}, None
        current = interrupts[0]
        payload = getattr(current, "value", {})
        payload = payload if isinstance(payload, dict) else {}
        interrupt_type = str(payload.get("type") or "unknown")
        identifier = getattr(current, "id", None) or self._fallback_id(thread_id, state, payload)
        return interrupt_type, payload, str(identifier)

    def _fallback_id(self, thread_id: str, state: dict[str, Any], payload: dict[str, Any]) -> str:
        value = {
            "thread_id": thread_id,
            "payload": payload,
            "workflow_status": state.get("workflow_status"),
        }
        encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()
