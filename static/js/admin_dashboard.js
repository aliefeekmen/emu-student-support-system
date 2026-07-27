const elements = {
    userCount: document.querySelector(
        "#admin-user-count"
    ),

    questionCount: document.querySelector(
        "#admin-question-count"
    ),

    answerCount: document.querySelector(
        "#admin-answer-count"
    ),

    categoryCount: document.querySelector(
        "#admin-category-count"
    ),

    knowledgeCount: document.querySelector(
        "#admin-knowledge-count"
    ),

    openCount: document.querySelector(
        "#admin-open-count"
    ),

    assignedCount: document.querySelector(
        "#admin-assigned-count"
    ),

    answeredCount: document.querySelector(
        "#admin-answered-count"
    ),

    closedCount: document.querySelector(
        "#admin-closed-count"
    ),

    userTable: document.querySelector(
        "#admin-user-table"
    ),

    userTableCount: document.querySelector(
        "#admin-user-table-count"
    ),

    refreshButton: document.querySelector(
        "#refresh-admin"
    ),

    message: document.querySelector(
        "#admin-message"
    ),
};

function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

function formatDate(value) {
    if (!value) {
        return "-";
    }

    const date = new Date(
        value.replace(" ", "T") + "Z"
    );

    if (Number.isNaN(date.getTime())) {
        return value;
    }

    return date.toLocaleString();
}

async function apiRequest(url) {
    const response = await fetch(url);

    let data = null;

    try {
        data = await response.json();
    } catch {
        data = null;
    }

    if (!response.ok) {
        throw new Error(
            data?.detail
            || "The request could not be completed."
        );
    }

    return data;
}

async function loadOverview() {
    const overview = await apiRequest(
        "/admin/overview"
    );

    elements.userCount.textContent =
        overview.users;

    elements.questionCount.textContent =
        overview.questions.total;

    elements.answerCount.textContent =
        overview.answers;

    elements.categoryCount.textContent =
        overview.categories;

    elements.knowledgeCount.textContent =
        overview.knowledge_entries;

    elements.openCount.textContent =
        overview.questions.open;

    elements.assignedCount.textContent =
        overview.questions.assigned;

    elements.answeredCount.textContent =
        overview.questions.answered;

    elements.closedCount.textContent =
        overview.questions.closed;
}

async function loadUsers() {
    const users = await apiRequest(
        "/admin/users"
    );

    elements.userTableCount.textContent =
        `${users.length} users`;

    if (users.length === 0) {
        elements.userTable.innerHTML = `
            <tr>
                <td colspan="7">
                    No users found.
                </td>
            </tr>
        `;

        return;
    }

    elements.userTable.innerHTML = users
        .map(
            (user) => `
                <tr>
                    <td>${user.id}</td>

                    <td>
                        ${escapeHtml(
                            user.university_id || "-"
                        )}
                    </td>

                    <td>
                        ${escapeHtml(user.full_name)}
                    </td>

                    <td>
                        ${escapeHtml(user.email)}
                    </td>

                    <td>
                        <span
                            class="role-badge ${escapeHtml(
                                user.role
                            )}"
                        >
                            ${escapeHtml(user.role)}
                        </span>
                    </td>

                    <td>
                        <span
                            class="account-status ${
                                user.is_active
                                    ? "active"
                                    : "inactive"
                            }"
                        >
                            ${
                                user.is_active
                                    ? "Active"
                                    : "Inactive"
                            }
                        </span>
                    </td>

                    <td>
                        ${escapeHtml(
                            formatDate(user.created_at)
                        )}
                    </td>
                </tr>
            `
        )
        .join("");
}

async function loadAdminDashboard() {
    elements.refreshButton.disabled = true;
    showMessage("Refreshing system data...");

    try {
        await Promise.all([
            loadOverview(),
            loadUsers(),
        ]);

        showMessage(
            "Dashboard data updated successfully."
        );
    } catch (error) {
        showMessage(error.message, true);
    } finally {
        elements.refreshButton.disabled = false;
    }
}

function showMessage(
    message,
    isError = false
) {
    elements.message.hidden = false;
    elements.message.textContent = message;

    elements.message.style.color =
        isError ? "#d83b4f" : "#158657";

    window.clearTimeout(showMessage.timeout);

    showMessage.timeout = window.setTimeout(
        () => {
            elements.message.hidden = true;
        },
        3000
    );
}

elements.refreshButton.addEventListener(
    "click",
    loadAdminDashboard
);

loadAdminDashboard();