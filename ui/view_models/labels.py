BAND_LABELS = {"clear_yes": "明确推荐", "clear_no": "明确不推荐", "mid": "中间档"}
STANCE_LABELS = {"recommend": "推荐", "reject": "不推荐", "not_recommend": "不推荐"}
AUDIT_LABELS = {"passed": "通过", "skipped_clear_band": "明确档", "needs_resolution": "待处理",
                "execution_error": "审核异常", "flagged_release": "带标记放行"}
RISK_LABELS = {"data_incomplete": "数据不全", "policy_changed_after_approval": "策略已调整",
               "manual_review_required": "需人工核对", "unverified_checks": "存在待核实项",
               "audit_unverified_checks": "存在待核实项", "missing_data_fields": "缺少指标",
               "missing_fields": "缺少指标", "flagged_release": "带标记放行"}
KPI_LABELS = {"exposure": "曝光量", "interactions": "互动量", "cpe": "互动成本", "brand_search_lift": "品牌搜索增长"}
KPI_STATUS_LABELS = {"proxy_met": "估算达标", "proxy_unmet": "未达目标", "not_evaluable": "待核实", "not_set": "未设置"}
PORTFOLIO_WARNINGS = {
    "Search node limit reached": "方案搜索已达上限，需复核投放组合",
    "No priced post was selected": "预算内暂无可执行投放项",
    "Unpriced conditional candidates": "部分达人报价待补充",
    "No supported KPI targets": "效果目标待补充",
    "Out-of-corridor proposed pricing": "报价超出参考区间，需人工确认",
    "A non-recommended record": "已排除不推荐达人",
    "A held_for_review record": "待处理达人未纳入投放",
}


def business_warning(value: str) -> str:
    """把已知运行风险转换为简短业务状态。"""
    if "一个或多个客户KPI未达标" in value:
        return "部分效果目标未达标或待核实"
    for prefix, label in PORTFOLIO_WARNINGS.items():
        if value.startswith(prefix):
            return label
    if "price_" in value and "is unavailable" in value:
        return "部分合作形式报价待补充"
    if "invalid upstream score" in value:
        return "部分达人评分缺失"
    if "explicit zero post cap" in value:
        return "已排除投放数量为零的达人"
    return value


def format_money(value: float | None) -> str:
    """格式化金额并明确区分缺失值。"""
    return "—" if value is None else f"¥{value:,.2f}"
