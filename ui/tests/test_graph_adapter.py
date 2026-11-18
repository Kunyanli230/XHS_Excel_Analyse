from types import SimpleNamespace

import pytest
from langgraph.types import Interrupt

from ui.adapters.langgraph_workflow import LangGraphWorkflowAdapter
from ui.models.errors import WorkflowConflictError
from ui.models.run import RunFiles
from ui.view_models.workflow import PolicyDecision


def test_adapter_matches_real_backend_signature_and_disables_global_exports(tmp_path):
    """主图只推进审核，后续文件输出由运行目录隔离。"""
    from agent.graph import build_graph
    from inspect import signature

    calls = []

    def factory(*args, **kwargs):
        """使用真实后端签名检查接线。"""
        signature(build_graph).bind(*args, **kwargs)
        calls.append(kwargs)
        return SimpleNamespace(invoke=lambda *a, **k: {"__interrupt__": [Interrupt({"type": "policy_review", "policy": {}}, id="policy-1")]})

    clients = SimpleNamespace(requirements=None, evaluation=None, audit=None, portfolio=None, advice=None)
    adapter = LangGraphWorkflowAdapter(client_factory=lambda: clients, graph_factory=factory)
    context = adapter.start("run-a", RunFiles(tmp_path, tmp_path / "b.xlsx", tmp_path / "t.xlsx"))
    assert calls[0]["enable_portfolio"] is False
    assert context.interrupt_type == "policy_review"


def test_successful_resume_consumes_interrupt_before_downstream_processing(tmp_path):
    """已消费的策略审批不能再次恢复。"""
    from ui.tests.fixtures import make_context

    graph = SimpleNamespace(invoke=lambda *a, **k: {"workflow_status": "audit_complete", "audited_talents": []})
    context = make_context(tmp_path, graph=graph, interrupt_type="policy_review", interrupt_id="policy-1")
    adapter = LangGraphWorkflowAdapter()
    decision = PolicyDecision("approve", "policy-1")
    adapter.resume_policy(context, decision)
    assert context.interrupt_type is None
    with pytest.raises(WorkflowConflictError):
        adapter.resume_policy(context, decision)
