from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RunFiles:
    run_dir: Path
    brief_path: Path
    talent_path: Path


@dataclass
class RunContext:
    run_id: str
    thread_id: str
    graph: Any
    clients: Any
    config: dict[str, Any]
    files: RunFiles
    latest_state: dict[str, Any]
    interrupt_type: str | None = None
    interrupt_payload: dict[str, Any] = field(default_factory=dict)
    interrupt_id: str | None = None
    consumed_interrupt_ids: set[str] = field(default_factory=set)
    busy: bool = False
    last_error: str | None = None
