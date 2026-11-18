from __future__ import annotations

from collections.abc import Callable
from typing import Any
from uuid import uuid4

from ui.adapters.post_policy_workflow import PostPolicyWorkflowAdapter
from ui.adapters.run_artifact_store import RunArtifactStore
from ui.adapters.run_upload_store import UploadValidationError
from ui.models.errors import WorkflowConflictError
from ui.view_models.post_policy import FinalReviewDecision
from ui.view_models.workflow import (
    ClientAnswer,
    PolicyDecision,
    RunPhase,
    UploadInput,
    WorkflowView,
    map_workflow,
)


class WorkflowService:
    def __init__(
        self,
        upload_store: Any,
        workflow: Any,
        run_store: Any,
        *,
        run_id_factory: Callable[[], str] | None = None,
        post_policy: Any = None,
        artifact_store: Any = None,
    ) -> None:
        self.upload_store = upload_store
        self.workflow = workflow
        self.run_store = run_store
        self.run_id_factory = run_id_factory or (lambda: uuid4().hex)
        self.post_policy = post_policy or PostPolicyWorkflowAdapter()
        self.artifact_store = artifact_store or RunArtifactStore()

    def current(self) -> WorkflowView:
        context = self.run_store.get()
        if context is not None:
            if context.latest_state.get("workflow_status") == "export_complete":
                try:
                    self.artifact_store.read(context, "final")
                except ValueError:
                    context.latest_state["workflow_status"] = "export_failed"
                    context.last_error = "交付表不可用，请重新导出"
                    self.run_store.save(context)
            return map_workflow(context)
        error = self.run_store.get_error()
        if error:
            return WorkflowView(phase=RunPhase.FAILED, error=error, message="运行失败")
        return map_workflow(None)

    def start(self, uploaded: UploadInput) -> WorkflowView:
        current = self.run_store.get()
        if current is not None and current.busy:
            return map_workflow(current)
        run_id = self.run_id_factory()
        files = None
        try:
            files = self.upload_store.save(run_id, uploaded)
            context = self.workflow.start(run_id, files)
        except Exception as exc:
            if files is not None:
                self.upload_store.remove(files)
            message = str(exc) if isinstance(exc, UploadValidationError) else "分析失败，请重试"
            self.run_store.set_error(message)
            return WorkflowView(phase=RunPhase.FAILED, error=message, message="运行失败")
        previous = self.run_store.get()
        self.run_store.save(context)
        self.run_store.set_error(None)
        if previous is not None and previous.files.run_dir != files.run_dir:
            self.upload_store.remove(previous.files)
        return map_workflow(context)

    def decide_policy(self, decision: PolicyDecision) -> WorkflowView:
        """恢复策略审核后按需推进已完成的审核结果。"""
        return self._operate(lambda context: self._continue(self.workflow.resume_policy(context, decision)))

    def answer_client(self, answer: ClientAnswer) -> WorkflowView:
        """恢复客户答复并继续工作流。"""
        return self._operate(lambda context: self._continue(self.workflow.resume_client_confirmation(context, answer)))

    def decide_final(self, decision: FinalReviewDecision) -> WorkflowView:
        """提交针对当前任务与方案版本的最终决定。"""
        return self._operate(lambda context: self.post_policy.review(context, decision))

    def retry(self) -> WorkflowView:
        """重新执行失败的下游步骤。"""
        return self._operate(self.post_policy.retry)

    def replan(self, feedback: str) -> WorkflowView:
        """提交方案调整意见。"""
        return self._operate(lambda context: self.post_policy.replan(context, feedback))

    def download(self, kind: str):
        """读取当前任务可交付的文件。"""
        context = self.run_store.get()
        if context is None:
            raise ValueError("没有可下载的文件")
        return self.artifact_store.read(context, kind)

    def _operate(self, operation: Callable) -> WorkflowView:
        """串行处理状态变更并在异常后解除会话忙碌状态。"""
        context = self.run_store.get()
        if context is None:
            return WorkflowView(phase=RunPhase.FAILED, error="没有可恢复的任务", message="运行失败")
        if context.busy:
            return map_workflow(context)
        context.busy = True
        self.run_store.save(context)
        try:
            context.last_error = None
            context = operation(context)
        except Exception as exc:
            context.last_error = str(exc) if isinstance(exc, WorkflowConflictError) else "处理失败，请重试"
        finally:
            context.busy = False
            self.run_store.save(context)
        self.run_store.set_error(None)
        return map_workflow(context)

    def _continue(self, context):
        """在图完成审核后调用隔离的下游适配层。"""
        if not context.interrupt_type and context.latest_state.get("audited_talents") is not None:
            return self.post_policy.advance(context)
        return context

    def reset(self) -> WorkflowView:
        context = self.run_store.clear()
        self.run_store.set_error(None)
        if context is not None:
            self.upload_store.remove(context.files)
        return map_workflow(None)
