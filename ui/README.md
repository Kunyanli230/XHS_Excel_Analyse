# Streamlit 前端

从项目根目录运行：

```powershell
.venv\Scripts\python.exe -m streamlit run ui/app.py --theme.base dark
```

前端使用现有五模块 LLM 配置。上传需求单和达人表后，依次完成需求补充、策略审核、达人结果查看、方案复核、最终审核及 Excel 导出。

## 模块边界

| 目录 | 职责 |
| --- | --- |
| `components/` | 无后端调用的展示组件及审核表单；组合组件转交用户操作 |
| `pages/` | 按会话阶段编排页面 |
| `view_models/` | 将后端状态投影为只读视图与中文业务标签 |
| `services/` | 串行处理用户操作、会话忙碌状态及恢复 |
| `adapters/` | LangGraph 恢复、后续业务节点、上传和文件下载边界 |
| `models/` | 运行上下文、文件元数据与操作冲突 |
| `styles/` | 沿用现有深色与紫色强调色 |
| `tests/` | 离线单元、真实后端集成、Streamlit AppTest 与浏览器验收入口 |

## 后端接线

`LangGraphWorkflowAdapter` 使用真实 `build_graph(..., enable_portfolio=False)` 完成需求、筛选与审校，保留 LangGraph 暂停及恢复语义。

`PostPolicyWorkflowAdapter` 直接调用现有 `make_portfolio_handoff_node`、`make_advice_node` 和 `export_recommendations`。这样，第 9–10 步和最终导出都使用本会话运行目录，不依赖后端当前没有提供的 `advice_output_dir` 参数或 CLI 拆分接口。

最终审核按任务 ID 和报价版本验证，拒绝重复及过期操作。重定价归档上一版建议并清除旧审批和下载路径；重试从失败阶段继续。正式导出失败或文件丢失时保留人工审批，仅重新导出。无可执行项的有效空方案通过调整意见恢复，不提供原样重试。

下载仅读取当前状态引用、且位于本任务目录内的工作簿。正式表格要求 `review_status=approved` 且 `workflow_status=export_complete`。页面只接收文件内容和下载名称，不展示本地路径。

## 测试

```powershell
.venv\Scripts\python.exe -m pytest ui/tests -q
.venv\Scripts\python.exe -m pytest tests ui/tests -q
```

测试使用合成记录或现有模拟 Excel 与注入的离线模型，不请求真实模型服务。`test_real_workflow.py` 通过真实 LangGraph、筛选、审核、报价、建议和 Excel 导出节点验证全链路。

浏览器离线验收入口（仅测试用途，不进入生产导航）：

```powershell
.venv\Scripts\python.exe -m streamlit run ui/tests/preview_app.py --server.port 8502 --theme.base dark
```

查询参数支持 `scenario=upload`、`review`、`no_candidates`、`failed_advice`、`empty_results`。测试运行文件位于 `ui/tests/.artifacts/`，不纳入版本控制。
