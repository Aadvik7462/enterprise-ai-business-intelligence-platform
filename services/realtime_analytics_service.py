
from __future__ import annotations

from typing import Any

import pandas as pd

from services.enterprise_ai_service import (
    dataset_profile,
    generate_insights,
    generate_kpis,
)


def realtime_snapshot(
    dataframe: pd.DataFrame,
) -> dict[str, Any]:
    return {
        "profile": dataset_profile(
            dataframe
        ),
        "kpis": generate_kpis(
            dataframe
        ),
        "alerts": [
            insight
            for insight in generate_insights(
                dataframe
            )
            if insight.get("severity") in {
                "warning",
                "info",
            }
        ],
    }
