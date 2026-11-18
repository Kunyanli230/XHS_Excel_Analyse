import streamlit as st


def render_download(service, kind: str, scope: str) -> None:
    """提供已验证归属与审核状态的工作簿下载。"""
    try:
        artifact = service.download(kind)
    except ValueError as exc:
        st.warning(str(exc))
        return
    st.download_button("下载交付表" if kind == "final" else "下载预览表", data=artifact.content,
                       file_name=artifact.filename, mime=artifact.mime,
                       key=f"download_{kind}_{scope}", on_click="ignore", width="stretch",
                       type="primary" if kind == "final" else "secondary")
