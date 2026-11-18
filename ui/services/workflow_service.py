from __future__ import annotations

from collections.abc import Callable
from typing import Any
from uuid import uuid4

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
    ) -> None:
        self.upload_store = upload_store
        self.workflow = workflow
        self.run_store = run_store
        self.run_id_factory = run_id_factory or (lambda: uuid4().hex)

    def current(self) -> WorkflowView:
        context = self.run_store.get()
        if context is not None:
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
            self.run_store.set_error(str(exc))
            return WorkflowView(phase=RunPhase.FAILED, error=str(exc), message="运行失败")
        previous = self.run_store.get()
        self.run_store.save(context)
        self.run_store.set_error(None)
        if previous is not None and previous.files.run_dir != files.run_dir:
            self.upload_store.remove(previous.files)
        return map_workflow(context)

    def decide_policy(self, decision: PolicyDecision) -> WorkflowView:
        context = self.run_store.get()
        if context is None:
            return WorkflowView(phase=RunPhase.FAILED, error="没有可恢复的任务", message="运行失败")
        if context.busy:
            return map_workflow(context)
        context.busy = True
        self.run_store.save(context)
        try:
            context = self.workflow.resume_policy(context, decision)
        except Exception as exc:
            context.last_error = str(exc)
            return map_workflow(context)
        finally:
            context.busy = False
            self.run_store.save(context)
        self.run_store.set_error(None)
        return map_workflow(context)

    def answer_client(self, answer: ClientAnswer) -> WorkflowView:
        context = self.run_store.get()
        if context is None:
            return WorkflowView(phase=RunPhase.FAILED, error="没有可恢复的任务", message="运行失败")
        if context.busy:
            return map_workflow(context)
        context.busy = True
        self.run_store.save(context)
        try:
            context = self.workflow.resume_client_confirmation(context, answer)
        except Exception as exc:
            context.last_error = str(exc)
            return map_workflow(context)
        finally:
            context.busy = False
            self.run_store.save(context)
        self.run_store.set_error(None)
        return map_workflow(context)

    def reset(self) -> WorkflowView:
        context = self.run_store.clear()
        self.run_store.set_error(None)
        if context is not None:
            self.upload_store.remove(context.files)
        return map_workflow(None)
