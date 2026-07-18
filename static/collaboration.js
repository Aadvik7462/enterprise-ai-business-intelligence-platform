(() => {
    "use strict";

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


    document
        .querySelectorAll(
            "[data-invitation-action]"
        )
        .forEach(button => {
            button.addEventListener(
                "click",
                async () => {
                    const invitationId =
                        button.dataset
                            .invitationId;

                    const accept =
                        button.dataset
                            .invitationAction
                        === "accept";

                    button.disabled =
                        true;

                    try {
                        await requestJson(
                            `/api/invitations/${invitationId}/respond`,
                            {
                                method: "POST",
                                body:
                                    JSON.stringify({
                                        accept
                                    })
                            }
                        );

                        button
                            .closest(
                                "[data-invitation-id]"
                            )
                            ?.remove();

                    } catch (error) {
                        window.alert(
                            error.message
                        );

                        button.disabled =
                            false;
                    }
                }
            );
        });


    document
        .querySelectorAll(
            "[data-notification-id]"
        )
        .forEach(button => {
            button.addEventListener(
                "click",
                async () => {
                    const notificationId =
                        button.dataset
                            .notificationId;

                    try {
                        await requestJson(
                            `/api/notifications/${notificationId}/read`,
                            {
                                method: "POST",
                                body:
                                    JSON.stringify({})
                            }
                        );

                        button.classList.remove(
                            "unread"
                        );

                    } catch (error) {
                        window.alert(
                            error.message
                        );
                    }
                }
            );
        });
})();
