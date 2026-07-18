(() => {
    "use strict";

    const config =
        window.enterpriseAIConfig || {};

    async function requestJson(
        url,
        options = {}
    ) {
        const response =
            await fetch(
                url,
                {
                    ...options,
                    headers: {
                        "Content-Type":
                            "application/json",
                        ...(options.headers || {})
                    }
                }
            );

        const result =
            await response.json();

        if (!response.ok || !result.success) {
            throw new Error(
                result.message
                || "Request failed."
            );
        }

        return result;
    }


    document.getElementById(
        "narrationForm"
    )?.addEventListener(
        "submit",
        async event => {
            event.preventDefault();

            const metricColumn =
                document.getElementById(
                    "narrationMetric"
                ).value;

            const target =
                document.getElementById(
                    "narrationResult"
                );

            target.textContent =
                "Generating narration...";

            try {
                const result =
                    await requestJson(
                        `/api/enterprise-ai/${encodeURIComponent(config.filename)}/narration`,
                        {
                            method: "POST",
                            body:
                                JSON.stringify({
                                    metric_column:
                                        metricColumn
                                })
                        }
                    );

                target.textContent =
                    result.narration;

            } catch (error) {
                target.textContent =
                    error.message;
            }
        }
    );


    document.getElementById(
        "whatIfForm"
    )?.addEventListener(
        "submit",
        async event => {
            event.preventDefault();

            const resultBox =
                document.getElementById(
                    "whatIfResult"
                );

            try {
                const result =
                    await requestJson(
                        `/api/enterprise-ai/${encodeURIComponent(config.filename)}/what-if`,
                        {
                            method: "POST",
                            body:
                                JSON.stringify({
                                    metric_column:
                                        document.getElementById(
                                            "whatIfMetric"
                                        ).value,

                                    change_percent:
                                        Number(
                                            document.getElementById(
                                                "whatIfPercent"
                                            ).value
                                        )
                                })
                        }
                    );

                resultBox.textContent =
                    result.summary;

            } catch (error) {
                resultBox.textContent =
                    error.message;
            }
        }
    );


    document.getElementById(
        "scenarioForm"
    )?.addEventListener(
        "submit",
        async event => {
            event.preventDefault();

            try {
                const result =
                    await requestJson(
                        `/api/enterprise-ai/${encodeURIComponent(config.filename)}/scenarios`,
                        {
                            method: "POST",
                            body:
                                JSON.stringify({
                                    metric_column:
                                        document.getElementById(
                                            "scenarioMetric"
                                        ).value,

                                    optimistic_percent:
                                        Number(
                                            document.getElementById(
                                                "optimisticPercent"
                                            ).value
                                        ),

                                    expected_percent:
                                        Number(
                                            document.getElementById(
                                                "expectedPercent"
                                            ).value
                                        ),

                                    pessimistic_percent:
                                        Number(
                                            document.getElementById(
                                                "pessimisticPercent"
                                            ).value
                                        )
                                })
                        }
                    );

                Plotly.newPlot(
                    "scenarioChart",
                    [
                        {
                            type: "bar",
                            x:
                                result.scenarios.map(
                                    item => item.name
                                ),

                            y:
                                result.scenarios.map(
                                    item =>
                                        item.projected_total
                                ),

                            text:
                                result.scenarios.map(
                                    item =>
                                        item.projected_total
                                            .toLocaleString()
                                ),

                            textposition:
                                "auto"
                        }
                    ],
                    {
                        title:
                            `${result.metric_column} Scenario Comparison`,

                        template:
                            "plotly_white",

                        margin: {
                            l: 60,
                            r: 20,
                            t: 60,
                            b: 50
                        }
                    },
                    {
                        responsive: true
                    }
                );

            } catch (error) {
                window.alert(
                    error.message
                );
            }
        }
    );


    document.getElementById(
        "goalForm"
    )?.addEventListener(
        "submit",
        async event => {
            event.preventDefault();

            try {
                await requestJson(
                    `/api/enterprise-ai/${encodeURIComponent(config.filename)}/goals`,
                    {
                        method: "POST",
                        body:
                            JSON.stringify({
                                goal_name:
                                    document.getElementById(
                                        "goalName"
                                    ).value,

                                metric_column:
                                    document.getElementById(
                                        "goalMetric"
                                    ).value,

                                current_value:
                                    Number(
                                        document.getElementById(
                                            "goalCurrent"
                                        ).value
                                    ),

                                target_value:
                                    Number(
                                        document.getElementById(
                                            "goalTarget"
                                        ).value
                                    )
                            })
                    }
                );

                window.location.reload();

            } catch (error) {
                window.alert(
                    error.message
                );
            }
        }
    );


    document.getElementById(
        "scheduleForm"
    )?.addEventListener(
        "submit",
        async event => {
            event.preventDefault();

            try {
                const result =
                    await requestJson(
                        "/api/enterprise-ai/schedules",
                        {
                            method: "POST",
                            body:
                                JSON.stringify({
                                    filename:
                                        config.filename,

                                    report_name:
                                        document.getElementById(
                                            "scheduleName"
                                        ).value,

                                    frequency:
                                        document.getElementById(
                                            "scheduleFrequency"
                                        ).value,

                                    delivery_email:
                                        document.getElementById(
                                            "scheduleEmail"
                                        ).value,

                                    export_format:
                                        document.getElementById(
                                            "scheduleFormat"
                                        ).value
                                })
                        }
                    );

                window.alert(
                    result.message
                );

                window.location.reload();

            } catch (error) {
                window.alert(
                    error.message
                );
            }
        }
    );
})();
