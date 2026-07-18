(() => {
    "use strict";

    const root = document.documentElement;
    const sidebar = document.getElementById("appSidebar");
    const sidebarOverlay = document.getElementById("sidebarOverlay");
    const commandPalette = document.getElementById("commandPalette");
    const commandInput = document.getElementById("commandPaletteInput");
    const commandEmpty = document.getElementById("commandPaletteEmpty");
    const notificationPanel = document.getElementById("notificationPanel");
    const userMenuDropdown = document.getElementById("userMenuDropdown");

    function showToast(message, type = "success") {
        const container = document.getElementById("globalToastContainer");

        if (!container) {
            return;
        }

        const toast = document.createElement("div");
        toast.className = `global-toast ${type}`;
        toast.textContent = message;
        container.appendChild(toast);

        window.setTimeout(() => {
            toast.remove();
        }, 3200);
    }

    window.showGlobalToast = showToast;

    function setTheme(theme) {
        root.dataset.theme = theme;
        localStorage.setItem("ai_bi_theme", theme);

        const button = document.getElementById("themeToggleButton");

        if (button) {
            button.textContent = theme === "dark" ? "☀️" : "🌙";
        }
    }

    setTheme(localStorage.getItem("ai_bi_theme") || "light");

    document.getElementById("themeToggleButton")?.addEventListener(
        "click",
        () => {
            setTheme(root.dataset.theme === "dark" ? "light" : "dark");
        }
    );

    function openSidebar() {
        sidebar?.classList.add("open");
        sidebarOverlay?.classList.add("open");
    }

    function closeSidebar() {
        sidebar?.classList.remove("open");
        sidebarOverlay?.classList.remove("open");
    }

    document.getElementById("sidebarOpenButton")?.addEventListener(
        "click",
        openSidebar
    );

    document.getElementById("sidebarCloseButton")?.addEventListener(
        "click",
        closeSidebar
    );

    sidebarOverlay?.addEventListener("click", closeSidebar);

    function filterCommands() {
        const term = (commandInput?.value || "").trim().toLowerCase();
        const items = document.querySelectorAll("[data-command-item]");
        let visibleCount = 0;

        items.forEach(item => {
            const matches = !term || item.textContent.toLowerCase().includes(term);
            item.style.display = matches ? "" : "none";

            if (matches) {
                visibleCount += 1;
            }
        });

        if (commandEmpty) {
            commandEmpty.style.display = visibleCount ? "none" : "block";
        }
    }

    function openCommandPalette() {
        commandPalette?.classList.add("open");
        commandPalette?.setAttribute("aria-hidden", "false");

        if (commandInput) {
            commandInput.value = "";
            filterCommands();
            window.setTimeout(() => commandInput.focus(), 30);
        }
    }

    function closeCommandPalette() {
        commandPalette?.classList.remove("open");
        commandPalette?.setAttribute("aria-hidden", "true");
    }

    document.querySelectorAll("[data-open-command-palette]").forEach(button => {
        button.addEventListener("click", openCommandPalette);
    });

    commandInput?.addEventListener("input", filterCommands);

    commandPalette
        ?.querySelector(".command-palette-backdrop")
        ?.addEventListener("click", closeCommandPalette);

    document.addEventListener("keydown", event => {
        if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
            event.preventDefault();
            openCommandPalette();
        }

        if (event.key === "Escape") {
            closeCommandPalette();
            closeSidebar();
            notificationPanel?.classList.remove("open");
            userMenuDropdown?.classList.remove("open");
        }
    });

    document.getElementById("userMenuButton")?.addEventListener(
        "click",
        event => {
            event.stopPropagation();
            userMenuDropdown?.classList.toggle("open");
        }
    );

    document.addEventListener("click", event => {
        if (!event.target.closest(".global-user-menu")) {
            userMenuDropdown?.classList.remove("open");
        }
    });

    async function requestJson(url, options = {}) {
        const response = await fetch(url, {
            ...options,
            headers: {
                "Content-Type": "application/json",
                ...(options.headers || {})
            }
        });

        const result = await response.json();

        if (!response.ok || !result.success) {
            throw new Error(result.message || "Request failed.");
        }

        return result;
    }

    async function loadNotifications() {
        const content = document.getElementById("notificationPanelContent");
        const badge = document.getElementById("notificationBadge");

        if (!content) {
            return;
        }

        content.innerHTML =
            '<div class="notification-panel-loading">Loading notifications...</div>';

        try {
            const result = await requestJson("/api/notifications");
            const notifications = Array.isArray(result.notifications)
                ? result.notifications
                : [];

            const unreadCount = notifications.filter(item => !item.is_read).length;

            if (badge) {
                badge.textContent = unreadCount;
                badge.style.display = unreadCount ? "block" : "none";
            }

            if (!notifications.length) {
                content.innerHTML =
                    '<div class="notification-panel-empty">No notifications.</div>';
                return;
            }

            content.innerHTML = "";

            notifications.forEach(notification => {
                const button = document.createElement("button");
                button.type = "button";
                button.className =
                    "notification-panel-item" +
                    (notification.is_read ? "" : " unread");

                const title = document.createElement("strong");
                title.textContent = notification.title;

                const message = document.createElement("span");
                message.textContent = notification.message;

                const created = document.createElement("small");
                created.textContent = notification.created_at;

                button.appendChild(title);
                button.appendChild(message);
                button.appendChild(created);

                button.addEventListener("click", async () => {
                    if (notification.is_read) {
                        return;
                    }

                    try {
                        await requestJson(
                            `/api/notifications/${notification.id}/read`,
                            {
                                method: "POST",
                                body: JSON.stringify({})
                            }
                        );

                        notification.is_read = 1;
                        button.classList.remove("unread");
                        loadNotifications();
                    } catch (error) {
                        showToast(error.message, "error");
                    }
                });

                content.appendChild(button);
            });
        } catch (error) {
            content.innerHTML =
                `<div class="notification-panel-empty">${error.message}</div>`;
        }
    }

    document.getElementById("notificationPanelButton")?.addEventListener(
        "click",
        () => {
            notificationPanel?.classList.add("open");
            notificationPanel?.setAttribute("aria-hidden", "false");
            loadNotifications();
        }
    );

    document.getElementById("closeNotificationPanelButton")?.addEventListener(
        "click",
        () => {
            notificationPanel?.classList.remove("open");
            notificationPanel?.setAttribute("aria-hidden", "true");
        }
    );

    if (document.getElementById("notificationBadge")) {
        loadNotifications();
    }
})();
/* =========================================================
   COMMAND PALETTE AUTO-CLOSE FIX
   ========================================================= */

document.addEventListener("DOMContentLoaded", function () {
    const paletteSelectors = [
        "#commandPalette",
        "#command-palette",
        ".command-palette",
        ".command-palette-overlay",
        ".command-overlay",
        ".palette-overlay",
        "[data-command-palette]"
    ];

    function getCommandPaletteElements() {
        const elements = [];

        paletteSelectors.forEach(function (selector) {
            document.querySelectorAll(selector).forEach(function (element) {
                if (!elements.includes(element)) {
                    elements.push(element);
                }
            });
        });

        return elements;
    }

    function closeCommandPalette() {
        const palettes = getCommandPaletteElements();

        palettes.forEach(function (palette) {
            palette.classList.remove(
                "active",
                "open",
                "show",
                "visible",
                "is-open"
            );

            palette.setAttribute("aria-hidden", "true");

            // Hide only palette/overlay elements
            if (
                palette.matches(
                    ".command-palette-overlay, " +
                    ".command-overlay, " +
                    ".palette-overlay"
                )
            ) {
                palette.style.display = "none";
            }
        });

        document.body.classList.remove(
            "command-palette-open",
            "palette-open",
            "modal-open",
            "no-scroll",
            "overflow-hidden"
        );

        document.documentElement.classList.remove(
            "command-palette-open",
            "palette-open",
            "modal-open",
            "no-scroll",
            "overflow-hidden"
        );

        document.body.style.overflow = "";
        document.documentElement.style.overflow = "";
    }

    // Always close the palette when a page finishes loading
    closeCommandPalette();

    // Close before navigating through any normal link
    document.addEventListener("click", function (event) {
        const link = event.target.closest("a[href]");

        if (!link) {
            return;
        }

        const href = link.getAttribute("href");

        if (
            !href ||
            href === "#" ||
            href.startsWith("javascript:")
        ) {
            return;
        }

        closeCommandPalette();
    });

    // Close when a command-palette result is selected
    document.addEventListener("click", function (event) {
        const commandItem = event.target.closest(
            ".command-item, " +
            ".command-result, " +
            ".palette-item, " +
            "[data-command-item]"
        );

        if (commandItem) {
            closeCommandPalette();
        }
    });

    // Close using Escape
    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape") {
            closeCommandPalette();
        }
    });

    // Close when returning through browser back/forward navigation
    window.addEventListener("pageshow", function () {
        closeCommandPalette();
    });

    // Make the function available to other scripts
    window.closeCommandPalette = closeCommandPalette;
});