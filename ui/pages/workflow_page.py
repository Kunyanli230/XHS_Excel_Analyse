from __future__ import annotations

import streamlit as st

from ui.components.advice_review import render_advice_review
from ui.components.client_confirmation import render_client_confirmation
from ui.components.policy_review import render_policy_review
from ui.components.recovery import render_recovery
from ui.components.run_status import render_run_status
from ui.components.upload_form import render_upload_form
from ui.view_models.workflow import RunPhase


def render(service) -> None:
    st.title("达人投放分析")
    view = service.current()
    render_run_status(view)

    if view.phase in {RunPhase.EMPTY, RunPhase.FAILED}:
        uploaded = render_upload_form(view)
        if uploaded is not None:
            with st.spinner("正在分析需求"):
                service.start(uploaded)
            st.rerun()
        return

    if view.phase is RunPhase.CLIENT_CONFIRMATION and view.client_confirmation is not None:
        answer = render_client_confirmation(view.client_confirmation, disabled=view.busy)
        if answer is not None:
            with st.spinner("正在更新需求"):
                service.answer_client(answer)
            st.rerun()

    if view.phase is RunPhase.POLICY_REVIEW and view.policy_review is not None:
        decision = render_policy_review(view.policy_review, disabled=view.busy)
        if decision is not None:
            with st.spinner("正在筛选与生成方案"):
                service.decide_policy(decision)
            st.rerun()

    if view.advice_review is not None:
        render_advice_review(view, service)

    if view.phase is RunPhase.ACTION_REQUIRED:
        render_recovery(view, service)

    if view.phase is not RunPhase.RUNNING:
        st.space("medium")
        if st.button("开始新任务", key="reset_run"):
            service.reset()
            st.rerun()
