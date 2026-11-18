from __future__ import annotations

import streamlit as st

from ui.view_models.workflow import ClientAnswer, ClientConfirmationView


def render_client_confirmation(
    confirmation: ClientConfirmationView,
    *,
    disabled: bool,
) -> ClientAnswer | None:
    st.subheader("补充需求")
    if confirmation.message:
        st.caption(confirmation.message)
    for question in confirmation.questions:
        st.markdown(question)
    with st.form("client_confirmation_form", border=False):
        answers = st.text_area(
            "客户答复",
            key="client_answers",
            disabled=disabled,
            label_visibility="collapsed",
            placeholder="填写补充信息",
        )
        submitted = st.form_submit_button(
            "提交并继续",
            key="submit_client_answers",
            type="primary",
            disabled=disabled,
            width="stretch",
        )
    if not submitted or not answers.strip():
        return None
    return ClientAnswer(answers.strip(), confirmation.interrupt_id)
