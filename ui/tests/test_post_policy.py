from copy import deepcopy

import pytest

from ui.adapters.post_policy_workflow import PostPolicyWorkflowAdapter
from ui.models.errors import WorkflowConflictError
from ui.tests.fixtures import make_context
from ui.view_models.post_policy import FinalReviewDecision, map_advice_review


def test_approval_exports_once_and_preserves_results(tmp_path):
    """最终批准只导出一次且保留原始评估结果。"""
    context = make_context(tmp_path)
    original = deepcopy(context.latest_state["audited_talents"])
    adapter = PostPolicyWorkflowAdapter()
    decision = FinalReviewDecision("approve", 1, expected_run_id="run-a")
    adapter.review(context, decision)
    assert context.latest_state["workflow_status"] == "export_complete"
    assert context.latest_state["review_status"] == "approved"
    assert context.latest_state["audited_talents"] == original
    assert len(list(tmp_path.glob("recommendations_approved_*.xlsx"))) == 1
    with pytest.raises(WorkflowConflictError):
        adapter.review(context, decision)


@pytest.mark.parametrize("decision", [
    FinalReviewDecision("approve", 0, expected_run_id="run-a"),
    FinalReviewDecision("approve", 1, expected_run_id="another-run"),
    FinalReviewDecision("reprice", 1, "  ", expected_run_id="run-a"),
])
def test_stale_or_empty_decision_does_not_mutate_state(tmp_path, decision):
    """失效或空白请求不能修改审核状态。"""
    context = make_context(tmp_path)
    original = deepcopy(context.latest_state)
    with pytest.raises(WorkflowConflictError):
        PostPolicyWorkflowAdapter().review(context, decision)
    assert context.latest_state == original


def test_repricing_invalidates_deliverables_and_retains_audit(tmp_path):
    """打回重定价保留审核证据并清除旧交付。"""
    context = make_context(tmp_path)
    context.latest_state.update(final_export_path="old.xlsx", advice_preview_path="old-preview.xlsx")
    original = deepcopy(context.latest_state["audited_talents"])

    def portfolio(_client):
        """检查旧结果已失效并返回新报价。"""
        def run(state):
            """返回第二版报价。"""
            assert not state.get("recommendations")
            assert not state.get("final_export_path")
            plan = deepcopy(state["portfolio_plan"])
            plan["revision"] = 2
            return {"portfolio_plan": plan, "portfolio_error": None}
        return run

    def advice(_client, **kwargs):
        """仅在运行目录内生成新建议。"""
        assert kwargs["output_dir"] == tmp_path
        return lambda state: {"recommendations": [{"nickname": "新建议"}], "workflow_status": "advice_ready"}

    adapter = PostPolicyWorkflowAdapter(portfolio_node_factory=portfolio, advice_node_factory=advice)
    adapter.review(context, FinalReviewDecision("reprice", 1, "降低报价", expected_run_id="run-a"))
    assert context.latest_state["portfolio_plan"]["revision"] == 2
    assert context.latest_state["review_status"] == "pending"
    assert context.latest_state["audited_talents"] == original
    assert len(context.latest_state["advice_history"]) == 1
    assert not context.latest_state.get("final_export_path")


def test_export_failure_can_retry_without_reapproval(tmp_path):
    """导出重试复用已记录的人工审批。"""
    context = make_context(tmp_path)
    calls = []

    def export(rows, path, **kwargs):
        """模拟首次写入失败。"""
        calls.append(path)
        if len(calls) == 1:
            raise OSError("文件被占用")
        path.write_bytes(b"xlsx")
        return path

    adapter = PostPolicyWorkflowAdapter(exporter=export)
    adapter.review(context, FinalReviewDecision("approve", 1, expected_run_id="run-a"))
    assert context.latest_state["workflow_status"] == "export_failed"
    adapter.retry(context)
    assert context.latest_state["workflow_status"] == "export_complete"
    assert len(context.latest_state["human_review_history"]) == 1


def test_unexpected_export_error_still_exposes_recovery(tmp_path):
    """非预期导出异常同样保留审批并进入重试状态。"""
    def fail(*args, **kwargs):
        """模拟第三方导出库异常。"""
        raise TypeError("broken exporter")
    context = make_context(tmp_path)
    PostPolicyWorkflowAdapter(exporter=fail).review(context, FinalReviewDecision("approve", 1, expected_run_id="run-a"))
    assert context.latest_state["workflow_status"] == "export_failed"
    assert context.latest_state["review_status"] == "approved"


def test_valid_empty_plan_cannot_be_retried_without_changes(tmp_path):
    """成功但空的方案需要调整条件而不是原样重跑。"""
    context = make_context(tmp_path)
    context.latest_state.update(workflow_status="portfolio_no_candidates", recommendations=[])
    context.latest_state["portfolio_plan"]["lines"] = []
    with pytest.raises(WorkflowConflictError):
        PostPolicyWorkflowAdapter().retry(context)


def test_view_uses_audit_summary_and_carries_review_risks(tmp_path):
    """视图保留审核待处理项与核对事项。"""
    view = map_advice_review(make_context(tmp_path).latest_state)
    assert view.audit.pending_count == 1
    assert view.candidates[1].stance_label == "不推荐"
    assert view.candidates[0].band_label == "明确推荐"
    assert view.unverified_checks == ("核对近期品牌合作记录",)
    assert view.portfolio.kpis[0].status_label == "未达目标"


def test_held_candidate_is_not_counted_as_available_when_summary_missing(tmp_path):
    """汇总缺失时仍区分暂存与可投放记录。"""
    state = make_context(tmp_path).latest_state
    state.pop("audit_summary")
    view = map_advice_review(state)
    assert (view.audit.input_count, view.audit.recommended_count, view.audit.rejected_count, view.audit.pending_count) == (3, 1, 1, 1)
