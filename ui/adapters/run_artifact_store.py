from pathlib import Path

from ui.models.artifact import DownloadArtifact
from ui.models.run import RunContext


class RunArtifactStore:
    """只读取当前任务状态引用的运行目录内文件。"""

    def read(self, context: RunContext, kind: str) -> DownloadArtifact:
        """验证审核状态与文件归属后返回下载内容。"""
        if kind not in {"preview", "final"}:
            raise ValueError("不支持的文件类型")
        state = context.latest_state
        if kind == "final" and (state.get("review_status") != "approved" or state.get("workflow_status") != "export_complete"):
            raise ValueError("请先完成最终审核")
        raw = state.get("final_export_path" if kind == "final" else "advice_preview_path")
        if not raw:
            raise ValueError("文件不可用，请重新生成")
        root = context.files.run_dir.resolve()
        path = Path(raw).resolve()
        if not path.is_relative_to(root) or path.suffix.lower() != ".xlsx":
            raise ValueError("文件不属于当前任务")
        try:
            content = path.read_bytes()
        except OSError as exc:
            raise ValueError("文件不可用，请重新生成") from exc
        revision = (state.get("portfolio_plan") or {}).get("revision", 1)
        name = "达人推荐表" if kind == "final" else "达人推荐表_预览"
        return DownloadArtifact(f"{name}_v{revision}.xlsx", content)
