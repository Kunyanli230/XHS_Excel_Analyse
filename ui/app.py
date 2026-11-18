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
    return WorkflowService(
        RunUploadStore(RUN_ROOT),
        LangGraphWorkflowAdapter(),
        StreamlitRunStore(st.session_state),
    )


st.set_page_config(
    page_title="达人投放分析",
    page_icon="●",
    layout="wide",
    initial_sidebar_state="collapsed",
)
apply_theme()
render(build_service())
