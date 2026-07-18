
"use strict";

document.addEventListener("DOMContentLoaded", () => {
    const config = window.aiAssistantConfig || {};
    const endpoint = config.endpoint || "/ai/chat";
    const datasetName = config.datasetName || "uploaded dataset";
    const storageKey = config.storageKey || "ai-bi-v2-chat";

    const elements = {
        launcher: document.getElementById("aiAssistantLauncher"),
        panel: document.getElementById("aiAssistantPanel"),
        close: document.getElementById("aiAssistantClose"),
        minimize: document.getElementById("aiAssistantMinimize"),
        clear: document.getElementById("aiAssistantClear"),
        export: document.getElementById("aiAssistantExport"),
        form: document.getElementById("aiAssistantForm"),
        input: document.getElementById("aiAssistantInput"),
        send: document.getElementById("aiAssistantSend"),
        messages: document.getElementById("aiAssistantMessages"),
        prompts: document.querySelectorAll(".ai-prompt-chip"),
    };

    if (!elements.launcher || !elements.panel || !elements.form || !elements.input || !elements.messages) {
        return;
    }

    let busy = false;
    let minimized = false;

    function scrollToBottom(smooth = true) {
        requestAnimationFrame(() => {
            elements.messages.scrollTo({
                top: elements.messages.scrollHeight,
                behavior: smooth ? "smooth" : "auto",
            });
        });
    }

    function resizeInput() {
        elements.input.style.height = "auto";
        elements.input.style.height = `${Math.min(elements.input.scrollHeight, 140)}px`;
    }

    function setBusy(value) {
        busy = value;
        elements.input.disabled = value;
        elements.send.disabled = value;
        elements.send.classList.toggle("loading", value);
        elements.prompts.forEach((button) => {
            button.disabled = value;
        });
    }

    function openPanel() {
        elements.panel.classList.add("active");
        elements.launcher.classList.add("open");
        elements.panel.setAttribute("aria-hidden", "false");
        elements.launcher.setAttribute("aria-expanded", "true");

        if (minimized) {
            toggleMinimize();
        }

        setTimeout(() => {
            elements.input.focus();
            scrollToBottom(false);
        }, 150);
    }

    function closePanel() {
        elements.panel.classList.remove("active");
        elements.launcher.classList.remove("open");
        elements.panel.setAttribute("aria-hidden", "true");
        elements.launcher.setAttribute("aria-expanded", "false");
    }

    function toggleMinimize() {
        minimized = !minimized;
        elements.panel.classList.toggle("minimized", minimized);
        elements.minimize.textContent = minimized ? "□" : "—";
    }

    function createMessage(text, role = "assistant", error = false) {
        const article = document.createElement("article");
        article.className = [
            "ai-chat-message",
            role === "user" ? "ai-chat-message-user" : "ai-chat-message-assistant",
            error ? "ai-chat-message-error" : "",
        ].filter(Boolean).join(" ");

        const avatar = document.createElement("div");
        avatar.className = "ai-chat-avatar";
        avatar.textContent = role === "user" ? "You" : "AI";

        const bubble = document.createElement("div");
        bubble.className = "ai-chat-bubble";

        const sender = document.createElement("strong");
        sender.textContent = role === "user"
            ? "You"
            : error
            ? "AI Assistant Error"
            : "AI Data Assistant";

        const paragraph = document.createElement("p");
        paragraph.textContent = text;

        bubble.append(sender, paragraph);
        article.append(avatar, bubble);
        return article;
    }

    function renderTable(container, tableData) {
        const rows = Array.isArray(tableData?.rows) ? tableData.rows : [];
        const columns = Array.isArray(tableData?.columns)
            ? tableData.columns
            : rows.length
            ? Object.keys(rows[0])
            : [];

        if (!rows.length || !columns.length) {
            return;
        }

        const wrapper = document.createElement("div");
        wrapper.className = "ai-result-table-wrapper";

        const table = document.createElement("table");
        table.className = "ai-result-table";

        const head = document.createElement("thead");
        const headRow = document.createElement("tr");

        columns.forEach((column) => {
            const th = document.createElement("th");
            th.textContent = column;
            headRow.appendChild(th);
        });

        head.appendChild(headRow);

        const body = document.createElement("tbody");
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

        table.append(head, body);
        wrapper.appendChild(table);
        container.appendChild(wrapper);
    }

    function renderList(container, items) {
        if (!Array.isArray(items) || !items.length) {
            return;
        }

        const list = document.createElement("ul");
        list.className = "ai-result-list";

        items.forEach((item) => {
            const li = document.createElement("li");
            li.textContent = String(item);
            list.appendChild(li);
        });

        container.appendChild(list);
    }

    function renderChart(container, chart) {
        if (!chart || !Array.isArray(chart.records) || !window.Plotly) {
            return;
        }

        const chartId = `ai-v2-chart-${Date.now()}-${Math.floor(Math.random() * 10000)}`;
        const chartElement = document.createElement("div");
        chartElement.id = chartId;
        chartElement.className = "ai-result-chart";
        container.appendChild(chartElement);

        const xValues = chart.records.map((row) => row[chart.x]);
        const yValues = chart.records.map((row) => row[chart.y]);

        Plotly.newPlot(
            chartId,
            [{
                type: chart.type || "bar",
                x: xValues,
                y: yValues,
            }],
            {
                title: chart.title || "AI Generated Chart",
                autosize: true,
                margin: { t: 50, r: 20, b: 90, l: 60 },
                paper_bgcolor: "transparent",
                plot_bgcolor: "transparent",
            },
            {
                responsive: true,
                displaylogo: false,
            }
        );
    }

    function addMessage(text, role = "assistant", options = {}) {
        const article = createMessage(text, role, Boolean(options.error));
        const bubble = article.querySelector(".ai-chat-bubble");

        if (options.responseType === "table") {
            renderTable(bubble, options.data);
        }

        if (options.responseType === "list") {
            renderList(bubble, options.data?.items || []);
        }

        if (options.responseType === "chart") {
            renderChart(bubble, options.data?.chart);
            renderTable(bubble, options.data?.table);
        }

        if (Array.isArray(options.suggestions) && options.suggestions.length) {
            const suggestions = document.createElement("div");
            suggestions.className = "ai-inline-suggestions";

            options.suggestions.slice(0, 4).forEach((question) => {
                const button = document.createElement("button");
                button.type = "button";
                button.textContent = question;
                button.addEventListener("click", () => ask(question));
                suggestions.appendChild(button);
            });

            bubble.appendChild(suggestions);
        }

        elements.messages.appendChild(article);

        if (options.save !== false) {
            saveHistory();
        }

        scrollToBottom();
    }

    function addTyping() {
        removeTyping();

        const wrapper = document.createElement("article");
        wrapper.id = "aiTypingIndicator";
        wrapper.className = "ai-chat-message ai-chat-message-assistant ai-typing-message";
        wrapper.innerHTML = `
            <div class="ai-chat-avatar">AI</div>
            <div class="ai-typing-bubble">
                <span class="ai-typing-dot"></span>
                <span class="ai-typing-dot"></span>
                <span class="ai-typing-dot"></span>
            </div>
        `;
        elements.messages.appendChild(wrapper);
        scrollToBottom();
    }

    function removeTyping() {
        document.getElementById("aiTypingIndicator")?.remove();
    }

    function serialiseHistory() {
        return Array.from(elements.messages.querySelectorAll(".ai-chat-message:not(.ai-typing-message)"))
            .map((message) => ({
                role: message.classList.contains("ai-chat-message-user") ? "user" : "assistant",
                text: message.querySelector(".ai-chat-bubble p")?.textContent || "",
                error: message.classList.contains("ai-chat-message-error"),
            }));
    }

    function saveHistory() {
        try {
            localStorage.setItem(storageKey, JSON.stringify(serialiseHistory()));
        } catch (error) {
            console.warn("Could not save AI chat history.", error);
        }
    }

    function restoreHistory() {
        try {
            const saved = JSON.parse(localStorage.getItem(storageKey) || "[]");
            if (!Array.isArray(saved) || !saved.length) {
                return;
            }

            elements.messages.innerHTML = "";
            saved.forEach((item) => {
                addMessage(item.text, item.role, {
                    error: Boolean(item.error),
                    save: false,
                });
            });
            scrollToBottom(false);
        } catch (error) {
            console.warn("Could not restore AI chat history.", error);
        }
    }

    function clearHistory() {
        if (!window.confirm("Clear the AI assistant conversation?")) {
            return;
        }

        localStorage.removeItem(storageKey);
        elements.messages.innerHTML = "";
        addMessage(`Chat cleared. I am ready to analyze ${datasetName}.`);
    }

    function exportHistory() {
        const lines = serialiseHistory().map((item) => {
            const label = item.role === "user" ? "You" : "AI Data Assistant";
            return `${label}\n${item.text}`;
        });

        const blob = new Blob(
            [`AI BI Platform 2.0 Chat Export\nDataset: ${datasetName}\n\n${lines.join("\n\n")}`],
            { type: "text/plain;charset=utf-8" }
        );

        const url = URL.createObjectURL(blob);
        const anchor = document.createElement("a");
        anchor.href = url;
        anchor.download = `ai-chat-${datasetName.replace(/[^a-z0-9]+/gi, "-").toLowerCase()}.txt`;
        document.body.appendChild(anchor);
        anchor.click();
        anchor.remove();
        URL.revokeObjectURL(url);
    }

    async function ask(question) {
        const cleaned = String(question || "").trim();
        if (!cleaned || busy) {
            return;
        }

        addMessage(cleaned, "user");
        elements.input.value = "";
        resizeInput();
        setBusy(true);
        addTyping();

        try {
            const response = await fetch(endpoint, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                body: JSON.stringify({
                    question: cleaned,
                    filename: datasetName,
                }),
            });

            const payload = await response.json().catch(() => ({}));
            removeTyping();

            if (!response.ok || payload.success === false) {
                addMessage(
                    payload.answer || `Request failed with status ${response.status}.`,
                    "assistant",
                    { error: true }
                );
                return;
            }

            addMessage(
                payload.answer || "No response was returned.",
                "assistant",
                {
                    responseType: payload.response_type || "text",
                    data: payload.data || {},
                    suggestions: payload.suggestions || [],
                }
            );
        } catch (error) {
            removeTyping();
            addMessage(
                "I could not connect to the AI assistant service. Verify that Flask is running and /ai/chat is registered.",
                "assistant",
                { error: true }
            );
            console.error(error);
        } finally {
            setBusy(false);
            elements.input.focus();
        }
    }

    elements.launcher.addEventListener("click", () => {
        elements.panel.classList.contains("active") ? closePanel() : openPanel();
    });

    elements.close?.addEventListener("click", closePanel);
    elements.minimize?.addEventListener("click", toggleMinimize);
    elements.clear?.addEventListener("click", clearHistory);
    elements.export?.addEventListener("click", exportHistory);

    elements.form.addEventListener("submit", (event) => {
        event.preventDefault();
        ask(elements.input.value);
    });

    elements.input.addEventListener("input", resizeInput);
    elements.input.addEventListener("keydown", (event) => {
        if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            elements.form.requestSubmit();
        }
    });

    elements.prompts.forEach((button) => {
        button.addEventListener("click", () => {
            openPanel();
            ask(button.dataset.aiQuestion || "");
        });
    });

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && elements.panel.classList.contains("active")) {
            closePanel();
        }
    });

    restoreHistory();
    resizeInput();
});
