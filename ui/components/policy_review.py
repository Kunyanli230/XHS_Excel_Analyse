from __future__ import annotations

import streamlit as st

from ui.view_models.workflow import PolicyCriterionView, PolicyDecision, PolicyReviewView


def render_policy_review(policy: PolicyReviewView, *, disabled: bool) -> PolicyDecision | None:
    st.subheader(policy.name)
    if policy.rationale:
        st.caption(policy.rationale)
    if policy.hard_criteria:
        st.markdown("**排除条件**")
        st.dataframe(
            [_criterion_row(item, hard=True) for item in policy.hard_criteria],
            hide_index=True,
            width="stretch",
        )
    if policy.scoring_criteria:
        st.markdown("**评分条件**")
        st.dataframe(
            [_criterion_row(item, hard=False) for item in policy.scoring_criteria],
            hide_index=True,
            width="stretch",
        )
    if policy.manual_checks:
        st.markdown("**人工核对**")
        for item in policy.manual_checks:
            st.write(item)
    with st.form("policy_review_form", border=False):
        feedback = st.text_area(
            "修改意见",
            key="policy_feedback",
            disabled=disabled,
            label_visibility="collapsed",
            placeholder="填写需要调整的条件或权重",
        )
        approve_column, revise_column = st.columns(2)
        with approve_column:
            approved = st.form_submit_button(
                "批准并继续",
                key="approve_policy",
                type="primary",
                disabled=disabled,
                width="stretch",
            )
        with revise_column:
            revised = st.form_submit_button(
                "提交修改",
                key="revise_policy",
                disabled=disabled,
                width="stretch",
            )
    if approved:
        return PolicyDecision("approve", policy.interrupt_id)
    if revised and feedback.strip():
        return PolicyDecision("revise", policy.interrupt_id, feedback.strip())
    return None


def _criterion_row(item: PolicyCriterionView, *, hard: bool) -> dict[str, object]:
    row: dict[str, object] = {
        "指标": item.field,
        "规则": item.operator,
        "取值": "" if item.value is None else item.value,
        "依据": item.reason,
    }
    if not hard:
        row["权重"] = f"{(item.weight or 0) * 100:g}%"
    return row
