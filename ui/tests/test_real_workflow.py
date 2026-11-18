from io import BytesIO
from types import SimpleNamespace

from openpyxl import load_workbook

from agent.requirements import LLMClient
from tests.test_requirements import DATA, ResponseSequence, complete_profile, reason_draft, valid_policy
from ui.adapters.langgraph_workflow import LangGraphWorkflowAdapter
from ui.adapters.run_upload_store import RunUploadStore
from ui.adapters.streamlit_run_store import StreamlitRunStore
from ui.services.workflow_service import WorkflowService
from ui.view_models.post_policy import FinalReviewDecision
from ui.view_models.workflow import PolicyDecision, RunPhase, UploadInput


def test_real_graph_to_review_reprice_and_export_stays_within_run(tmp_path):
    """通过真实图和业务节点离线验证上传至正式交付。"""
    clients = SimpleNamespace(
        requirements=LLMClient(transport=ResponseSequence([complete_profile(), valid_policy()])),
        evaluation=LLMClient(transport=lambda *args: reason_draft()),
        audit=LLMClient(transport=lambda *args: {"verdict": "pass", "issues": []}),
        portfolio=None,
        advice=LLMClient(transport=lambda *args: {"angle": "场景种草", "sub_angle": "换季护肤",
                                                "details": "展示护肤步骤与产品质地。", "warnings": []}),
    )
    service = WorkflowService(RunUploadStore(tmp_path), LangGraphWorkflowAdapter(client_factory=lambda: clients),
                              StreamlitRunStore({}), run_id_factory=lambda: "offline-run")
    upload = UploadInput("brief.xlsx", (DATA / "甲方投放需求单_屿光精华.xlsx").read_bytes(),
                         "talents.xlsx", (DATA / "蒲公英达人数据_屿光精华.xlsx").read_bytes())
    view = service.start(upload)
    assert view.phase is RunPhase.POLICY_REVIEW
    view = service.decide_policy(PolicyDecision("approve", view.policy_review.interrupt_id))
    assert view.phase is RunPhase.ADVICE_REVIEW
    assert service.download("preview").content.startswith(b"PK")
    revision = view.advice_review.portfolio.revision
    view = service.decide_final(FinalReviewDecision("reprice", revision, "九折", expected_run_id="offline-run"))
    assert view.phase is RunPhase.ADVICE_REVIEW
    assert view.advice_review.portfolio.revision == revision + 1
    view = service.decide_final(FinalReviewDecision("approve", revision + 1, expected_run_id="offline-run"))
    assert view.phase is RunPhase.COMPLETED
    workbook = load_workbook(BytesIO(service.download("final").content))
    assert "达人推荐表" in workbook.sheetnames
    assert workbook["达人推荐表"].max_row > 1
    assert all(path.parent == tmp_path / "offline-run" for path in (tmp_path / "offline-run").glob("*.xlsx"))
