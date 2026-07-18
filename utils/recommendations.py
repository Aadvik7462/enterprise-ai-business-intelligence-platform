def generate_recommendations(stats):
    recommendations = []

    # Dataset Quality
    if stats["quality_score"] >= 95:
        recommendations.append({
            "type": "success",
            "title": "Dataset Ready",
            "message": "Dataset quality is excellent and ready for reporting."
        })
    elif stats["quality_score"] >= 80:
        recommendations.append({
            "type": "warning",
            "title": "Minor Cleaning",
            "message": "Perform minor cleaning before advanced analytics."
        })
    else:
        recommendations.append({
            "type": "danger",
            "title": "Cleaning Required",
            "message": "Clean the dataset before analysis."
        })

    # Missing Values
    if stats["missing_values"] == 0:
        recommendations.append({
            "type": "success",
            "title": "Missing Values",
            "message": "No missing values detected."
        })
    else:
        recommendations.append({
            "type": "warning",
            "title": "Missing Values",
            "message": f"{stats['missing_values']} missing values detected."
        })

    # Duplicate Rows
    if stats["duplicate_rows"] == 0:
        recommendations.append({
            "type": "success",
            "title": "Duplicates",
            "message": "No duplicate rows found."
        })
    else:
        recommendations.append({
            "type": "warning",
            "title": "Duplicates",
            "message": f"{stats['duplicate_rows']} duplicate rows found."
        })

    # Forecast
    recommendations.append({
        "type": "info",
        "title": "Forecast",
        "message": "Time-series forecasting is recommended if a date column exists."
    })

    # Dashboard
    recommendations.append({
        "type": "info",
        "title": "Visualization",
        "message": "Interactive dashboards can now be generated."
    })

    return recommendations