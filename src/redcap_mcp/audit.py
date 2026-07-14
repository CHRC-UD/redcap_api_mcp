from __future__ import annotations

import json
import logging
from datetime import datetime, timezone


def audit(tool: str, profile: str, rows: int, identifiers: bool, truncated: bool) -> None:
    logging.getLogger("redcap_mcp.audit").info(
        json.dumps(
            {
                "time": datetime.now(timezone.utc).isoformat(),
                "tool": tool,
                "profile": profile,
                "rows": rows,
                "identifiers": identifiers,
                "truncated": truncated,
            }
        )
    )
