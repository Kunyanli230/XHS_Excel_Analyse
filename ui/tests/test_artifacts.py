import pytest

from ui.adapters.run_artifact_store import RunArtifactStore
from ui.tests.fixtures import make_context


def test_only_approved_current_run_artifact_is_downloadable(tmp_path):
    """正式下载需要当前任务的审批和导出状态。"""
    context = make_context(tmp_path / "run")
    path = context.files.run_dir / "final.xlsx"
    path.write_bytes(b"approved-workbook")
    context.latest_state["final_export_path"] = str(path)
    store = RunArtifactStore()
    with pytest.raises(ValueError):
        store.read(context, "final")
    context.latest_state.update(review_status="approved", workflow_status="export_complete")
    artifact = store.read(context, "final")
    assert artifact.content == b"approved-workbook"
    assert artifact.filename.endswith(".xlsx")


def test_preview_outside_run_directory_is_rejected(tmp_path):
    """下载文件不能跨运行目录。"""
    context = make_context(tmp_path / "run")
    outside = tmp_path / "other.xlsx"
    outside.write_bytes(b"other-user-data")
    context.latest_state["advice_preview_path"] = str(outside)
    with pytest.raises(ValueError):
        RunArtifactStore().read(context, "preview")


def test_missing_preview_is_reported_without_internal_paths(tmp_path):
    """丢失的导出文件返回可理解的错误。"""
    context = make_context(tmp_path)
    context.latest_state["advice_preview_path"] = str(tmp_path / "gone.xlsx")
    with pytest.raises(ValueError, match="文件不可用"):
        RunArtifactStore().read(context, "preview")
