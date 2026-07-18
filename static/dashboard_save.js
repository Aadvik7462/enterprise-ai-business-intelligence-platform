(() => {
    "use strict";

    const modal =
        document.getElementById(
            "saveDashboardModal"
        );

    const openButton =
        document.getElementById(
            "openSaveDashboardButton"
        );

    const closeButton =
        document.getElementById(
            "closeSaveDashboardButton"
        );

    const cancelButton =
        document.getElementById(
            "cancelSaveDashboardButton"
        );

    const form =
        document.getElementById(
            "saveDashboardForm"
        );

    const workspaceSelect =
        document.getElementById(
            "saveDashboardWorkspace"
        );

    const dashboardName =
        document.getElementById(
            "saveDashboardName"
        );

    const dashboardDescription =
        document.getElementById(
            "saveDashboardDescription"
        );

    const submitButton =
        document.getElementById(
            "submitSaveDashboardButton"
        );

    const messageBox =
        document.getElementById(
            "saveDashboardMessage"
        );

    const pageConfig =
        window.dashboardSaveConfig || {};


    function showMessage(
        message,
        type = "success"
    ) {
        if (!messageBox) {
            return;
        }

        messageBox.textContent =
            message;

        messageBox.className =
            "save-dashboard-message "
            + type;

        messageBox.style.display =
            "block";
    }


    function hideMessage() {
        if (!messageBox) {
            return;
        }

        messageBox.style.display =
            "none";
    }


    function openModal() {
        if (!modal) {
            return;
        }

        hideMessage();

        modal.classList.add(
            "open"
        );

        modal.setAttribute(
            "aria-hidden",
            "false"
        );

        if (
            dashboardName
            && !dashboardName.value
        ) {
            dashboardName.value =
                pageConfig.defaultName
                || "Saved Dashboard";
        }

        loadWorkspaces();

        window.setTimeout(() => {
            dashboardName?.focus();
        }, 50);
    }


    function closeModal() {
        if (!modal) {
            return;
        }

        modal.classList.remove(
            "open"
        );

        modal.setAttribute(
            "aria-hidden",
            "true"
        );

        hideMessage();
    }


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

        if (
            !response.ok
            || !result.success
        ) {
            throw new Error(
                result.message
                || "The request failed."
            );
        }

        return result;
    }


    async function loadWorkspaces() {
        if (!workspaceSelect) {
            return;
        }

        workspaceSelect.innerHTML =
            `
            <option value="">
                Loading workspaces...
            </option>
            `;

        workspaceSelect.disabled =
            true;

        try {
            const result =
                await requestJson(
                    "/api/workspaces"
                );

            const workspaces =
                Array.isArray(
                    result.workspaces
                )
                    ? result.workspaces
                    : [];

            workspaceSelect.innerHTML =
                "";

            if (!workspaces.length) {
                workspaceSelect.innerHTML =
                    `
                    <option value="">
                        No workspace available
                    </option>
                    `;

                showMessage(
                    "Create a workspace before saving a dashboard.",
                    "error"
                );

                return;
            }

            workspaces.forEach(
                workspace => {
                    const option =
                        document.createElement(
                            "option"
                        );

                    option.value =
                        workspace.id;

                    option.textContent =
                        workspace.name
                        + (
                            workspace.is_default
                                ? " — Default"
                                : ""
                        );

                    if (
                        workspace.is_default
                    ) {
                        option.selected =
                            true;
                    }

                    workspaceSelect.appendChild(
                        option
                    );
                }
            );

        } catch (error) {
            workspaceSelect.innerHTML =
                `
                <option value="">
                    Unable to load workspaces
                </option>
                `;

            showMessage(
                error.message,
                "error"
            );

        } finally {
            workspaceSelect.disabled =
                false;
        }
    }


    function collectDashboardState() {
        const state = {
            page_url:
                window.location.pathname
                + window.location.search,

            saved_at:
                new Date().toISOString(),

            scroll_position:
                window.scrollY,

            dashboard_type:
                pageConfig.dashboardType
                || "executive",

            filename:
                pageConfig.filename
                || ""
        };

        if (
            typeof window.getCustomDashboardState
            === "function"
        ) {
            try {
                const customState =
                    window
                        .getCustomDashboardState();

                if (
                    customState
                    && typeof customState
                    === "object"
                ) {
                    Object.assign(
                        state,
                        customState
                    );
                }

            } catch (error) {
                console.error(
                    "Unable to collect custom dashboard state:",
                    error
                );
            }
        }

        return state;
    }


    async function saveDashboard(
        event
    ) {
        event.preventDefault();

        hideMessage();

        const workspaceId =
            workspaceSelect?.value;

        const name =
            dashboardName?.value
                .trim();

        const description =
            dashboardDescription?.value
                .trim();

        if (!workspaceId) {
            showMessage(
                "Please select a workspace.",
                "error"
            );

            return;
        }

        if (!name) {
            showMessage(
                "Dashboard name is required.",
                "error"
            );

            return;
        }

        if (!pageConfig.filename) {
            showMessage(
                "Dataset filename is missing.",
                "error"
            );

            return;
        }

        submitButton.disabled =
            true;

        submitButton.textContent =
            "Saving...";

        const payload = {
            name,
            description,

            filename:
                pageConfig.filename,

            dashboard_type:
                pageConfig.dashboardType
                || "executive",

            dashboard_state:
                collectDashboardState(),

            thumbnail:
                ""
        };

        try {
            const result =
                await requestJson(
                    `/api/workspaces/${workspaceId}/dashboards`,
                    {
                        method: "POST",

                        body:
                            JSON.stringify(
                                payload
                            )
                    }
                );

            showMessage(
                result.message
                || "Dashboard saved successfully.",
                "success"
            );

            submitButton.textContent =
                "Saved ✓";

            window.setTimeout(() => {
                closeModal();

                submitButton.textContent =
                    "Save Dashboard";

                form?.reset();
            }, 1400);

        } catch (error) {
            showMessage(
                error.message,
                "error"
            );

            submitButton.textContent =
                "Save Dashboard";

        } finally {
            submitButton.disabled =
                false;
        }
    }


    openButton?.addEventListener(
        "click",
        openModal
    );


    closeButton?.addEventListener(
        "click",
        closeModal
    );


    cancelButton?.addEventListener(
        "click",
        closeModal
    );


    modal
        ?.querySelector(
            ".save-dashboard-backdrop"
        )
        ?.addEventListener(
            "click",
            closeModal
        );


    form?.addEventListener(
        "submit",
        saveDashboard
    );


    document.addEventListener(
        "keydown",
        event => {
            if (
                event.key === "Escape"
                && modal
                    ?.classList
                    .contains("open")
            ) {
                closeModal();
            }
        }
    );
})();