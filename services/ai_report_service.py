import pandas as pd


def normalize_column_name(column):
    return str(column).lower().replace("_", " ").strip()


def find_column(df, keywords):
    for column in df.columns:
        normalized = normalize_column_name(column)

        for keyword in keywords:
            if keyword in normalized:
                return column

    return None


def format_number(value):
    try:
        numeric_value = float(value)

        if numeric_value.is_integer():
            return f"{int(numeric_value):,}"

        return f"{numeric_value:,.2f}"

    except (TypeError, ValueError):
        return str(value)


def detect_dataset_type(df):
    normalized_columns = [
        normalize_column_name(column)
        for column in df.columns
    ]

    joined_columns = " ".join(normalized_columns)

    if any(
        keyword in joined_columns
        for keyword in [
            "sales",
            "revenue",
            "profit",
            "order",
            "customer",
            "product"
        ]
    ):
        return "sales"

    if any(
        keyword in joined_columns
        for keyword in [
            "attrition",
            "employee",
            "job role",
            "department",
            "monthly income",
            "years at company"
        ]
    ):
        return "hr"

    if any(
        keyword in joined_columns
        for keyword in [
            "loan amount",
            "credit history",
            "default",
            "applicant income",
            "loan status",
            "credit score"
        ]
    ):
        return "finance"

    if any(
        keyword in joined_columns
        for keyword in [
            "inventory",
            "supplier",
            "shipping",
            "delivery",
            "stock",
            "warehouse"
        ]
    ):
        return "supply_chain"

    return "generic"


def build_sales_kpis(df):
    kpis = {}

    sales_col = find_column(
        df,
        ["sales", "revenue", "amount", "total"]
    )

    profit_col = find_column(
        df,
        ["profit", "income", "earning", "margin"]
    )

    order_col = find_column(
        df,
        ["order id", "order number", "invoice id", "invoice"]
    )

    customer_col = find_column(
        df,
        ["customer id", "customer name", "customer"]
    )

    quantity_col = find_column(
        df,
        ["quantity", "qty", "units"]
    )

    if sales_col:
        sales_series = pd.to_numeric(
            df[sales_col],
            errors="coerce"
        ).dropna()

        if not sales_series.empty:
            kpis["total_sales"] = float(sales_series.sum())
            kpis["average_sales"] = float(sales_series.mean())

    if profit_col:
        profit_series = pd.to_numeric(
            df[profit_col],
            errors="coerce"
        ).dropna()

        if not profit_series.empty:
            kpis["total_profit"] = float(profit_series.sum())
            kpis["negative_profit_orders"] = int(
                (profit_series < 0).sum()
            )

    if (
        "total_sales" in kpis
        and "total_profit" in kpis
        and kpis["total_sales"] != 0
    ):
        kpis["profit_margin"] = (
            kpis["total_profit"] / kpis["total_sales"]
        ) * 100

    if order_col:
        total_orders = int(
            df[order_col].nunique(dropna=True)
        )

        kpis["total_orders"] = total_orders

        if (
            total_orders > 0
            and "total_sales" in kpis
        ):
            kpis["average_order_value"] = (
                kpis["total_sales"] / total_orders
            )

    if customer_col:
        kpis["total_customers"] = int(
            df[customer_col].nunique(dropna=True)
        )

    if quantity_col:
        quantity_series = pd.to_numeric(
            df[quantity_col],
            errors="coerce"
        ).dropna()

        if not quantity_series.empty:
            kpis["total_quantity"] = float(
                quantity_series.sum()
            )

    return kpis


def get_group_performance(
    df,
    category_column,
    value_column
):
    if not category_column or not value_column:
        return None

    temp = df[
        [category_column, value_column]
    ].copy()

    temp[value_column] = pd.to_numeric(
        temp[value_column],
        errors="coerce"
    )

    temp = temp.dropna()

    if temp.empty:
        return None

    grouped = (
        temp.groupby(category_column)[value_column]
        .sum()
        .sort_values(ascending=False)
    )

    if grouped.empty:
        return None

    return {
        "best_name": str(grouped.index[0]),
        "best_value": float(grouped.iloc[0]),
        "worst_name": str(grouped.index[-1]),
        "worst_value": float(grouped.iloc[-1]),
        "grouped": grouped
    }


def get_top_product(df, product_col, sales_col):
    if not product_col or not sales_col:
        return None

    temp = df[
        [product_col, sales_col]
    ].copy()

    temp[sales_col] = pd.to_numeric(
        temp[sales_col],
        errors="coerce"
    )

    temp = temp.dropna()

    if temp.empty:
        return None

    grouped = (
        temp.groupby(product_col)[sales_col]
        .sum()
        .sort_values(ascending=False)
    )

    if grouped.empty:
        return None

    return {
        "name": str(grouped.index[0]),
        "value": float(grouped.iloc[0])
    }


def get_monthly_performance(df, date_col, value_col):
    if not date_col or not value_col:
        return None

    temp = df[
        [date_col, value_col]
    ].copy()

    temp[date_col] = pd.to_datetime(
        temp[date_col],
        errors="coerce"
    )

    temp[value_col] = pd.to_numeric(
        temp[value_col],
        errors="coerce"
    )

    temp = temp.dropna()

    if temp.empty:
        return None

    temp["Month"] = (
        temp[date_col]
        .dt.to_period("M")
        .astype(str)
    )

    grouped = (
        temp.groupby("Month")[value_col]
        .sum()
        .sort_index()
    )

    if grouped.empty:
        return None

    peak_month = grouped.idxmax()
    weakest_month = grouped.idxmin()

    result = {
        "peak_month": peak_month,
        "peak_value": float(grouped.loc[peak_month]),
        "weakest_month": weakest_month,
        "weakest_value": float(
            grouped.loc[weakest_month]
        ),
        "grouped": grouped
    }

    if len(grouped) >= 2:
        first_value = float(grouped.iloc[0])
        last_value = float(grouped.iloc[-1])

        if first_value != 0:
            result["overall_change_percent"] = (
                (last_value - first_value)
                / abs(first_value)
            ) * 100

    return result


def generate_sales_intelligence(df, stats):
    findings = []
    risks = []
    recommendations = []

    sales_col = find_column(
        df,
        ["sales", "revenue", "amount", "total"]
    )

    profit_col = find_column(
        df,
        ["profit", "income", "earning", "margin"]
    )

    category_col = find_column(
        df,
        ["category"]
    )

    segment_col = find_column(
        df,
        ["segment"]
    )

    region_col = find_column(
        df,
        ["region", "state", "country", "city"]
    )

    product_col = find_column(
        df,
        ["product name", "product"]
    )

    discount_col = find_column(
        df,
        ["discount"]
    )

    date_col = find_column(
        df,
        ["order date", "date"]
    )

    kpis = build_sales_kpis(df)

    if "total_sales" in kpis:
        findings.append(
            f"Total sales are "
            f"{format_number(kpis['total_sales'])}."
        )

    if "total_profit" in kpis:
        findings.append(
            f"Total profit is "
            f"{format_number(kpis['total_profit'])}."
        )

    if "profit_margin" in kpis:
        findings.append(
            f"Overall profit margin is "
            f"{kpis['profit_margin']:.2f}%."
        )

        if kpis["profit_margin"] < 5:
            risks.append(
                "Overall profit margin is very low."
            )

            recommendations.append(
                "Review pricing, discounts, and product-level margins."
            )

        elif kpis["profit_margin"] < 10:
            risks.append(
                "Profit margin is below a healthy target."
            )

            recommendations.append(
                "Improve margin by reducing low-value discounts and costs."
            )

    if "average_order_value" in kpis:
        findings.append(
            f"Average order value is "
            f"{format_number(kpis['average_order_value'])}."
        )

    if "total_orders" in kpis:
        findings.append(
            f"The dataset contains "
            f"{kpis['total_orders']:,} unique orders."
        )

    if "total_customers" in kpis:
        findings.append(
            f"The dataset contains "
            f"{kpis['total_customers']:,} unique customers."
        )

    if "negative_profit_orders" in kpis:
        negative_count = kpis[
            "negative_profit_orders"
        ]

        if negative_count > 0:
            risks.append(
                f"{negative_count:,} records contain negative profit."
            )

            recommendations.append(
                "Investigate loss-making orders, products, and customer segments."
            )

    category_performance = get_group_performance(
        df,
        category_col,
        sales_col
    )

    if category_performance:
        findings.append(
            f"The best category is "
            f"'{category_performance['best_name']}' "
            f"with sales of "
            f"{format_number(category_performance['best_value'])}."
        )

        findings.append(
            f"The weakest category is "
            f"'{category_performance['worst_name']}' "
            f"with sales of "
            f"{format_number(category_performance['worst_value'])}."
        )

        recommendations.append(
            f"Protect growth in "
            f"'{category_performance['best_name']}' "
            f"and review the strategy for "
            f"'{category_performance['worst_name']}'."
        )

    segment_performance = get_group_performance(
        df,
        segment_col,
        sales_col
    )

    if segment_performance:
        findings.append(
            f"The strongest segment is "
            f"'{segment_performance['best_name']}' "
            f"with sales of "
            f"{format_number(segment_performance['best_value'])}."
        )

    region_performance = get_group_performance(
        df,
        region_col,
        sales_col
    )

    if region_performance:
        findings.append(
            f"The best-performing {region_col} is "
            f"'{region_performance['best_name']}' "
            f"with sales of "
            f"{format_number(region_performance['best_value'])}."
        )

        risks.append(
            f"The weakest-performing {region_col} is "
            f"'{region_performance['worst_name']}' "
            f"with sales of "
            f"{format_number(region_performance['worst_value'])}."
        )

        recommendations.append(
            f"Create a targeted sales plan for "
            f"'{region_performance['worst_name']}'."
        )

    top_product = get_top_product(
        df,
        product_col,
        sales_col
    )

    if top_product:
        findings.append(
            f"The top product is "
            f"'{top_product['name']}' "
            f"with sales of "
            f"{format_number(top_product['value'])}."
        )

    monthly_performance = get_monthly_performance(
        df,
        date_col,
        sales_col
    )

    if monthly_performance:
        findings.append(
            f"Peak sales occurred in "
            f"{monthly_performance['peak_month']} "
            f"with sales of "
            f"{format_number(monthly_performance['peak_value'])}."
        )

        findings.append(
            f"The weakest month was "
            f"{monthly_performance['weakest_month']} "
            f"with sales of "
            f"{format_number(monthly_performance['weakest_value'])}."
        )

        if "overall_change_percent" in monthly_performance:
            change = monthly_performance[
                "overall_change_percent"
            ]

            direction = (
                "increased"
                if change >= 0
                else "decreased"
            )

            findings.append(
                f"Sales {direction} by "
                f"{abs(change):.2f}% from the first "
                f"available month to the latest month."
            )

            if change < -10:
                risks.append(
                    "Sales show a meaningful downward trend."
                )

                recommendations.append(
                    "Investigate the causes of the recent sales decline."
                )

    if discount_col and profit_col:
        temp = df[
            [discount_col, profit_col]
        ].copy()

        temp[discount_col] = pd.to_numeric(
            temp[discount_col],
            errors="coerce"
        )

        temp[profit_col] = pd.to_numeric(
            temp[profit_col],
            errors="coerce"
        )

        temp = temp.dropna()

        if len(temp) >= 2:
            correlation = temp[
                [discount_col, profit_col]
            ].corr().iloc[0, 1]

            if not pd.isna(correlation):
                findings.append(
                    f"Discount and profit correlation is "
                    f"{correlation:.2f}."
                )

                if correlation < -0.25:
                    risks.append(
                        "Higher discounts are associated with lower profit."
                    )

                    recommendations.append(
                        "Introduce discount approval limits for low-margin orders."
                    )

    if stats["missing_values"] > 0:
        recommendations.insert(
            0,
            "Clean or impute missing values before advanced modeling."
        )

    if stats["duplicate_rows"] > 0:
        recommendations.insert(
            0,
            "Remove duplicate rows before final KPI reporting."
        )

    if not risks:
        risks.append(
            "No major business risks were automatically detected."
        )

    recommendations.extend([
        "Track sales and profit trends monthly.",
        "Monitor margin by category, region, and product.",
        "Create alerts for declining sales and negative-profit orders."
    ])

    return {
        "kpis": kpis,
        "findings": findings[:12],
        "risks": risks[:8],
        "recommendations": recommendations[:10]
    }


def generate_generic_intelligence(df, stats):
    findings = []
    risks = []
    recommendations = []

    numeric_columns = df.select_dtypes(
        include="number"
    ).columns.tolist()

    categorical_columns = df.select_dtypes(
        include=["object", "category"]
    ).columns.tolist()

    findings.append(
        f"{len(numeric_columns)} numeric columns were detected."
    )

    findings.append(
        f"{len(categorical_columns)} categorical columns were detected."
    )

    for column in numeric_columns[:5]:
        series = pd.to_numeric(
            df[column],
            errors="coerce"
        ).dropna()

        if not series.empty:
            findings.append(
                f"Average {column} is "
                f"{format_number(series.mean())}, "
                f"with a minimum of "
                f"{format_number(series.min())} "
                f"and a maximum of "
                f"{format_number(series.max())}."
            )

    if stats["missing_values"] > 0:
        risks.append(
            "Missing values may affect analytical reliability."
        )

        recommendations.append(
            "Clean or impute missing values."
        )

    if stats["duplicate_rows"] > 0:
        risks.append(
            "Duplicate rows may distort KPIs."
        )

        recommendations.append(
            "Remove duplicate records."
        )

    if not risks:
        risks.append(
            "No major data-quality risks were detected."
        )

    recommendations.extend([
        "Create KPI cards for important numeric measures.",
        "Analyze relationships between numeric columns.",
        "Use grouped charts for categorical performance.",
        "Apply forecasting when date-based columns are available."
    ])

    return {
        "kpis": {},
        "findings": findings[:10],
        "risks": risks[:6],
        "recommendations": recommendations[:8]
    }


def generate_executive_report(df, stats):
    dataset_type = detect_dataset_type(df)

    summary = (
        f"This dataset contains {stats['rows']:,} rows and "
        f"{stats['columns']:,} columns. "
        f"The overall data quality score is "
        f"{stats['quality_score']}%. "
        f"There are {stats['missing_values']:,} missing values and "
        f"{stats['duplicate_rows']:,} duplicate rows. "
        f"The system classified this as a "
        f"{dataset_type.replace('_', ' ')} dataset."
    )

    if dataset_type == "sales":
        intelligence = generate_sales_intelligence(
            df,
            stats
        )
    else:
        intelligence = generate_generic_intelligence(
            df,
            stats
        )

    if stats["quality_score"] >= 90:
        conclusion = (
            "The dataset is suitable for executive dashboards, "
            "business intelligence analysis, forecasting, "
            "and automated reporting."
        )
    elif stats["quality_score"] >= 75:
        conclusion = (
            "The dataset can support business analysis after "
            "minor data-quality improvements."
        )
    else:
        conclusion = (
            "The dataset requires cleaning and validation before "
            "reliable decision-making or predictive modeling."
        )

    return {
        "dataset_type": dataset_type,
        "summary": summary,
        "kpis": intelligence["kpis"],
        "findings": intelligence["findings"],
        "risks": intelligence["risks"],
        "recommendations": intelligence["recommendations"],
        "conclusion": conclusion
    }