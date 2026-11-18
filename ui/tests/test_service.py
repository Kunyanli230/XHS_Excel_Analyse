from types import SimpleNamespace

from ui.adapters.streamlit_run_store import StreamlitRunStore
from ui.services.workflow_service import WorkflowService
from ui.tests.fixtures import make_context
from ui.view_models.post_policy import FinalReviewDecision
from ui.view_models.workflow import RunPhase, UploadInput, map_workflow


def test_completed_view_keeps_results_visible(tmp_path):
    """导出成功后仍保留各结果页。"""
    context = make_context(tmp_path)
    context.latest_state.update(workflow_status="export_complete", review_status="approved")
    view = map_workflow(context)
    assert view.phase is RunPhase.COMPLETED
    assert view.advice_review.candidates
    assert not view.advice_review.can_approve


def test_service_always_releases_busy_state_after_downstream_failure(tmp_path):
    """下游调用失败不能锁死会话或丢失达人结果。"""
    context = make_context(tmp_path)
    store = StreamlitRunStore({})
    store.save(context)

    def fail(*args):
        """模拟外部服务中断。"""
        raise RuntimeError("secret internal endpoint")

    service = WorkflowService(None, None, store, post_policy=SimpleNamespace(review=fail))
    view = service.decide_final(FinalReviewDecision("approve", 1, expected_run_id="run-a"))
    assert not store.get().busy
    assert view.phase is RunPhase.ADVICE_REVIEW
    assert view.error == "处理失败，请重试"
    assert view.advice_review.candidates


def test_busy_service_does_not_submit_a_second_approval(tmp_path):
    """重复点击不能在忙碌状态下再次审批。"""
    context = make_context(tmp_path, busy=True)
    store = StreamlitRunStore({})
    store.save(context)
    service = WorkflowService(None, None, store, post_policy=SimpleNamespace())
    assert service.decide_final(FinalReviewDecision("approve", 1)).phase is RunPhase.RUNNING


def test_sessions_never_share_run_context(tmp_path):
    """不同浏览器会话拥有独立的运行状态。"""
    first, second = StreamlitRunStore({}), StreamlitRunStore({})
    first.save(make_context(tmp_path))
    assert second.get() is None
    first.clear()
    assert first.get() is None


def test_export_failure_exposes_retry_without_repricing(tmp_path):
    """导出失败只提供文件重试入口。"""
    context = make_context(tmp_path)
    context.latest_state.update(workflow_status="export_failed", review_status="approved")
    view = map_workflow(context)
    assert view.phase is RunPhase.ACTION_REQUIRED
    assert view.retry_available
    assert not view.replan_available
    assert not view.advice_review.can_approve


def test_empty_portfolio_retains_candidates_and_recovery(tmp_path):
    """无可投放项时仍展示达人与方案调整入口。"""
    context = make_context(tmp_path)
    context.latest_state.update(workflow_status="portfolio_no_candidates", recommendations=[])
    context.latest_state["portfolio_plan"]["lines"] = []
    view = map_workflow(context)
    assert view.phase is RunPhase.ACTION_REQUIRED
    assert view.replan_available
    assert len(view.advice_review.candidates) == 3


def test_lost_approved_artifact_can_be_regenerated_without_new_approval(tmp_path):
    """丢失文件可独立重导出且不重复记录审批。"""
    store = StreamlitRunStore({})
    store.save(make_context(tmp_path))
    service = WorkflowService(None, None, store)
    service.decide_final(FinalReviewDecision("approve", 1, expected_run_id="run-a"))
    from pathlib import Path
    Path(store.get().latest_state["final_export_path"]).unlink()
    assert service.current().retry_available
    assert service.retry().phase is RunPhase.COMPLETED
    assert service.download("final").content.startswith(b"PK")
    assert len(store.get().latest_state["human_review_history"]) == 1


def test_start_failure_does_not_expose_backend_configuration(tmp_path):
    """开始任务失败时保留简洁错误并清理本次上传。"""
    removed = []
    files = make_context(tmp_path).files
    def fail(*args):
        """模拟后端配置不可用。"""
        raise RuntimeError("private endpoint API_KEY configuration")
    service = WorkflowService(SimpleNamespace(save=lambda *args: files, remove=removed.append),
                              SimpleNamespace(start=fail), StreamlitRunStore({}))
    view = service.start(UploadInput("b.xlsx", b"", "t.xlsx", b""))
    assert view.error == "分析失败，请重试"
    assert removed == [files]
