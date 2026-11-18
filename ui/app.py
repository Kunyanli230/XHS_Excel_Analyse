from __future__ import annotations

from pathlib import Path

import streamlit as st

from ui.adapters.langgraph_workflow import LangGraphWorkflowAdapter
from ui.adapters.run_upload_store import RunUploadStore
from ui.adapters.streamlit_run_store import StreamlitRunStore
from ui.pages.workflow_page import render
from ui.services.workflow_service import WorkflowService
from ui.styles.theme import apply_theme


ROOT = Path(__file__).resolve().parents[1]
RUN_ROOT = ROOT / "tmp" / "ui-runs"


def build_service() -> WorkflowService:
    """为当前浏览器会话装配工作流服务。"""
    return WorkflowService(
        RunUploadStore(RUN_ROOT),
        LangGraphWorkflowAdapter(),
        StreamlitRunStore(st.session_state),
    )


def render_app() -> None:
    """渲染唯一的工作流入口。"""
    apply_theme()
    render(build_service())


st.set_page_config(
    page_title="达人投放分析",
    page_icon="●",
    layout="wide",
    initial_sidebar_state="collapsed",
)
st.navigation([st.Page(render_app, title="达人投放分析", default=True)], position="hidden").run()
