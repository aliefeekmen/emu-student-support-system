const state = {
    categories: [],
    subcategories: [],
    questions: [],
};

const CURRENT_USER_ID = Number(
    document.body.dataset.userId
);

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

    newCategoryTr: document.querySelector(
        "#admin-new-category-tr"
    ),

    newCategoryEn: document.querySelector(
        "#admin-new-category-en"
    ),

    newCategoryDescription: document.querySelector(
        "#admin-new-category-description"
    ),

    newCategoryUnit: document.querySelector(
        "#admin-new-category-unit"
    ),

    createCategoryButton: document.querySelector(
        "#admin-create-category"
    ),

    categoryMessage: document.querySelector(
        "#admin-category-message"
    ),

    categoryListCount: document.querySelector(
        "#admin-category-list-count"
    ),

    subcategoryCategorySelect: document.querySelector(
        "#admin-subcategory-category"
    ),

    newSubcategoryTr: document.querySelector(
        "#admin-new-subcategory-tr"
    ),

    newSubcategoryEn: document.querySelector(
        "#admin-new-subcategory-en"
    ),

    createSubcategoryButton: document.querySelector(
        "#admin-create-subcategory"
    ),

    subcategoryMessage: document.querySelector(
        "#admin-subcategory-message"
    ),

    questionCategoryTable: document.querySelector(
        "#admin-question-category-table"
    ),

    questionTableCount: document.querySelector(
        "#admin-question-table-count"
    ),

    categoryNav: document.querySelector(
        "#admin-category-nav"
    ),

    categoryManagementSection: document.querySelector(
        "#admin-category-management-section"
    ),

    userNav: document.querySelector(
        "#admin-user-nav"
    ),

    userManagementSection: document.querySelector(
        "#admin-user-management-section"
    ),

    newUserName: document.querySelector(
        "#admin-new-user-name"
    ),

    newUserUniversityId: document.querySelector(
        "#admin-new-user-university-id"
    ),

    newUserEmail: document.querySelector(
        "#admin-new-user-email"
    ),

    newUserPassword: document.querySelector(
        "#admin-new-user-password"
    ),

    newUserRole: document.querySelector(
        "#admin-new-user-role"
    ),

    createUserButton: document.querySelector(
        "#admin-create-user"
    ),

    userMessage: document.querySelector(
        "#admin-user-message"
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

async function apiRequest(
    url,
    options = {}
) {
    const response = await fetch(url, {
        headers: {
            "Content-Type": "application/json",
            ...(options.headers || {}),
        },
        ...options,
    });

    let data = null;

    try {
        data = await response.json();
    } catch {
        data = null;
    }

    if (!response.ok) {
        let message =
            "The request could not be completed.";

        if (typeof data?.detail === "string") {
            message = data.detail;
        } else if (Array.isArray(data?.detail)) {
            message = data.detail
                .map((item) => {
                    const field = Array.isArray(item.loc)
                        ? item.loc[item.loc.length - 1]
                        : "field";

                    return `${field}: ${item.msg}`;
                })
                .join(" | ");
        }

        throw new Error(message);
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
                <td colspan="8">
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
                        <select
                            class="select"
                            data-admin-user-role="${user.id}"
                            ${user.id === CURRENT_USER_ID
                    ? "disabled"
                    : ""
                }
                        >
                            ${userRoleOptions(user.role)}
                        </select>
                    </td>

                    <td>
                        <span
                            class="account-status ${user.is_active
                    ? "active"
                    : "inactive"
                }"
                        >
                            ${user.is_active
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

                    <td>
                        <button
                            class="secondary-button"
                            type="button"
                            data-admin-update-user-role="${user.id}"
                            ${user.id === CURRENT_USER_ID
                    ? "disabled"
                    : ""
                }
                        >
                            Update Role
                        </button>
                    </td>
                </tr>
            `
        )
        .join("");

    document
        .querySelectorAll(
            "[data-admin-update-user-role]"
        )
        .forEach((button) => {
            button.addEventListener(
                "click",
                () => {
                    updateUserRole(
                        Number(
                            button.dataset
                                .adminUpdateUserRole
                        )
                    );
                }
            );
        });
}

function userRoleOptions(selectedRole) {
    return ["student", "staff", "admin"]
        .map(
            (role) => `
                <option
                    value="${role}"
                    ${role === selectedRole
                    ? "selected"
                    : ""
                }
                >
                    ${role.charAt(0).toUpperCase()
                + role.slice(1)}
                </option>
            `
        )
        .join("");
}

async function createUser() {
    const fullName =
        elements.newUserName.value.trim();

    const universityId =
        elements.newUserUniversityId.value.trim();

    const email =
        elements.newUserEmail.value.trim();

    const password =
        elements.newUserPassword.value;

    const role = elements.newUserRole.value;

    if (!fullName || !email || !password) {
        showUserMessage(
            "Full name, email, and password are required.",
            true
        );

        return;
    }

    elements.createUserButton.disabled = true;

    try {
        await apiRequest(
            "/admin/users",
            {
                method: "POST",
                body: JSON.stringify({
                    university_id:
                        universityId || null,
                    full_name: fullName,
                    email,
                    password,
                    role,
                }),
            }
        );

        elements.newUserName.value = "";
        elements.newUserUniversityId.value = "";
        elements.newUserEmail.value = "";
        elements.newUserPassword.value = "";
        elements.newUserRole.value = "student";

        await Promise.all([
            loadUsers(),
            loadOverview(),
        ]);

        showUserMessage(
            "User created successfully."
        );
    } catch (error) {
        showUserMessage(
            error.message,
            true
        );
    } finally {
        elements.createUserButton.disabled = false;
    }
}

async function updateUserRole(userId) {
    const select = document.querySelector(
        `[data-admin-user-role="${userId}"]`
    );

    if (!select) {
        return;
    }

    try {
        await apiRequest(
            `/admin/users/${userId}/role`,
            {
                method: "PATCH",
                body: JSON.stringify({
                    role: select.value,
                }),
            }
        );

        await loadUsers();

        showUserMessage(
            "User role updated successfully."
        );
    } catch (error) {
        showUserMessage(
            error.message,
            true
        );
    }
}

function showUserMessage(
    message,
    isError = false
) {
    elements.userMessage.hidden = false;
    elements.userMessage.textContent = message;
    elements.userMessage.style.color =
        isError ? "#d83b4f" : "#158657";
}

async function loadCategories() {
    const [categories, subcategories] =
        await Promise.all([
            apiRequest("/categories"),
            apiRequest("/subcategories"),
        ]);

    state.categories = categories;
    state.subcategories = subcategories;

    elements.categoryListCount.textContent =
        `${state.categories.length} categories / `
        + `${state.subcategories.length} subcategories`;

    elements.subcategoryCategorySelect.innerHTML = `
        <option value="">
            Select parent category
        </option>
    `;

    state.categories.forEach((category) => {
        const option = document.createElement("option");
        option.value = category.id;
        option.textContent =
            `${category.name_en} / ${category.name_tr}`;
        elements.subcategoryCategorySelect.appendChild(
            option
        );
    });
}

function categoryOptions(
    selectedCategoryId
) {
    return state.categories
        .map(
            (category) => `
                <option
                    value="${category.id}"
                    ${category.id
                    === selectedCategoryId
                    ? "selected"
                    : ""
                }
                >
                    ${escapeHtml(category.name_en)}
                    /
                    ${escapeHtml(category.name_tr)}
                </option>
            `
        )
        .join("");
}

async function loadQuestions() {
    state.questions = await apiRequest(
        "/questions?limit=100"
    );

    elements.questionTableCount.textContent =
        `${state.questions.length} questions`;

    renderQuestionCategoryTable();
}

function renderQuestionCategoryTable() {
    if (state.questions.length === 0) {
        elements.questionCategoryTable.innerHTML = `
            <tr>
                <td colspan="6">
                    No questions found.
                </td>
            </tr>
        `;

        return;
    }

    elements.questionCategoryTable.innerHTML =
        state.questions
            .map(
                (question) => `
                    <tr>
                        <td>${question.id}</td>

                        <td>
                            ${escapeHtml(
                    question.subject
                )}
                        </td>

                        <td>
                            ${escapeHtml(
                    question.student_name
                )}
                        </td>

                        <td>
                            ${escapeHtml(
                    question.category_en
                    || question.category
                )}
                        </td>

                        <td>
                            <select
                                class="select"
                                data-admin-category-select="${question.id
                    }"
                            >
                                ${categoryOptions(
                        question.category_id
                    )}
                            </select>
                        </td>

                        <td>
                            <button
                                class="secondary-button"
                                type="button"
                                data-admin-update-category="${question.id
                    }"
                            >
                                Update
                            </button>
                        </td>
                    </tr>
                `
            )
            .join("");

    document
        .querySelectorAll(
            "[data-admin-update-category]"
        )
        .forEach((button) => {
            button.addEventListener(
                "click",
                () => {
                    updateQuestionCategory(
                        Number(
                            button.dataset
                                .adminUpdateCategory
                        )
                    );
                }
            );
        });
}

async function createCategory() {
    const nameTr =
        elements.newCategoryTr.value.trim();

    const nameEn =
        elements.newCategoryEn.value.trim();

    const description =
        elements.newCategoryDescription.value.trim();

    const responsibleUnit =
        elements.newCategoryUnit.value.trim();

    if (!nameTr || !nameEn) {
        showCategoryMessage(
            "Both Turkish and English category names are required.",
            true
        );

        return;
    }

    elements.createCategoryButton.disabled = true;

    try {
        await apiRequest(
            "/categories",
            {
                method: "POST",
                body: JSON.stringify({
                    name_tr: nameTr,
                    name_en: nameEn,
                    description: description || null,
                    responsible_unit: responsibleUnit || null,
                }),
            }
        );

        elements.newCategoryTr.value = "";
        elements.newCategoryEn.value = "";
        elements.newCategoryDescription.value = "";
        elements.newCategoryUnit.value = "";

        await Promise.all([
            loadCategories(),
            loadOverview(),
        ]);

        renderQuestionCategoryTable();

        showCategoryMessage(
            "Category created successfully."
        );
    } catch (error) {
        showCategoryMessage(
            error.message,
            true
        );
    } finally {
        elements.createCategoryButton.disabled =
            false;
    }
}

async function createSubcategory() {
    const categoryId = Number(
        elements.subcategoryCategorySelect.value
    );
    const nameTr =
        elements.newSubcategoryTr.value.trim();
    const nameEn =
        elements.newSubcategoryEn.value.trim();

    if (!categoryId || !nameTr || !nameEn) {
        showSubcategoryMessage(
            "Parent category and both names are required.",
            true
        );
        return;
    }

    elements.createSubcategoryButton.disabled = true;

    try {
        await apiRequest(
            "/subcategories",
            {
                method: "POST",
                body: JSON.stringify({
                    category_id: categoryId,
                    name_tr: nameTr,
                    name_en: nameEn,
                }),
            }
        );

        elements.newSubcategoryTr.value = "";
        elements.newSubcategoryEn.value = "";
        await loadCategories();
        elements.subcategoryCategorySelect.value =
            String(categoryId);

        showSubcategoryMessage(
            "Subcategory created successfully."
        );
    } catch (error) {
        showSubcategoryMessage(error.message, true);
    } finally {
        elements.createSubcategoryButton.disabled = false;
    }
}

async function updateQuestionCategory(
    questionId
) {
    const select = document.querySelector(
        `[data-admin-category-select="${questionId
        }"]`
    );

    const categoryId = Number(
        select?.value
    );

    if (!categoryId) {
        showMessage(
            "Please select a valid category.",
            true
        );

        return;
    }

    try {
        await apiRequest(
            `/questions/${questionId}/category`,
            {
                method: "PATCH",
                body: JSON.stringify({
                    category_id: categoryId,
                }),
            }
        );

        await loadQuestions();

        showMessage(
            `Question #${questionId} category updated successfully.`
        );
    } catch (error) {
        showMessage(
            error.message,
            true
        );
    }
}

async function loadAdminDashboard() {
    elements.refreshButton.disabled = true;
    showMessage("Refreshing system data...");

    try {
        await Promise.all([
            loadOverview(),
            loadUsers(),
            loadCategories(),
        ]);

        await loadQuestions();

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

function showCategoryMessage(
    message,
    isError = false
) {
    elements.categoryMessage.hidden = false;
    elements.categoryMessage.textContent =
        message;

    elements.categoryMessage.style.color =
        isError ? "#d83b4f" : "#158657";
}

function showSubcategoryMessage(
    message,
    isError = false
) {
    elements.subcategoryMessage.hidden = false;
    elements.subcategoryMessage.textContent = message;
    elements.subcategoryMessage.style.color =
        isError ? "#d83b4f" : "#158657";
}

elements.refreshButton.addEventListener(
    "click",
    loadAdminDashboard
);

elements.createCategoryButton.addEventListener(
    "click",
    createCategory
);

elements.createSubcategoryButton.addEventListener(
    "click",
    createSubcategory
);

elements.createUserButton.addEventListener(
    "click",
    createUser
);

elements.userNav.addEventListener(
    "click",
    () => {
        document
            .querySelectorAll(".navigation .nav-item")
            .forEach((item) => {
                item.classList.remove("active");
            });

        elements.userNav.classList.add("active");

        elements.userManagementSection
            .scrollIntoView({
                behavior: "smooth",
                block: "start",
            });
    }
);

elements.categoryNav.addEventListener(
    "click",
    () => {
        document
            .querySelectorAll(".navigation .nav-item")
            .forEach((item) => {
                item.classList.remove("active");
            });

        elements.categoryNav.classList.add(
            "active"
        );

        elements.categoryManagementSection
            .scrollIntoView({
                behavior: "smooth",
                block: "start",
            });
    }
);

loadAdminDashboard();
