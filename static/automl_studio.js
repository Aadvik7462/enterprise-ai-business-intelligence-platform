
"use strict";

document.addEventListener("DOMContentLoaded", () => {
    const config = window.automlStudioConfig || {};

    const elements = {
        form: document.getElementById("automlForm"),
        targetColumn: document.getElementById("automlTargetColumn"),
        testSize: document.getElementById("automlTestSize"),
        trainButton: document.getElementById("automlTrainButton"),
        progressCard: document.getElementById("automlProgressCard"),
        progressTitle: document.getElementById("automlProgressTitle"),
        progressMessage: document.getElementById("automlProgressMessage"),
        progressPercent: document.getElementById("automlProgressPercent"),
        progressBar: document.getElementById("automlProgressBar"),
        status: document.getElementById("automlStatus"),
        results: document.getElementById("automlResults"),
        resultTitle: document.getElementById("automlResultTitle"),
        bestModelName: document.getElementById("automlBestModelName"),
        bestModelReason: document.getElementById("automlBestModelReason"),
        bestMetrics: document.getElementById("automlBestMetrics"),
        leaderboardTable: document.getElementById("automlLeaderboardTable"),
        previewTable: document.getElementById("automlPreviewTable"),
        leaderboardChart: document.getElementById("automlLeaderboardChart"),
        featureImportance: document.getElementById("automlFeatureImportance"),
        downloadModel: document.getElementById("automlDownloadModel"),
        downloadLeaderboard: document.getElementById("automlDownloadLeaderboard"),
        downloadPredictions: document.getElementById("automlDownloadPredictions"),
    };

    let progressTimer = null;

    function setBusy(value) {
        elements.trainButton.disabled = value;
        elements.trainButton.textContent = value
            ? "Running AutoML..."
            : "Run AutoML";
    }

    function showStatus(message, error = false) {
        elements.status.hidden = false;
        elements.status.textContent = message;
        elements.status.classList.toggle("error", error);
    }

    function setProgress(percent, title, message) {
        elements.progressCard.hidden = false;
        elements.progressPercent.textContent = `${percent}%`;
        elements.progressBar.style.width = `${percent}%`;

        if (title) {
            elements.progressTitle.textContent = title;
        }

        if (message) {
            elements.progressMessage.textContent = message;
        }
    }

    function startProgress() {
        let value = 4;

        setProgress(
            value,
            "Preparing AutoML pipeline",
            "Profiling dataset and configuring candidate models."
        );

        progressTimer = window.setInterval(() => {
            value = Math.min(value + Math.floor(Math.random() * 8) + 2, 92);

            let title = "Training candidate models";
            let message = "Evaluating model performance and training time.";

            if (value > 35) {
                title = "Comparing models";
                message = "Ranking successful models on validation metrics.";
            }

            if (value > 68) {
                title = "Selecting the best model";
                message = "Generating explanations and export files.";
            }

            setProgress(value, title, message);
        }, 650);
    }

    function finishProgress() {
        if (progressTimer) {
            window.clearInterval(progressTimer);
            progressTimer = null;
        }

        setProgress(
            100,
            "AutoML complete",
            "The leaderboard and recommended model are ready."
        );
    }

    function stopProgressOnError() {
        if (progressTimer) {
            window.clearInterval(progressTimer);
            progressTimer = null;
        }
    }

    function labelize(value) {
        return String(value)
            .replace(/_/g, " ")
            .replace(/\b\w/g, (letter) => letter.toUpperCase());
    }

    function renderBestModel(bestModel) {
        elements.bestModelName.textContent =
            bestModel.model_name || "Recommended model";

        elements.bestModelReason.textContent =
            bestModel.selection_reason || "";

        elements.bestMetrics.innerHTML = "";

        const excluded = new Set([
            "model_name",
            "status",
            "selection_reason",
            "error",
        ]);

        Object.entries(bestModel || {})
            .filter(([key]) => !excluded.has(key))
            .slice(0, 6)
            .forEach(([key, value]) => {
                const card = document.createElement("article");
                card.className = "automl-best-metric";

                const label = document.createElement("span");
                label.textContent = labelize(key);

                const strong = document.createElement("strong");
                strong.textContent = String(value);

                card.append(label, strong);
                elements.bestMetrics.appendChild(card);
            });
    }

    function renderTable(table, rows) {
        const head = table.querySelector("thead");
        const body = table.querySelector("tbody");

        head.innerHTML = "";
        body.innerHTML = "";

        if (!Array.isArray(rows) || !rows.length) {
            return;
        }

        const preferred = [
            "model_name",
            "status",
            "score",
            "accuracy",
            "precision",
            "recall",
            "f1_score",
            "r2_score",
            "mae",
            "rmse",
            "training_time",
            "actual",
            "predicted",
        ];

        const allColumns = Array.from(
            new Set(
                rows.flatMap((row) => Object.keys(row))
            )
        );

        const columns = [
            ...preferred.filter((column) => allColumns.includes(column)),
            ...allColumns.filter((column) => !preferred.includes(column)),
        ];

        const headerRow = document.createElement("tr");

        columns.forEach((column) => {
            const th = document.createElement("th");
            th.textContent = labelize(column);
            headerRow.appendChild(th);
        });

        head.appendChild(headerRow);

        rows.forEach((row) => {
            const tr = document.createElement("tr");

            columns.forEach((column) => {
                const td = document.createElement("td");
                const value = row[column];

                td.textContent =
                    value === undefined || value === null
                        ? "—"
                        : String(value);

                tr.appendChild(td);
            });

            body.appendChild(tr);
        });
    }

    function renderLeaderboardChart(rows) {
        if (!window.Plotly || !Array.isArray(rows)) {
            return;
        }

        const successful = rows.filter(
            (row) => row.status === "Success"
        );

        Plotly.newPlot(
            elements.leaderboardChart,
            [{
                type: "bar",
                orientation: "h",
                x: successful.map((row) => row.score).reverse(),
                y: successful.map((row) => row.model_name).reverse(),
                text: successful.map((row) => row.score).reverse(),
                textposition: "auto",
                hovertemplate:
                    "%{y}<br>Score: %{x}<extra></extra>",
            }],
            {
                title: "Validation Score by Model",
                autosize: true,
                margin: {
                    t: 55,
                    r: 25,
                    b: 55,
                    l: 135,
                },
                paper_bgcolor: "transparent",
                plot_bgcolor: "transparent",
                xaxis: {
                    title: "Score",
                },
            },
            {
                responsive: true,
                displaylogo: false,
            }
        );
    }

    function renderFeatureImportance(items) {
        elements.featureImportance.innerHTML = "";

        if (!Array.isArray(items) || !items.length) {
            elements.featureImportance.textContent =
                "Feature importance is unavailable for the selected model.";
            return;
        }

        const maximum = Math.max(
            ...items.map((item) => Number(item.importance) || 0),
            1
        );

        items.forEach((item) => {
            const wrapper = document.createElement("div");
            wrapper.className = "automl-feature-item";

            const name = document.createElement("span");
            name.textContent = item.feature;

            const value = document.createElement("strong");
            value.textContent = Number(item.importance).toFixed(4);

            const bar = document.createElement("div");
            bar.className = "automl-feature-bar";

            const fill = document.createElement("div");
            fill.style.width = `${Math.max(
                2,
                (Number(item.importance) / maximum) * 100
            )}%`;

            bar.appendChild(fill);
            wrapper.append(name, value, bar);
            elements.featureImportance.appendChild(wrapper);
        });
    }

    elements.form.addEventListener("submit", async (event) => {
        event.preventDefault();

        const targetColumn = elements.targetColumn.value;

        if (!targetColumn) {
            showStatus("Select a target column before running AutoML.", true);
            return;
        }

        setBusy(true);
        elements.results.hidden = true;
        elements.status.hidden = true;
        startProgress();

        try {
            const response = await fetch(config.trainEndpoint, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                body: JSON.stringify({
                    filename: config.filename,
                    target_column: targetColumn,
                    test_size: Number(elements.testSize.value),
                }),
            });

            const payload = await response
                .json()
                .catch(() => ({}));

            if (!response.ok || payload.success === false) {
                throw new Error(
                    payload.message || "AutoML training failed."
                );
            }

            finishProgress();
            showStatus(payload.message);

            elements.results.hidden = false;
            elements.resultTitle.textContent =
                `${labelize(payload.task_type)} Model Leaderboard`;

            renderBestModel(payload.best_model || {});
            renderTable(
                elements.leaderboardTable,
                payload.leaderboard || []
            );
            renderLeaderboardChart(payload.leaderboard || []);
            renderFeatureImportance(
                payload.feature_importance || []
            );
            renderTable(
                elements.previewTable,
                payload.preview || []
            );

            const downloads = payload.downloads || {};

            if (downloads.model) {
                elements.downloadModel.hidden = false;
                elements.downloadModel.href = downloads.model;
            }

            if (downloads.leaderboard) {
                elements.downloadLeaderboard.hidden = false;
                elements.downloadLeaderboard.href =
                    downloads.leaderboard;
            }

            if (downloads.predictions) {
                elements.downloadPredictions.hidden = false;
                elements.downloadPredictions.href =
                    downloads.predictions;
            }

            elements.results.scrollIntoView({
                behavior: "smooth",
                block: "start",
            });
        } catch (error) {
            stopProgressOnError();
            showStatus(
                error.message || "AutoML training failed.",
                true
            );
        } finally {
            setBusy(false);
        }
    });
});
