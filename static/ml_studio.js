
"use strict";

document.addEventListener("DOMContentLoaded", () => {
    const config = window.mlStudioConfig || {};

    const elements = {
        form: document.getElementById("mlStudioForm"),
        taskType: document.getElementById("mlTaskType"),
        targetColumn: document.getElementById("mlTargetColumn"),
        modelName: document.getElementById("mlModelName"),
        testSize: document.getElementById("mlTestSize"),
        clusterCount: document.getElementById("mlClusterCount"),
        trainButton: document.getElementById("mlTrainButton"),
        status: document.getElementById("mlStudioStatus"),
        results: document.getElementById("mlStudioResults"),
        title: document.getElementById("mlStudioResultTitle"),
        metrics: document.getElementById("mlMetricsGrid"),
        chart: document.getElementById("mlStudioChart"),
        importance: document.getElementById("mlFeatureImportance"),
        table: document.getElementById("mlPreviewTable"),
        download: document.getElementById("mlDownloadModel"),
    };

    function showStatus(message, error = false) {
        elements.status.hidden = false;
        elements.status.textContent = message;
        elements.status.classList.toggle("error", error);
    }

    function setBusy(value) {
        elements.trainButton.disabled = value;
        elements.trainButton.textContent = value ? "Training..." : "Train Model";
    }

    function renderMetrics(metrics) {
        elements.metrics.innerHTML = "";

        Object.entries(metrics || {}).forEach(([key, value]) => {
            const card = document.createElement("article");
            card.className = "ml-studio-metric-card";

            const label = document.createElement("span");
            label.textContent = key
                .replace(/_/g, " ")
                .replace(/\b\w/g, (letter) => letter.toUpperCase());

            const strong = document.createElement("strong");
            strong.textContent = String(value);

            card.append(label, strong);
            elements.metrics.appendChild(card);
        });
    }

    function renderImportance(items) {
        elements.importance.innerHTML = "";

        if (!Array.isArray(items) || !items.length) {
            elements.importance.textContent = "Feature importance is not available.";
            return;
        }

        const maxValue = Math.max(
            ...items.map((item) => Number(item.importance) || 0),
            1
        );

        items.forEach((item) => {
            const wrapper = document.createElement("div");
            wrapper.className = "ml-feature-item";

            const name = document.createElement("span");
            name.textContent = item.feature;

            const value = document.createElement("strong");
            value.textContent = Number(item.importance).toFixed(4);

            const bar = document.createElement("div");
            bar.className = "ml-feature-bar";

            const fill = document.createElement("div");
            fill.style.width = `${Math.max(
                2,
                (Number(item.importance) / maxValue) * 100
            )}%`;

            bar.appendChild(fill);
            wrapper.append(name, value, bar);
            elements.importance.appendChild(wrapper);
        });
    }

    function renderChart(chart) {
        elements.chart.innerHTML = "";

        if (!chart || !window.Plotly) {
            return;
        }

        if (chart.type === "cluster_scatter") {
            Plotly.newPlot(
                elements.chart,
                [{
                    type: "scatter",
                    mode: "markers",
                    x: chart.x,
                    y: chart.y,
                    marker: {
                        color: chart.labels,
                        size: 9,
                        opacity: 0.75,
                        colorscale: "Viridis",
                        showscale: true,
                    },
                }],
                {
                    title: chart.title,
                    xaxis: { title: chart.x_label },
                    yaxis: { title: chart.y_label },
                    autosize: true,
                    margin: { t: 55, r: 20, b: 70, l: 70 },
                    paper_bgcolor: "transparent",
                    plot_bgcolor: "transparent",
                },
                {
                    responsive: true,
                    displaylogo: false,
                }
            );
            return;
        }

        if (chart.type === "classification") {
            const values = chart.actual.map((actual, index) => ({
                actual,
                predicted: chart.predicted[index],
            }));

            const counts = {};

            values.forEach((item) => {
                const key = `${item.actual} → ${item.predicted}`;
                counts[key] = (counts[key] || 0) + 1;
            });

            Plotly.newPlot(
                elements.chart,
                [{
                    type: "bar",
                    x: Object.keys(counts),
                    y: Object.values(counts),
                }],
                {
                    title: chart.title,
                    autosize: true,
                    margin: { t: 55, r: 20, b: 110, l: 70 },
                    paper_bgcolor: "transparent",
                    plot_bgcolor: "transparent",
                },
                {
                    responsive: true,
                    displaylogo: false,
                }
            );
            return;
        }

        Plotly.newPlot(
            elements.chart,
            [{
                type: "scatter",
                mode: "markers",
                x: chart.x,
                y: chart.y,
            }],
            {
                title: chart.title,
                xaxis: { title: "Actual" },
                yaxis: { title: "Predicted" },
                autosize: true,
                margin: { t: 55, r: 20, b: 70, l: 70 },
                paper_bgcolor: "transparent",
                plot_bgcolor: "transparent",
            },
            {
                responsive: true,
                displaylogo: false,
            }
        );
    }

    function renderPreview(rows) {
        const head = elements.table.querySelector("thead");
        const body = elements.table.querySelector("tbody");

        head.innerHTML = "";
        body.innerHTML = "";

        if (!Array.isArray(rows) || !rows.length) {
            return;
        }

        const columns = Object.keys(rows[0]);
        const headerRow = document.createElement("tr");

        columns.forEach((column) => {
            const th = document.createElement("th");
            th.textContent = column;
            headerRow.appendChild(th);
        });

        head.appendChild(headerRow);

        rows.forEach((row) => {
            const tr = document.createElement("tr");

            columns.forEach((column) => {
                const td = document.createElement("td");
                const value = row[column];
                td.textContent = value === null || value === undefined ? "—" : String(value);
                tr.appendChild(td);
            });

            body.appendChild(tr);
        });
    }

    elements.taskType.addEventListener("change", () => {
        const clustering = elements.taskType.value === "clustering";

        elements.targetColumn.disabled = clustering;
        elements.modelName.disabled = clustering;
        elements.testSize.disabled = clustering;
        elements.clusterCount.disabled = !clustering;
    });

    elements.form.addEventListener("submit", async (event) => {
        event.preventDefault();

        setBusy(true);
        showStatus("Training model...");

        try {
            const response = await fetch(config.trainEndpoint, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                body: JSON.stringify({
                    filename: config.filename,
                    task_type: elements.taskType.value,
                    target_column: elements.targetColumn.value,
                    model_name: elements.modelName.value,
                    test_size: Number(elements.testSize.value),
                    cluster_count: Number(elements.clusterCount.value),
                }),
            });

            const payload = await response.json().catch(() => ({}));

            if (!response.ok || payload.success === false) {
                throw new Error(payload.message || "Model training failed.");
            }

            showStatus(payload.message);

            elements.results.hidden = false;
            elements.title.textContent = `${payload.task_type} · ${payload.model_name}`;

            renderMetrics(payload.metrics || {});
            renderImportance(payload.feature_importance || []);
            renderChart(payload.chart || {});
            renderPreview(payload.preview || []);

            if (payload.download_url) {
                elements.download.hidden = false;
                elements.download.href = payload.download_url;
            }

            elements.results.scrollIntoView({
                behavior: "smooth",
                block: "start",
            });
        } catch (error) {
            showStatus(error.message || "Model training failed.", true);
        } finally {
            setBusy(false);
        }
    });

    elements.taskType.dispatchEvent(new Event("change"));
});
