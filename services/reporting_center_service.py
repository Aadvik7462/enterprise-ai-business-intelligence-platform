from __future__ import annotations

from html import escape
from typing import Any
import pandas as pd


def build_reporting_summary(df: pd.DataFrame, filename: str) -> dict[str, Any]:
    numeric = [str(c) for c in df.select_dtypes(include="number").columns]
    summaries = []
    for column in numeric[:10]:
        s = pd.to_numeric(df[column], errors="coerce").dropna()
        if s.empty:
            continue
        summaries.append({
            "column": column,
            "total": round(float(s.sum()), 2),
            "average": round(float(s.mean()), 2),
            "minimum": round(float(s.min()), 2),
            "maximum": round(float(s.max()), 2),
        })
    return {
        "success": True,
        "filename": filename,
        "total_rows": len(df),
        "total_columns": len(df.columns),
        "missing_values": int(df.isna().sum().sum()),
        "duplicate_rows": int(df.duplicated().sum()),
        "numeric_summaries": summaries,
    }


def render_report_html(report: dict[str, Any]) -> str:
    rows = "".join(
        f"<tr><td>{escape(str(i['column']))}</td><td>{i['total']}</td><td>{i['average']}</td><td>{i['minimum']}</td><td>{i['maximum']}</td></tr>"
        for i in report.get("numeric_summaries", [])
    )
    return f"""<!DOCTYPE html><html><head><meta charset='UTF-8'><title>Enterprise Report</title><style>body{{font-family:Arial;margin:40px;color:#0f172a}}.grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:15px;margin:20px 0}}.card{{border:1px solid #e2e8f0;padding:18px;border-radius:12px}}table{{width:100%;border-collapse:collapse}}th,td{{padding:10px;border-bottom:1px solid #e2e8f0;text-align:left}}</style></head><body><h1>Enterprise BI Report</h1><p><strong>Dataset:</strong> {escape(report.get('filename',''))}</p><div class='grid'><div class='card'><strong>Total Rows</strong><p>{report.get('total_rows',0)}</p></div><div class='card'><strong>Total Columns</strong><p>{report.get('total_columns',0)}</p></div><div class='card'><strong>Missing Values</strong><p>{report.get('missing_values',0)}</p></div><div class='card'><strong>Duplicate Rows</strong><p>{report.get('duplicate_rows',0)}</p></div></div><h2>Numeric KPI Summary</h2><table><thead><tr><th>Column</th><th>Total</th><th>Average</th><th>Minimum</th><th>Maximum</th></tr></thead><tbody>{rows}</tbody></table></body></html>"""
