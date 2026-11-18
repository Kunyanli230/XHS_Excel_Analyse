from __future__ import annotations

import streamlit as st

from ui.view_models.workflow import UploadInput, WorkflowView


def render_upload_form(view: WorkflowView) -> UploadInput | None:
    brief = st.file_uploader(
        "投放需求单",
        type=["xlsx"],
        key="brief_upload",
        max_upload_size=20,
        disabled=view.busy,
    )
    talents = st.file_uploader(
        "达人数据",
        type=["xlsx"],
        key="talent_upload",
        max_upload_size=20,
        disabled=view.busy,
    )
    submitted = st.button(
        "开始分析",
        key="start_run",
        type="primary",
        disabled=view.busy or brief is None or talents is None,
        width="stretch",
    )
    if not submitted or brief is None or talents is None:
        return None
    return UploadInput(
        brief_name=brief.name,
        brief_bytes=brief.getvalue(),
        talent_name=talents.name,
        talent_bytes=talents.getvalue(),
    )
