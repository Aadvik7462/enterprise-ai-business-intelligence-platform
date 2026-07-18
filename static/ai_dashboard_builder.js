
"use strict";

document.addEventListener("DOMContentLoaded", () => {
    const payload =
        window.aiDashboardBuilderData || {};

    const charts = Array.isArray(payload.charts)
        ? payload.charts
        : [];

    charts.forEach((chart, index) => {
        const target =
            `aiGeneratedChart${index + 1}`;

        const records = Array.isArray(
            chart.records
        )
            ? chart.records
            : [];

        if (!records.length || !window.Plotly) {
            return;
        }

        let traces = [];

        if (chart.type === "scatter") {
            traces = [{
                type: "scatter",
                mode: "markers",
                x: records.map(
                    (row) => row[chart.x]
                ),
                y: records.map(
                    (row) => row[chart.y]
                ),
                marker: {
                    size: 8,
                    opacity: 0.7,
                },
            }];
        } else if (chart.type === "line") {
            traces = [{
                type: "scatter",
                mode: "lines+markers",
                x: records.map(
                    (row) => row[chart.x]
                ),
                y: records.map(
                    (row) => row[chart.y]
                ),
            }];
        } else if (chart.type === "pie") {
            traces = [{
                type: "pie",
                labels: records.map(
                    (row) => row[chart.x]
                ),
                values: records.map(
                    (row) => row[chart.y]
                ),
                hole: 0.42,
            }];
        } else {
            traces = [{
                type: "bar",
                x: records.map(
                    (row) => row[chart.x]
                ),
                y: records.map(
                    (row) => row[chart.y]
                ),
            }];
        }

        Plotly.newPlot(
            target,
            traces,
            {
                title: chart.title,
                autosize: true,
                margin: {
                    t: 55,
                    r: 20,
                    b: 80,
                    l: 65,
                },
                paper_bgcolor: "transparent",
                plot_bgcolor: "transparent",
            },
            {
                responsive: true,
                displaylogo: false,
            }
        );
    });

    document
        .querySelectorAll(
            ".ai-dashboard-kpi-value"
        )
        .forEach((element) => {
            const rawValue = Number(
                element.dataset.value
            );

            if (Number.isNaN(rawValue)) {
                return;
            }

            const format =
                element.dataset.format;

            const formatted =
                new Intl.NumberFormat(
                    undefined,
                    {
                        maximumFractionDigits: 2,
                    }
                ).format(rawValue);

            element.textContent =
                format === "percent"
                    ? `${formatted}%`
                    : formatted;
        });
});
