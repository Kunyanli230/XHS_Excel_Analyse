from io import BytesIO

import pytest
from openpyxl import Workbook

from ui.adapters.run_upload_store import RunUploadStore, UploadValidationError
from ui.view_models.workflow import UploadInput


def workbook(sheet_name="Sheet"):
    """创建没有外部依赖的上传测试工作簿。"""
    book = Workbook()
    book.active.title = sheet_name
    stream = BytesIO()
    book.save(stream)
    return stream.getvalue()


def test_valid_uploads_are_isolated_and_do_not_use_client_filenames(tmp_path):
    """上传文件名不会影响服务端保存路径。"""
    files = RunUploadStore(tmp_path).save("run-1", UploadInput("../../brief.xlsx", workbook(), "../../talent.xlsx", workbook("达人数据")))
    assert files.brief_path.parent == tmp_path / "run-1"
    assert files.talent_path.name == "talents.xlsx"


@pytest.mark.parametrize("name,content", [("bad.csv", b"not-xlsx"), ("empty.xlsx", b""), ("broken.xlsx", b"broken")])
def test_invalid_upload_does_not_leave_run_files(tmp_path, name, content):
    """无效上传不会留下半成品运行目录。"""
    with pytest.raises(UploadValidationError):
        RunUploadStore(tmp_path).save("run-1", UploadInput(name, content, "talents.xlsx", workbook("达人数据")))
    assert not (tmp_path / "run-1").exists()


def test_missing_talent_sheet_removes_both_uploaded_files(tmp_path):
    """缺少达人工作表时清理本次上传。"""
    with pytest.raises(UploadValidationError, match="达人数据"):
        RunUploadStore(tmp_path).save("run-1", UploadInput("brief.xlsx", workbook(), "talents.xlsx", workbook()))
    assert not (tmp_path / "run-1").exists()


def test_oversized_upload_is_rejected_before_writing(tmp_path):
    """超限上传在写盘前被拒绝。"""
    with pytest.raises(UploadValidationError, match="大小限制"):
        RunUploadStore(tmp_path, max_bytes=2).save("run-1", UploadInput("brief.xlsx", b"large", "talents.xlsx", b"large"))
    assert not (tmp_path / "run-1").exists()
