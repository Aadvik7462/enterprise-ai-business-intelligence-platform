
"use strict";

document.addEventListener("DOMContentLoaded", () => {
    const config = window.aiSqlConfig || {};

    const elements = {
        form: document.getElementById("aiSqlQuestionForm"),
        question: document.getElementById("aiSqlQuestion"),
        askButton: document.getElementById("aiSqlAskButton"),
        editor: document.getElementById("aiSqlEditor"),
        runButton: document.getElementById("runAiSqlButton"),
        copyButton: document.getElementById("copyAiSqlButton"),
        clearHistory: document.getElementById("clearAiSqlHistory"),
        status: document.getElementById("aiSqlStatus"),
        resultCard: document.getElementById("aiSqlResultCard"),
        table: document.getElementById("aiSqlResultTable"),
        chart: document.getElementById("aiSqlChart"),
        history: document.getElementById("aiSqlHistory"),
        csvButton: document.getElementById("exportAiSqlCsv"),
        excelButton: document.getElementById("exportAiSqlExcel"),
        schemaItems: document.querySelectorAll(".ai-sql-schema-item"),
        exampleButtons: document.querySelectorAll("[data-question]"),
    };

    let currentColumns = [];
    let currentRows = [];
    let busy = false;

    function setBusy(value) {
        busy = value;

        [
            elements.askButton,
            elements.runButton,
        ].forEach((button) => {
            if (button) {
                button.disabled = value;
            }
        });
    }

    function showStatus(message, error = false) {
        elements.status.hidden = false;
        elements.status.textContent = message;
        elements.status.classList.toggle("error", error);
    }

    function hideStatus() {
        elements.status.hidden = true;
        elements.status.textContent = "";
        elements.status.classList.remove("error");
    }

    function escapeCsv(value) {
        const text =
            value === null || value === undefined
                ? ""
                : String(value);

        if (
            text.includes(",") ||
            text.includes('"') ||
            text.includes("\n")
        ) {
            return `"${text.replace(/"/g, '""')}"`;
        }

        return text;
    }

    function renderTable(columns, rows) {
        currentColumns = Array.isArray(columns)
            ? columns
            : [];

        currentRows = Array.isArray(rows)
            ? rows
            : [];

        const head = elements.table.querySelector("thead");
        const body = elements.table.querySelector("tbody");

        head.innerHTML = "";
        body.innerHTML = "";

        if (!currentColumns.length) {
            elements.resultCard.hidden = true;
            return;
        }

        const headerRow = document.createElement("tr");

        currentColumns.forEach((column) => {
            const th = document.createElement("th");
            th.textContent = column;
            headerRow.appendChild(th);
        });

        head.appendChild(headerRow);

        currentRows.forEach((row) => {
            const tr = document.createElement("tr");

            currentColumns.forEach((column) => {
                const td = document.createElement("td");
                const value = row[column];

                td.textContent =
                    value === null || value === undefined
                        ? "—"
                        : String(value);

                tr.appendChild(td);
            });

            body.appendChild(tr);
        });

        elements.resultCard.hidden = false;
    }

    function renderChart(chart) {
        if (
            !chart ||
            !Array.isArray(chart.records) ||
            !chart.records.length ||
            !window.Plotly
        ) {
            elements.chart.hidden = true;
            elements.chart.innerHTML = "";
            return;
        }

        const x = chart.records.map(
            (row) => row[chart.x]
        );

        const y = chart.records.map(
            (row) => row[chart.y]
        );

        let trace;

        if (chart.type === "line") {
            trace = {
                type: "scatter",
                mode: "lines+markers",
                x,
                y,
            };
        } else if (chart.type === "scatter") {
            trace = {
                type: "scatter",
                mode: "markers",
                x,
                y,
            };
        } else {
            trace = {
                type: "bar",
                x,
                y,
            };
        }

        elements.chart.hidden = false;

        Plotly.newPlot(
            elements.chart,
            [trace],
            {
                title: chart.title || "SQL result chart",
                autosize: true,
                margin: {
                    t: 55,
                    r: 20,
                    b: 85,
                    l: 70,
                },
                paper_bgcolor: "transparent",
                plot_bgcolor: "transparent",
            },
            {
                responsive: true,
                displaylogo: false,
            }
        );
    }

    function getHistory() {
        try {
            const parsed = JSON.parse(
                localStorage.getItem(
                    config.storageKey
                ) || "[]"
            );

            return Array.isArray(parsed)
                ? parsed
                : [];
        } catch {
            return [];
        }
    }

    function saveHistory(question, sql) {
        const history = getHistory();

        history.unshift({
            question,
            sql,
            createdAt: new Date().toISOString(),
        });

        localStorage.setItem(
            config.storageKey,
            JSON.stringify(
                history.slice(0, 20)
            )
        );

        renderHistory();
    }

    function renderHistory() {
        const history = getHistory();

        elements.history.innerHTML = "";

        if (!history.length) {
            const empty = document.createElement("p");
            empty.className = "ai-sql-empty-state";
            empty.textContent = "No SQL history yet.";
            elements.history.appendChild(empty);
            return;
        }

        history.forEach((item) => {
            const card = document.createElement("article");
            card.className = "ai-sql-history-item";

            const title = document.createElement("strong");
            title.textContent =
                item.question || "Manual SQL";

            const code = document.createElement("code");
            code.textContent = item.sql;

            card.append(title, code);

            card.addEventListener("click", () => {
                elements.editor.value = item.sql;
                elements.question.value =
                    item.question || "";
                window.scrollTo({
                    top: 0,
                    behavior: "smooth",
                });
            });

            elements.history.appendChild(card);
        });
    }

    async function callEndpoint(endpoint, payload) {
        setBusy(true);
        showStatus("Running query...");

        try {
            const response = await fetch(endpoint, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                body: JSON.stringify(payload),
            });

            const result = await response
                .json()
                .catch(() => ({}));

            if (
                !response.ok ||
                result.success === false
            ) {
                throw new Error(
                    result.answer ||
                    "The SQL request failed."
                );
            }

            hideStatus();

            elements.editor.value =
                result.sql || elements.editor.value;

            renderTable(
                result.columns || [],
                result.rows || []
            );

            renderChart(
                result.chart || {}
            );

            showStatus(
                result.answer ||
                "Query completed successfully."
            );

            return result;
        } catch (error) {
            showStatus(
                error.message ||
                "The SQL request failed.",
                true
            );

            throw error;
        } finally {
            setBusy(false);
        }
    }

    elements.form?.addEventListener("submit", async (event) => {
        event.preventDefault();

        const question =
            elements.question.value.trim();

        if (!question || busy) {
            return;
        }

        try {
            const result = await callEndpoint(
                config.askEndpoint,
                {
                    question,
                    filename: config.filename,
                }
            );

            saveHistory(
                question,
                result.sql
            );
        } catch {
            // Status already displayed.
        }
    });

    elements.runButton?.addEventListener("click", async () => {
        const sql =
            elements.editor.value.trim();

        if (!sql || busy) {
            showStatus(
                "Enter a SQL query first.",
                true
            );
            return;
        }

        try {
            const result = await callEndpoint(
                config.executeEndpoint,
                {
                    sql,
                    filename: config.filename,
                }
            );

            saveHistory(
                "Manual SQL",
                result.sql
            );
        } catch {
            // Status already displayed.
        }
    });

    elements.copyButton?.addEventListener("click", async () => {
        const sql =
            elements.editor.value.trim();

        if (!sql) {
            showStatus(
                "There is no SQL to copy.",
                true
            );
            return;
        }

        try {
            await navigator.clipboard.writeText(sql);
            showStatus("SQL copied to clipboard.");
        } catch {
            showStatus(
                "Could not copy SQL.",
                true
            );
        }
    });

    elements.clearHistory?.addEventListener("click", () => {
        localStorage.removeItem(
            config.storageKey
        );

        renderHistory();
        showStatus("SQL history cleared.");
    });

    elements.exampleButtons.forEach((button) => {
        button.addEventListener("click", () => {
            elements.question.value =
                button.dataset.question || "";

            elements.question.focus();
        });
    });

    elements.schemaItems.forEach((button) => {
        button.addEventListener("click", () => {
            const column =
                button.dataset.column || "";

            const insertion = `"${column.replace(
                /"/g,
                '""'
            )}"`;

            const editor = elements.editor;
            const start = editor.selectionStart;
            const end = editor.selectionEnd;

            editor.value =
                editor.value.slice(0, start)
                + insertion
                + editor.value.slice(end);

            editor.focus();

            editor.selectionStart =
                editor.selectionEnd =
                start + insertion.length;
        });
    });

    elements.csvButton?.addEventListener("click", () => {
        if (!currentColumns.length) {
            return;
        }

        const lines = [
            currentColumns
                .map(escapeCsv)
                .join(","),
            ...currentRows.map((row) =>
                currentColumns
                    .map((column) =>
                        escapeCsv(row[column])
                    )
                    .join(",")
            ),
        ];

        const blob = new Blob(
            [lines.join("\n")],
            {
                type: "text/csv;charset=utf-8",
            }
        );

        const url = URL.createObjectURL(blob);
        const anchor = document.createElement("a");

        anchor.href = url;
        anchor.download = "ai-sql-results.csv";

        document.body.appendChild(anchor);
        anchor.click();
        anchor.remove();

        URL.revokeObjectURL(url);
    });

    elements.excelButton?.addEventListener("click", () => {
        if (
            !currentColumns.length ||
            !window.XLSX
        ) {
            return;
        }

        const worksheet = XLSX.utils.json_to_sheet(
            currentRows,
            {
                header: currentColumns,
            }
        );

        const workbook =
            XLSX.utils.book_new();

        XLSX.utils.book_append_sheet(
            workbook,
            worksheet,
            "SQL Results"
        );

        XLSX.writeFile(
            workbook,
            "ai-sql-results.xlsx"
        );
    });

    renderHistory();
});
