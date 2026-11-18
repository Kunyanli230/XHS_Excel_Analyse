from __future__ import annotations

import streamlit as st

from ui.view_models.workflow import RunPhase, WorkflowView


def render_run_status(view: WorkflowView) -> None:
    """只展示当前操作状态与需要处理的错误。"""
    if view.error and view.phase not in {RunPhase.ACTION_REQUIRED, RunPhase.FAILED}:
        st.error(view.error)
    if view.phase is RunPhase.RUNNING:
        st.info("正在处理")
    elif view.phase is RunPhase.FAILED:
        st.error(view.error or "运行失败")
    elif view.phase is RunPhase.CLIENT_CONFIRMATION:
        st.warning("等待客户确认")
    elif view.phase is RunPhase.UNSUPPORTED_INTERRUPT:
        st.warning(view.message)
    elif view.phase is RunPhase.ACTION_REQUIRED:
        st.warning(view.error or view.message)
    elif view.phase is RunPhase.ADVICE_REVIEW:
        st.caption("等待最终审核")
    elif view.phase is RunPhase.COMPLETED:
        st.success(view.message or "已完成")
