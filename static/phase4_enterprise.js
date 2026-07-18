
"use strict";

document.addEventListener("DOMContentLoaded", () => {
    const charts = window.phase4Charts || [];

    charts.forEach((chart, index) => {
        const element = document.getElementById(`phase4Chart${index + 1}`);
        if (!element || !window.Plotly) return;

        let trace;

        if (chart.type === "pie") {
            trace = {
                type: "pie",
                labels: chart.labels,
                values: chart.values,
                hole: 0.42,
            };
        } else if (chart.type === "scatter") {
            trace = {
                type: "scatter",
                mode: "markers",
                x: chart.x,
                y: chart.y,
            };
        } else {
            trace = {
                type: "bar",
                x: chart.x,
                y: chart.y,
            };
        }

        Plotly.newPlot(
            element,
            [trace],
            {
                title: chart.title,
                autosize: true,
                margin: { t: 55, r: 20, b: 85, l: 70 },
                paper_bgcolor: "transparent",
                plot_bgcolor: "transparent",
            },
            { responsive: true, displaylogo: false }
        );
    });

    const chatForm = document.getElementById("phase4ChatForm");

    if (chatForm) {
        chatForm.addEventListener("submit", async (event) => {
            event.preventDefault();

            const input = document.getElementById("phase4ChatInput");
            const messages = document.getElementById("phase4ChatMessages");
            const question = input.value.trim();

            if (!question) return;

            const userMessage = document.createElement("div");
            userMessage.className = "phase4-chat-message user";
            userMessage.textContent = question;
            messages.appendChild(userMessage);
            input.value = "";

            const response = await fetch(window.phase4Config.copilotEndpoint, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    filename: window.phase4Config.filename,
                    question,
                }),
            });

            const payload = await response.json();

            const assistantMessage = document.createElement("div");
            assistantMessage.className = "phase4-chat-message assistant";
            assistantMessage.textContent =
                payload.answer || payload.message || "No response.";
            messages.appendChild(assistantMessage);
            messages.scrollTop = messages.scrollHeight;
        });
    }

    const forecastForm = document.getElementById("phase4ForecastForm");

    if (forecastForm) {
        forecastForm.addEventListener("submit", async (event) => {
            event.preventDefault();

            const status = document.getElementById("phase4ForecastStatus");
            const results = document.getElementById("phase4ForecastResults");

            status.hidden = false;
            status.classList.remove("error");
            status.textContent = "Generating forecast...";

            const response = await fetch(window.phase4ForecastConfig.endpoint, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    filename: window.phase4ForecastConfig.filename,
                    date_column: document.getElementById("phase4DateColumn").value,
                    value_column: document.getElementById("phase4ValueColumn").value,
                    periods: Number(document.getElementById("phase4Periods").value),
                }),
            });

            const payload = await response.json();

            if (!response.ok || payload.success === false) {
                status.classList.add("error");
                status.textContent = payload.message || "Forecasting failed.";
                return;
            }

            status.textContent = "Forecast generated successfully.";
            results.hidden = false;

            const metrics = document.getElementById("phase4ForecastMetrics");
            metrics.innerHTML = "";

            Object.entries(payload.metrics).forEach(([key, value]) => {
                const card = document.createElement("article");
                card.className = "phase4-kpi";
                card.innerHTML = `<span>${key.replaceAll("_", " ")}</span><strong>${value}</strong>`;
                metrics.appendChild(card);
            });

            Plotly.newPlot(
                "phase4ForecastChart",
                [
                    {
                        type: "scatter",
                        mode: "lines+markers",
                        name: "History",
                        x: payload.history.dates,
                        y: payload.history.values,
                    },
                    {
                        type: "scatter",
                        mode: "lines",
                        name: "Forecast",
                        x: payload.forecast.dates,
                        y: payload.forecast.values,
                    },
                    {
                        type: "scatter",
                        mode: "lines",
                        name: "Upper",
                        x: payload.forecast.dates,
                        y: payload.forecast.upper,
                        line: { dash: "dot" },
                    },
                    {
                        type: "scatter",
                        mode: "lines",
                        name: "Lower",
                        x: payload.forecast.dates,
                        y: payload.forecast.lower,
                        line: { dash: "dot" },
                    },
                ],
                { title: "Forecast with Confidence Range", paper_bgcolor: "transparent", plot_bgcolor: "transparent" },
                { responsive: true, displaylogo: false }
            );

            Plotly.newPlot(
                "phase4ScenarioChart",
                [
                    { type: "scatter", mode: "lines", name: "Optimistic", x: payload.forecast.dates, y: payload.scenario.optimistic },
                    { type: "scatter", mode: "lines", name: "Base", x: payload.forecast.dates, y: payload.scenario.base },
                    { type: "scatter", mode: "lines", name: "Conservative", x: payload.forecast.dates, y: payload.scenario.conservative },
                ],
                { title: "Scenario Planning", paper_bgcolor: "transparent", plot_bgcolor: "transparent" },
                { responsive: true, displaylogo: false }
            );
        });
    }

    const refreshButton = document.getElementById("phase4RefreshButton");

    async function refreshRealtime() {
        if (!window.phase4RealtimeConfig) return;

        const response = await fetch(window.phase4RealtimeConfig.endpoint);
        const payload = await response.json();

        const kpiContainer = document.getElementById("phase4RealtimeKpis");
        const alertContainer = document.getElementById("phase4RealtimeAlerts");

        kpiContainer.innerHTML = "";
        alertContainer.innerHTML = "";

        (payload.kpis || []).forEach((kpi) => {
            const card = document.createElement("article");
            card.className = "phase4-kpi";
            card.innerHTML = `<span>${kpi.title}</span><strong>${kpi.value}</strong><small>${kpi.subtitle}</small>`;
            kpiContainer.appendChild(card);
        });

        (payload.alerts || []).forEach((alert) => {
            const card = document.createElement("article");
            card.className = `phase4-insight ${alert.severity || ""}`;
            card.innerHTML = `<strong>${alert.title}</strong><p>${alert.message}</p>`;
            alertContainer.appendChild(card);
        });
    }

    if (refreshButton) {
        refreshButton.addEventListener("click", refreshRealtime);
        window.setInterval(refreshRealtime, 30000);
    }

    const publishForm = document.getElementById("phase4PublishForm");

    if (publishForm) {
        publishForm.addEventListener("submit", async (event) => {
            event.preventDefault();

            const response = await fetch(window.phase4WorkspaceConfig.endpoint, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    filename: window.phase4WorkspaceConfig.filename,
                    name: document.getElementById("phase4DashboardName").value,
                }),
            });

            const payload = await response.json();

            if (payload.success) {
                window.location.reload();
            }
        });
    }
});
