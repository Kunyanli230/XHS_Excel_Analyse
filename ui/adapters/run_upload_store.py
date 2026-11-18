from __future__ import annotations

import shutil
from pathlib import Path

from openpyxl import load_workbook

from ui.models.run import RunFiles
from ui.view_models.workflow import UploadInput


class UploadValidationError(ValueError):
    pass


class RunUploadStore:
    def __init__(self, base_dir: str | Path, *, max_bytes: int = 20 * 1024 * 1024) -> None:
        self.base_dir = Path(base_dir)
        self.max_bytes = max_bytes

    def save(self, run_id: str, uploaded: UploadInput) -> RunFiles:
        self._validate_upload(uploaded.brief_name, uploaded.brief_bytes, "需求单")
        self._validate_upload(uploaded.talent_name, uploaded.talent_bytes, "达人数据")
        run_dir = self.base_dir / run_id
        if run_dir.exists():
            raise UploadValidationError("运行目录已存在")
        try:
            run_dir.mkdir(parents=True)
            brief_path = run_dir / "brief.xlsx"
            talent_path = run_dir / "talents.xlsx"
            brief_path.write_bytes(uploaded.brief_bytes)
            talent_path.write_bytes(uploaded.talent_bytes)
            self._validate_workbook(brief_path, "需求单")
            self._validate_workbook(talent_path, "达人数据", required_sheet="达人数据")
        except Exception:
            shutil.rmtree(run_dir, ignore_errors=True)
            raise
        return RunFiles(run_dir, brief_path, talent_path)

    def remove(self, files: RunFiles) -> None:
        shutil.rmtree(files.run_dir, ignore_errors=True)

    def _validate_upload(self, name: str, content: bytes, label: str) -> None:
        if Path(name).suffix.lower() != ".xlsx":
            raise UploadValidationError(f"{label}必须为 .xlsx 文件")
        if not content:
            raise UploadValidationError(f"{label}不能为空")
        if len(content) > self.max_bytes:
            raise UploadValidationError(f"{label}超过文件大小限制")

    def _validate_workbook(self, path: Path, label: str, required_sheet: str | None = None) -> None:
        try:
            workbook = load_workbook(path, read_only=True, data_only=True)
        except Exception as exc:
            raise UploadValidationError(f"{label}文件无法读取") from exc
        try:
            if required_sheet and required_sheet not in workbook.sheetnames:
                raise UploadValidationError(f"{label}缺少工作表：{required_sheet}")
        finally:
            workbook.close()
