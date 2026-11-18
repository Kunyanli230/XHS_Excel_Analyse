from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

from ui.models.run import RunContext, RunFiles


def sample_state():
    """提供与后端交接字段一致的合成审核数据。"""
    talent = {"xhs_id": "10001", "nickname": "桃桃吃梨", "price_image": 9500}
    candidate = {
        **talent, "talent": talent, "band": "clear_yes", "score": .85,
        "stance": "recommend", "tag": "粉丝匹配", "sentence": "女性受众占比较高，适合护肤内容。",
        "audit_status": "skipped_clear_band", "release_status": "eligible", "data_incomplete": False,
    }
    line = {
        "xhs_id": "10001", "nickname": "桃桃吃梨", "format": "image", "quantity": 1,
        "unit_price_low": 7600, "unit_price_suggested": 9500, "unit_price_high": 11400,
        "line_cost_suggested": 9500, "risk_flags": {"data_incomplete": False},
    }
    return {
        "workflow_status": "advice_ready", "review_status": "pending",
        "brief": {"brand": "屿光", "total_budget": 350000},
        "audit_summary": {"entered_count": 3, "usable_recommendations": 1, "rejected_count": 1, "held_count": 1},
        "audited_talents": [candidate, {
            **candidate, "xhs_id": "10002", "nickname": "慢生活收藏家", "band": "clear_no",
            "stance": "reject", "score": .22, "tag": "内容不合适", "sentence": "内容方向不匹配。",
        }, {
            **candidate, "xhs_id": "10003", "nickname": "山茶开在冬天", "band": "mid", "score": .52,
            "stance": "recommend", "audit_status": "needs_resolution", "release_status": "held_for_review",
            "data_incomplete": True,
        }],
        "audit_unverified_checks": [{"description": "核对近期品牌合作记录", "status": "unverified"}],
        "portfolio_plan": {
            "revision": 1, "status": "best_effort", "lines": [line],
            "budget": {"limit": 350000, "total_suggested": 9500, "total_upper": 11400},
            "kpi_checks": {"exposure": {"target": 25000000, "estimate": 300000,
                                         "status": "proxy_unmet", "gap": 24700000}},
            "conditional_candidates": [], "warnings": [],
        },
        "recommendations": [{
            "xhs_id": "10001", "nickname": "桃桃吃梨", "tag": "粉丝匹配",
            "sentence": candidate["sentence"], "format": "image_text", "quantity": 1,
            "unit_price": 9500, "total_price": 9500, "angle": "场景种草", "sub_angle": "换季护肤",
            "details": "通过换季护肤流程展示精华质地与使用感。", "warnings": ["核对近期品牌合作记录"],
            "remarks": [], "advice_status": "generated", "advice_error": None,
        }],
    }


def make_context(root: Path, state=None, **changes):
    """创建隔离的运行上下文。"""
    root.mkdir(parents=True, exist_ok=True)
    context = RunContext("run-a", "thread-a", None, SimpleNamespace(portfolio=None, advice=None), {},
                         RunFiles(root, root / "brief.xlsx", root / "talents.xlsx"), deepcopy(state or sample_state()))
    for key, value in changes.items():
        setattr(context, key, value)
    return context
