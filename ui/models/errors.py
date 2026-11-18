class WorkflowConflictError(ValueError):
    """拒绝失效、重复或不属于当前任务的操作。"""
