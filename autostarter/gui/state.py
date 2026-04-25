from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, Optional
@dataclass(slots=True)
class AppState:
    user: Optional[str] = None
    selected_account_id: Optional[str] = None
    flags: Dict[str, bool] = field(default_factory=dict)
    data: Dict[str, Any] = field(default_factory=dict)
