import streamlit as st

from ui.view_models.labels import AUDIT_LABELS
from ui.view_models.post_policy import AdviceReviewView


def render_candidates(review: AdviceReviewView, scope: str) -> None:
    """展示审核汇总与可检索的达人结果。"""
    summary = review.audit
    for column, label, value in zip(st.columns(4), ("进入流程", "推荐", "不推荐", "待处理"),
                                    (summary.input_count, summary.recommended_count, summary.rejected_count, summary.pending_count)):
        column.metric(label, value)
    st.space("small")
    filter_column, search_column = st.columns([3, 2])
    with filter_column:
        selected = st.segmented_control("结论", ["全部", "推荐", "不推荐", "待处理"], default="全部",
                                        key=f"candidate_filter_{scope}", label_visibility="collapsed")
    with search_column:
        query = st.text_input("搜索达人", placeholder="搜索达人", key=f"candidate_search_{scope}",
                              label_visibility="collapsed").strip().casefold()
    rows = [item for item in review.candidates if (not selected or selected == "全部" or item.stance_label == selected)
            and (not query or query in item.nickname.casefold() or query in item.xhs_id.casefold())]
    if not rows:
        st.info("暂无匹配达人")
        return
    st.dataframe([
        {"达人": item.nickname or item.xhs_id, "档位": item.band_label, "评分": item.score,
         "结论": item.stance_label, "原因标签": item.tag, "推荐理由": item.sentence,
         "审核": AUDIT_LABELS.get(item.audit_status, "待审核"),
         "风险": "数据不全" if item.data_incomplete else ""}
        for item in rows
    ], hide_index=True, width="stretch", row_height=46,
        column_config={"评分": st.column_config.NumberColumn(format="%.2f"),
                       "推荐理由": st.column_config.TextColumn(width="large")})
