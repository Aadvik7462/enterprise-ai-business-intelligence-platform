
from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from typing import Any

import pandas as pd


BLOCKED_KEYWORDS = {
    "insert",
    "update",
    "delete",
    "drop",
    "alter",
    "create",
    "replace",
    "truncate",
    "attach",
    "detach",
    "pragma",
    "vacuum",
    "reindex",
    "grant",
    "revoke",
}


@dataclass
class SQLAssistantResult:
    success: bool
    answer: str
    sql: str = ""
    columns: list[str] | None = None
    rows: list[dict[str, Any]] | None = None
    chart: dict[str, Any] | None = None
    suggestions: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "answer": self.answer,
            "sql": self.sql,
            "columns": self.columns or [],
            "rows": self.rows or [],
            "chart": self.chart or {},
            "suggestions": self.suggestions or [],
        }


def _normalise(value: Any) -> str:
    return re.sub(
        r"\s+",
        " ",
        str(value or "").strip().lower(),
    )


def _quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _safe_records(
    dataframe: pd.DataFrame,
    limit: int = 500,
) -> list[dict[str, Any]]:
    cleaned = (
        dataframe.head(limit)
        .copy()
        .where(
            dataframe.head(limit).notna(),
            None,
        )
    )

    return cleaned.to_dict(orient="records")


def _find_column(
    dataframe: pd.DataFrame,
    text: str,
    numeric_only: bool = False,
) -> str | None:
    question = _normalise(text)

    columns = (
        dataframe.select_dtypes(
            include="number"
        ).columns
        if numeric_only
        else dataframe.columns
    )

    exact_matches = [
        str(column)
        for column in columns
        if _normalise(column) in question
    ]

    if exact_matches:
        return max(
            exact_matches,
            key=len,
        )

    question_tokens = set(
        re.findall(
            r"[a-z0-9]+",
            question,
        )
    )

    scored: list[tuple[int, int, str]] = []

    for column in columns:
        column_name = str(column)

        column_tokens = set(
            re.findall(
                r"[a-z0-9]+",
                _normalise(column_name),
            )
        )

        score = len(
            question_tokens &
            column_tokens
        )

        if score:
            scored.append(
                (
                    score,
                    len(column_name),
                    column_name,
                )
            )

    if scored:
        scored.sort(
            reverse=True
        )
        return scored[0][2]

    return None


def _find_keyword_column(
    dataframe: pd.DataFrame,
    keywords: tuple[str, ...],
    numeric_only: bool = False,
) -> str | None:
    columns = (
        dataframe.select_dtypes(
            include="number"
        ).columns
        if numeric_only
        else dataframe.columns
    )

    for keyword in keywords:
        for column in columns:
            if keyword in _normalise(column):
                return str(column)

    return None


def _numeric_columns(
    dataframe: pd.DataFrame,
) -> list[str]:
    return (
        dataframe.select_dtypes(
            include="number"
        )
        .columns
        .astype(str)
        .tolist()
    )


def _categorical_columns(
    dataframe: pd.DataFrame,
) -> list[str]:
    return (
        dataframe.select_dtypes(
            exclude="number"
        )
        .columns
        .astype(str)
        .tolist()
    )


def _detect_date_column(
    dataframe: pd.DataFrame,
) -> str | None:
    for column in dataframe.columns:
        column_name = str(column)

        if any(
            token in _normalise(column_name)
            for token in (
                "date",
                "month",
                "year",
                "time",
            )
        ):
            parsed = pd.to_datetime(
                dataframe[column],
                errors="coerce",
            )

            if parsed.notna().sum() >= max(
                3,
                int(len(dataframe) * 0.25),
            ):
                return column_name

    return None


def validate_select_sql(sql: str) -> tuple[bool, str]:
    cleaned = _normalise(sql)

    if not cleaned:
        return False, "SQL query is empty."

    if not (
        cleaned.startswith("select ")
        or cleaned.startswith("with ")
    ):
        return (
            False,
            "Only SELECT and WITH queries are allowed.",
        )

    statements = [
        statement.strip()
        for statement in sql.split(";")
        if statement.strip()
    ]

    if len(statements) > 1:
        return (
            False,
            "Only one SQL statement can be executed at a time.",
        )

    tokens = set(
        re.findall(
            r"\b[a-z_]+\b",
            cleaned,
        )
    )

    blocked = sorted(
        tokens &
        BLOCKED_KEYWORDS
    )

    if blocked:
        return (
            False,
            "Blocked SQL keyword detected: "
            + ", ".join(blocked),
        )

    return True, ""


def generate_sql_from_question(
    dataframe: pd.DataFrame,
    question: str,
    table_name: str = "dataset",
) -> tuple[str, str]:
    q = _normalise(question)

    metric = _find_column(
        dataframe,
        question,
        numeric_only=True,
    )

    group = None

    by_match = re.search(
        r"\bby\s+(.+?)(?:\s+limit\s+\d+|$)",
        q,
    )

    if by_match:
        group = _find_column(
            dataframe,
            by_match.group(1),
        )

    if not metric:
        metric = _find_keyword_column(
            dataframe,
            (
                "sales",
                "revenue",
                "profit",
                "amount",
                "quantity",
                "cost",
            ),
            numeric_only=True,
        )

    quoted_table = _quote_identifier(
        table_name
    )

    if any(
        phrase in q
        for phrase in (
            "show all columns",
            "list columns",
            "column names",
        )
    ):
        return (
            f"SELECT * FROM {quoted_table} LIMIT 10",
            "Showing a sample with all columns.",
        )

    if any(
        phrase in q
        for phrase in (
            "count rows",
            "row count",
            "total rows",
            "number of rows",
        )
    ):
        return (
            f"SELECT COUNT(*) AS total_rows FROM {quoted_table}",
            "Counting all rows in the dataset.",
        )

    top_match = re.search(
        r"\btop\s+(\d+)",
        q,
    )

    bottom_match = re.search(
        r"\bbottom\s+(\d+)",
        q,
    )

    if (
        top_match
        or bottom_match
        or "highest" in q
        or "lowest" in q
    ):
        if not metric:
            raise ValueError(
                "A numeric column is required for ranking."
            )

        limit = int(
            (
                top_match
                or bottom_match
            ).group(1)
        ) if (
            top_match
            or bottom_match
        ) else 10

        direction = (
            "ASC"
            if bottom_match or "lowest" in q
            else "DESC"
        )

        quoted_metric = _quote_identifier(
            metric
        )

        return (
            f"SELECT * FROM {quoted_table} "
            f"WHERE {quoted_metric} IS NOT NULL "
            f"ORDER BY {quoted_metric} {direction} "
            f"LIMIT {max(1, min(limit, 100))}",
            (
                f"Ranking rows by {metric} "
                f"in {direction} order."
            ),
        )

    aggregation = None
    aggregation_label = None

    if any(
        token in q
        for token in (
            "average",
            "mean",
        )
    ):
        aggregation = "AVG"
        aggregation_label = "average"
    elif any(
        token in q
        for token in (
            "count",
            "number of",
        )
    ):
        aggregation = "COUNT"
        aggregation_label = "count"
    elif any(
        token in q
        for token in (
            "minimum",
            "min ",
            "lowest",
        )
    ):
        aggregation = "MIN"
        aggregation_label = "minimum"
    elif any(
        token in q
        for token in (
            "maximum",
            "max ",
            "highest",
        )
    ):
        aggregation = "MAX"
        aggregation_label = "maximum"
    else:
        aggregation = "SUM"
        aggregation_label = "total"

    if group and metric:
        quoted_group = _quote_identifier(
            group
        )

        quoted_metric = _quote_identifier(
            metric
        )

        alias = (
            f"{aggregation_label}_"
            + re.sub(
                r"[^a-z0-9]+",
                "_",
                _normalise(metric),
            ).strip("_")
        )

        sql = (
            f"SELECT {quoted_group} AS category, "
            f"{aggregation}({quoted_metric}) AS {_quote_identifier(alias)} "
            f"FROM {quoted_table} "
            f"WHERE {quoted_group} IS NOT NULL "
            f"GROUP BY {quoted_group} "
            f"ORDER BY {_quote_identifier(alias)} DESC "
            f"LIMIT 25"
        )

        return (
            sql,
            (
                f"Calculating {aggregation_label} "
                f"{metric} by {group}."
            ),
        )

    date_column = _detect_date_column(
        dataframe
    )

    if (
        date_column
        and metric
        and any(
            phrase in q
            for phrase in (
                "monthly trend",
                "month wise",
                "by month",
                "monthly sales",
                "monthly profit",
            )
        )
    ):
        quoted_date = _quote_identifier(
            date_column
        )

        quoted_metric = _quote_identifier(
            metric
        )

        return (
            f"SELECT strftime('%Y-%m', {quoted_date}) AS month, "
            f"SUM({quoted_metric}) AS total_value "
            f"FROM {quoted_table} "
            f"WHERE {quoted_date} IS NOT NULL "
            f"GROUP BY month "
            f"ORDER BY month",
            (
                f"Calculating monthly trend for {metric}."
            ),
        )

    if metric:
        quoted_metric = _quote_identifier(
            metric
        )

        alias = (
            f"{aggregation_label}_"
            + re.sub(
                r"[^a-z0-9]+",
                "_",
                _normalise(metric),
            ).strip("_")
        )

        return (
            f"SELECT {aggregation}({quoted_metric}) "
            f"AS {_quote_identifier(alias)} "
            f"FROM {quoted_table}",
            (
                f"Calculating {aggregation_label} "
                f"for {metric}."
            ),
        )

    categorical = _categorical_columns(
        dataframe
    )

    if categorical:
        selected = categorical[0]
        quoted_selected = _quote_identifier(
            selected
        )

        return (
            f"SELECT {quoted_selected}, COUNT(*) AS count "
            f"FROM {quoted_table} "
            f"GROUP BY {quoted_selected} "
            f"ORDER BY count DESC "
            f"LIMIT 25",
            (
                f"Showing row distribution by {selected}."
            ),
        )

    return (
        f"SELECT * FROM {quoted_table} LIMIT 10",
        "Showing a 10-row sample.",
    )


def _prepare_sqlite_dataframe(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    prepared = dataframe.copy()

    for column in prepared.columns:
        if pd.api.types.is_datetime64_any_dtype(
            prepared[column]
        ):
            prepared[column] = prepared[column].dt.strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            continue

        column_name = _normalise(column)

        if any(
            token in column_name
            for token in (
                "date",
                "month",
                "year",
                "time",
            )
        ):
            parsed = pd.to_datetime(
                prepared[column],
                errors="coerce",
            )

            if parsed.notna().sum() >= max(
                3,
                int(len(prepared) * 0.25),
            ):
                prepared[column] = parsed.dt.strftime(
                    "%Y-%m-%d %H:%M:%S"
                )

    return prepared


def execute_safe_sql(
    dataframe: pd.DataFrame,
    sql: str,
    table_name: str = "dataset",
) -> pd.DataFrame:
    valid, message = validate_select_sql(
        sql
    )

    if not valid:
        raise ValueError(
            message
        )

    connection = sqlite3.connect(
        ":memory:"
    )

    try:
        prepared = _prepare_sqlite_dataframe(
            dataframe
        )

        prepared.to_sql(
            table_name,
            connection,
            index=False,
            if_exists="replace",
        )

        cursor = connection.execute(
            sql
        )

        columns = [
            description[0]
            for description in cursor.description
        ]

        rows = cursor.fetchmany(
            500
        )

        return pd.DataFrame(
            rows,
            columns=columns,
        )

    finally:
        connection.close()


def _build_chart(
    result: pd.DataFrame,
) -> dict[str, Any]:
    if result.empty:
        return {}

    columns = result.columns.astype(
        str
    ).tolist()

    if len(columns) < 2:
        return {}

    first = columns[0]
    second = columns[1]

    if not pd.api.types.is_numeric_dtype(
        result[second]
    ):
        return {}

    x_values = result[first].astype(
        str
    ).tolist()

    chart_type = "bar"

    if any(
        token in _normalise(first)
        for token in (
            "month",
            "date",
            "year",
            "time",
        )
    ):
        chart_type = "line"

    if (
        pd.api.types.is_numeric_dtype(
            result[first]
        )
        and pd.api.types.is_numeric_dtype(
            result[second]
        )
    ):
        chart_type = "scatter"

    return {
        "type": chart_type,
        "x": first,
        "y": second,
        "title": (
            f"{second} by {first}"
        ),
        "records": _safe_records(
            result,
            100,
        ),
    }


def ask_sql_assistant(
    dataframe: pd.DataFrame,
    question: str,
    table_name: str = "dataset",
) -> dict[str, Any]:
    if dataframe.empty:
        return SQLAssistantResult(
            success=False,
            answer="The uploaded dataset is empty.",
        ).to_dict()

    try:
        sql, explanation = generate_sql_from_question(
            dataframe,
            question,
            table_name=table_name,
        )

        result = execute_safe_sql(
            dataframe,
            sql,
            table_name=table_name,
        )

        return SQLAssistantResult(
            success=True,
            answer=(
                f"{explanation} "
                f"The query returned {len(result):,} rows."
            ),
            sql=sql,
            columns=result.columns.astype(
                str
            ).tolist(),
            rows=_safe_records(
                result,
                500,
            ),
            chart=_build_chart(
                result
            ),
            suggestions=[
                "Show total sales by region",
                "Top 10 rows by profit",
                "Average profit by category",
                "Show monthly sales trend",
            ],
        ).to_dict()

    except Exception as error:
        return SQLAssistantResult(
            success=False,
            answer=str(error),
        ).to_dict()


def run_manual_sql(
    dataframe: pd.DataFrame,
    sql: str,
    table_name: str = "dataset",
) -> dict[str, Any]:
    try:
        result = execute_safe_sql(
            dataframe,
            sql,
            table_name=table_name,
        )

        return SQLAssistantResult(
            success=True,
            answer=(
                f"Query executed successfully. "
                f"{len(result):,} rows were returned."
            ),
            sql=sql,
            columns=result.columns.astype(
                str
            ).tolist(),
            rows=_safe_records(
                result,
                500,
            ),
            chart=_build_chart(
                result
            ),
        ).to_dict()

    except Exception as error:
        return SQLAssistantResult(
            success=False,
            answer=str(error),
            sql=sql,
        ).to_dict()
