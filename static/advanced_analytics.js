(() => {
    "use strict";
    const config = window.advancedAnalyticsConfig || {};
    const targetColumn = document.getElementById("advancedTargetColumn");

    async function requestJson(url, options = {}) {
        const response = await fetch(url, { ...options, headers: {"Content-Type": "application/json", ...(options.headers || {})} });
        const result = await response.json();
        if (!response.ok || !result.success) throw new Error(result.message || "Analysis failed.");
        return result;
    }

    function renderCorrelation(result) {
        Plotly.newPlot("correlationHeatmap", [{z: result.matrix, x: result.columns, y: result.columns, type: "heatmap", zmin: -1, zmax: 1}], {template: "plotly_white", margin: {l: 110, r: 30, t: 30, b: 110}}, {responsive: true, displaylogo: false});
    }

    function renderHorizontal(id, labels, values) {
        Plotly.newPlot(id, [{x: values, y: labels, type: "bar", orientation: "h"}], {template: "plotly_white", margin: {l: 140, r: 30, t: 30, b: 50}, yaxis: {autorange: "reversed"}}, {responsive: true, displaylogo: false});
    }

    function renderStatistics(result) {
        const body = document.getElementById("advancedStatisticsBody");
        body.innerHTML = "";
        result.summaries.forEach(item => {
            const row = document.createElement("tr");
            [item.column, item.count, item.mean, item.median, item.std, item.minimum, item.maximum, item.skewness, item.kurtosis].forEach(value => {
                const cell = document.createElement("td");
                cell.textContent = value;
                row.appendChild(cell);
            });
            body.appendChild(row);
        });
    }

    async function loadAll() {
        const filename = encodeURIComponent(config.filename);
        try {
            const [correlation, outliers, missing, statistics, importance] = await Promise.all([
                requestJson(`/api/advanced-analytics/${filename}/correlation`),
                requestJson(`/api/advanced-analytics/${filename}/outliers`),
                requestJson(`/api/advanced-analytics/${filename}/missing`),
                requestJson(`/api/advanced-analytics/${filename}/statistics`),
                requestJson(`/api/advanced-analytics/${filename}/feature-importance`, {method: "POST", body: JSON.stringify({target_column: targetColumn?.value || ""})})
            ]);
            renderCorrelation(correlation);
            renderHorizontal("featureImportanceChart", importance.features.map(i => i.feature), importance.features.map(i => i.importance));
            renderHorizontal("outlierChart", outliers.results.map(i => i.column), outliers.results.map(i => i.outlier_count));
            const missingRows = missing.results.filter(i => i.missing_count > 0);
            renderHorizontal("missingValueChart", missingRows.map(i => i.column), missingRows.map(i => i.missing_count));
            renderStatistics(statistics);
        } catch (error) {
            if (typeof window.showGlobalToast === "function") window.showGlobalToast(error.message, "error");
            else window.alert(error.message);
        }
    }

    document.getElementById("loadAdvancedAnalyticsButton")?.addEventListener("click", loadAll);
    loadAll();
})();
