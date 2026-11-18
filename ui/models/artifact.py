from dataclasses import dataclass


@dataclass(frozen=True)
class DownloadArtifact:
    """封装可下载文件而不向页面暴露磁盘路径。"""
    filename: str
    content: bytes
    mime: str = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
