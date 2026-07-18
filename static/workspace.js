(() => {
    "use strict";

    const config =
        window.workspacePageConfig || {};

    const workspaceGrid =
        document.getElementById(
            "workspaceGrid"
        );

    const workspaceSearchInput =
        document.getElementById(
            "workspaceSearchInput"
        );

    const workspaceTypeFilter =
        document.getElementById(
            "workspaceTypeFilter"
        );

    const workspaceSortSelect =
        document.getElementById(
            "workspaceSortSelect"
        );

    const workspaceEmptyState =
        document.getElementById(
            "workspaceEmptyState"
        );

    const workspaceAlert =
        document.getElementById(
            "workspaceAlert"
        );

    const workspaceModal =
        document.getElementById(
            "workspaceModal"
        );

    const workspaceModalTitle =
        document.getElementById(
            "workspaceModalTitle"
        );

    const workspaceForm =
        document.getElementById(
            "workspaceForm"
        );

    const workspaceId =
        document.getElementById(
            "workspaceId"
        );

    const workspaceName =
        document.getElementById(
            "workspaceName"
        );

    const workspaceDescription =
        document.getElementById(
            "workspaceDescription"
        );

    const workspaceType =
        document.getElementById(
            "workspaceType"
        );

    const workspaceIsDefault =
        document.getElementById(
            "workspaceIsDefault"
        );

    const saveWorkspaceButton =
        document.getElementById(
            "saveWorkspaceButton"
        );

    const favoritesOnlyToggle =
        document.getElementById(
            "favoritesOnlyToggle"
        );


    function showAlert(
        message,
        type = "success"
    ) {
        if (!workspaceAlert) {
            return;
        }

        workspaceAlert.textContent =
            message;

        workspaceAlert.className =
            "workspace-alert " + type;

        workspaceAlert.style.display =
            "block";

        window.setTimeout(() => {
            workspaceAlert.style.display =
                "none";
        }, 3200);
    }


    function openModal(
        mode = "create",
        data = {}
    ) {
        if (!workspaceModal) {
            return;
        }

        const isEdit =
            mode === "edit";

        workspaceModalTitle.textContent =
            isEdit
                ? "Update Workspace"
                : "Create Workspace";

        saveWorkspaceButton.textContent =
            isEdit
                ? "Save Changes"
                : "Create Workspace";

        workspaceId.value =
            data.id || "";

        workspaceName.value =
            data.name || "";

        workspaceDescription.value =
            data.description || "";

        workspaceType.value =
            data.type || "personal";

        workspaceIsDefault.checked =
            false;

        const checkboxField =
            workspaceIsDefault.closest(
                ".workspace-checkbox-field"
            );

        if (checkboxField) {
            checkboxField.style.display =
                isEdit
                    ? "none"
                    : "flex";
        }

        workspaceModal.classList.add(
            "open"
        );

        workspaceModal.setAttribute(
            "aria-hidden",
            "false"
        );

        window.setTimeout(() => {
            workspaceName.focus();
        }, 50);
    }


    function closeModal() {
        if (!workspaceModal) {
            return;
        }

        workspaceModal.classList.remove(
            "open"
        );

        workspaceModal.setAttribute(
            "aria-hidden",
            "true"
        );

        workspaceForm?.reset();

        if (workspaceId) {
            workspaceId.value = "";
        }
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

        if (!response.ok || !result.success) {
            throw new Error(
                result.message
                || "The request could not be completed."
            );
        }

        return result;
    }


    function applyWorkspaceFilters() {
        if (!workspaceGrid) {
            return;
        }

        const cards = Array.from(
            workspaceGrid.querySelectorAll(
                ".workspace-card"
            )
        );

        const searchTerm =
            (
                workspaceSearchInput?.value
                || ""
            )
                .trim()
                .toLowerCase();

        const typeFilter =
            workspaceTypeFilter?.value
            || "all";

        cards.forEach(card => {
            const matchesSearch =
                !searchTerm
                || (
                    card.dataset
                        .workspaceName
                    || ""
                ).includes(searchTerm);

            const matchesType =
                typeFilter === "all"
                || card.dataset.workspaceType
                    === typeFilter;

            card.style.display =
                matchesSearch
                && matchesType
                    ? ""
                    : "none";
        });

        const visibleCards =
            cards.filter(
                card =>
                    card.style.display
                    !== "none"
            );

        if (workspaceEmptyState) {
            workspaceEmptyState.style.display =
                visibleCards.length
                    ? "none"
                    : "block";
        }
    }


    function sortWorkspaceCards() {
        if (!workspaceGrid) {
            return;
        }

        const cards = Array.from(
            workspaceGrid.querySelectorAll(
                ".workspace-card"
            )
        );

        const sortMode =
            workspaceSortSelect?.value
            || "updated";

        cards.sort(
            (first, second) => {
                if (sortMode === "name") {
                    return (
                        (
                            first.dataset
                                .workspaceName
                            || ""
                        ).localeCompare(
                            second.dataset
                                .workspaceName
                            || ""
                        )
                    );
                }

                if (
                    sortMode ===
                    "dashboards"
                ) {
                    return (
                        Number(
                            second.dataset
                                .dashboardCount
                            || 0
                        )
                        -
                        Number(
                            first.dataset
                                .dashboardCount
                            || 0
                        )
                    );
                }

                return (
                    String(
                        second.dataset
                            .updatedAt
                        || ""
                    )
                    .localeCompare(
                        String(
                            first.dataset
                                .updatedAt
                            || ""
                        )
                    )
                );
            }
        );

        cards.forEach(card => {
            workspaceGrid.appendChild(card);
        });

        applyWorkspaceFilters();
    }


    async function submitWorkspaceForm(
        event
    ) {
        event.preventDefault();

        const id =
            workspaceId.value;

        const payload = {
            name:
                workspaceName.value.trim(),

            description:
                workspaceDescription.value
                    .trim(),

            workspace_type:
                workspaceType.value,

            is_default:
                workspaceIsDefault.checked
        };

        if (!payload.name) {
            showAlert(
                "Workspace name is required.",
                "error"
            );

            return;
        }

        saveWorkspaceButton.disabled =
            true;

        saveWorkspaceButton.textContent =
            id
                ? "Saving..."
                : "Creating...";

        try {
            const url = id
                ? `${config.workspaceBaseUrl}/${id}`
                : config.createWorkspaceApi;

            await requestJson(
                url,
                {
                    method:
                        id
                            ? "PUT"
                            : "POST",

                    body:
                        JSON.stringify(
                            payload
                        )
                }
            );

            closeModal();

            window.location.reload();

        } catch (error) {
            showAlert(
                error.message,
                "error"
            );

        } finally {
            saveWorkspaceButton.disabled =
                false;

            saveWorkspaceButton.textContent =
                id
                    ? "Save Changes"
                    : "Create Workspace";
        }
    }


    async function setDefaultWorkspace(
        id
    ) {
        try {
            await requestJson(
                `${config.workspaceBaseUrl}/${id}/default`,
                {
                    method: "POST",
                    body: JSON.stringify({})
                }
            );

            window.location.reload();

        } catch (error) {
            showAlert(
                error.message,
                "error"
            );
        }
    }


    async function deleteWorkspace(
        id,
        name
    ) {
        const confirmed =
            window.confirm(
                `Delete "${name}" and all dashboards inside it?`
            );

        if (!confirmed) {
            return;
        }

        try {
            await requestJson(
                `${config.workspaceBaseUrl}/${id}`,
                {
                    method: "DELETE"
                }
            );

            window.location.reload();

        } catch (error) {
            showAlert(
                error.message,
                "error"
            );
        }
    }


    async function toggleDashboardFavorite(
        dashboardId,
        button
    ) {
        try {
            const result =
                await requestJson(
                    `${config.dashboardBaseUrl}/${dashboardId}/favorite`,
                    {
                        method: "POST",
                        body: JSON.stringify({})
                    }
                );

            const isFavorite =
                Boolean(
                    result.dashboard
                        ?.is_favorite
                );

            button.classList.toggle(
                "active",
                isFavorite
            );

            const card =
                button.closest(
                    ".saved-dashboard-card"
                );

            if (card) {
                card.dataset.favorite =
                    isFavorite
                        ? "1"
                        : "0";
            }

            filterDashboardFavorites();

        } catch (error) {
            showAlert(
                error.message,
                "error"
            );
        }
    }


    function filterDashboardFavorites() {
        const cards =
            document.querySelectorAll(
                ".saved-dashboard-card"
            );

        const favoritesOnly =
            Boolean(
                favoritesOnlyToggle
                    ?.checked
            );

        let visibleCount = 0;

        cards.forEach(card => {
            const isFavorite =
                card.dataset.favorite === "1";

            const visible =
                !favoritesOnly
                || isFavorite;

            card.style.display =
                visible
                    ? ""
                    : "none";

            if (visible) {
                visibleCount += 1;
            }
        });

        const emptyState =
            document.getElementById(
                "dashboardEmptyState"
            );

        if (emptyState) {
            emptyState.style.display =
                visibleCount
                    ? "none"
                    : "block";
        }
    }


    function openSavedDashboard(
        button
    ) {
        const type =
            button.dataset.dashboardType;

        const filename =
            button.dataset.filename;

        if (!filename) {
            showAlert(
                "The saved dashboard has no dataset file.",
                "error"
            );

            return;
        }

        let target =
            config.executiveBaseUrl
            + encodeURIComponent(
                filename
            );

        if (type === "forecast") {
            target =
                config.forecastBaseUrl
                + encodeURIComponent(
                    filename
                );

        } else if (type === "analytics") {
            target =
                config.analyticsBaseUrl
                + encodeURIComponent(
                    filename
                );

        } else if (type === "preview") {
            target =
                config.previewBaseUrl
                + encodeURIComponent(
                    filename
                );
        }

        window.location.href =
            target;
    }


    document.getElementById(
        "openCreateWorkspaceButton"
    )?.addEventListener(
        "click",
        () => openModal("create")
    );


    document.getElementById(
        "closeWorkspaceModalButton"
    )?.addEventListener(
        "click",
        closeModal
    );


    document.getElementById(
        "cancelWorkspaceButton"
    )?.addEventListener(
        "click",
        closeModal
    );


    workspaceModal
        ?.querySelector(
            ".workspace-modal-backdrop"
        )
        ?.addEventListener(
            "click",
            closeModal
        );


    workspaceForm?.addEventListener(
        "submit",
        submitWorkspaceForm
    );


    workspaceSearchInput
        ?.addEventListener(
            "input",
            applyWorkspaceFilters
        );


    workspaceTypeFilter
        ?.addEventListener(
            "change",
            applyWorkspaceFilters
        );


    workspaceSortSelect
        ?.addEventListener(
            "change",
            sortWorkspaceCards
        );


    favoritesOnlyToggle
        ?.addEventListener(
            "change",
            filterDashboardFavorites
        );


    workspaceGrid?.addEventListener(
        "click",
        event => {
            const button =
                event.target.closest(
                    "[data-action]"
                );

            if (!button) {
                return;
            }

            const action =
                button.dataset.action;

            const id =
                button.dataset.workspaceId;

            if (action === "open") {
    window.location.href =
        `/workspaces/${id}`;

            } else if (
                action === "edit"
            ) {
                openModal(
                    "edit",
                    {
                        id,
                        name:
                            button.dataset
                                .workspaceName,

                        description:
                            button.dataset
                                .workspaceDescription,

                        type:
                            button.dataset
                                .workspaceType
                    }
                );

            } else if (
                action === "default"
            ) {
                setDefaultWorkspace(id);

            } else if (
                action === "delete"
            ) {
                deleteWorkspace(
                    id,
                    button.dataset
                        .workspaceName
                );
            }
        }
    );


    document
        .querySelectorAll(
            ".favorite-dashboard-btn"
        )
        .forEach(button => {
            button.addEventListener(
                "click",
                () => {
                    toggleDashboardFavorite(
                        button.dataset
                            .dashboardId,
                        button
                    );
                }
            );
        });


    document
        .querySelectorAll(
            ".open-saved-dashboard-btn"
        )
        .forEach(button => {
            button.addEventListener(
                "click",
                () => {
                    openSavedDashboard(
                        button
                    );
                }
            );
        });


    document.addEventListener(
        "keydown",
        event => {
            if (
                event.key === "Escape"
                && workspaceModal
                    ?.classList
                    .contains("open")
            ) {
                closeModal();
            }
        }
    );


    sortWorkspaceCards();
    filterDashboardFavorites();
})();
