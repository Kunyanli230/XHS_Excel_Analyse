from __future__ import annotations

from collections.abc import MutableMapping
from typing import Any


class StreamlitRunStore:
    RUN_KEY = "_xhs_workflow_run"
    ERROR_KEY = "_xhs_workflow_error"

    def __init__(self, state: MutableMapping[str, Any]) -> None:
        self.state = state

    def get(self) -> Any:
        return self.state.get(self.RUN_KEY)

    def save(self, context: Any) -> None:
        self.state[self.RUN_KEY] = context

    def clear(self) -> Any:
        return self.state.pop(self.RUN_KEY, None)

    def get_error(self) -> str | None:
        value = self.state.get(self.ERROR_KEY)
        return str(value) if value else None

    def set_error(self, message: str | None) -> None:
        if message:
            self.state[self.ERROR_KEY] = message
        else:
            self.state.pop(self.ERROR_KEY, None)
