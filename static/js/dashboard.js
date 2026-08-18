const STAFF_ID = Number(
    document.body.dataset.userId
);
const state = {
    questions: [],
    categories: [],
    selectedQuestionId: null,
    selectedQuestion: null,
    suggestion: "",
    suggestionId: null,
    suggestionUsed: false,
    search: "",
    status: "",
};

const elements = {
    questionList: document.querySelector("#question-list"),
    questionSearch: document.querySelector("#question-search"),
    statusFilter: document.querySelector("#status-filter"),

    newCount: document.querySelector("#new-count"),
    pendingCount: document.querySelector("#pending-count"),
    answeredCount: document.querySelector("#answered-count"),
    pendingNavCount: document.querySelector("#pending-nav-count"),

    detailStatus: document.querySelector("#detail-status"),
    detailCategory: document.querySelector("#detail-category"),
    detailLanguage: document.querySelector("#detail-language"),
    detailDate: document.querySelector("#detail-date"),
    detailSubject: document.querySelector("#detail-subject"),
    detailQuestion: document.querySelector("#detail-question"),
    detailAttachments: document.querySelector(
        "#detail-attachments"
    ),

    categorySelect: document.querySelector(
        "#question-category-select"
    ),
    updateCategoryButton: document.querySelector(
        "#update-category-button"
    ),
    categoryUpdateMessage: document.querySelector(
        "#category-update-message"
    ),

    studentName: document.querySelector("#student-name"),
    studentNumber: document.querySelector("#student-number"),
    assignedStaff: document.querySelector("#assigned-staff"),
    questionNumber: document.querySelector("#question-number"),

    answerText: document.querySelector("#answer-text"),
    answerMessage: document.querySelector("#answer-message"),
    sendAnswerButton: document.querySelector("#send-answer-button"),
    useSuggestionButton: document.querySelector(
        "#use-suggestion-button"
    ),

    similarQuestions: document.querySelector("#similar-questions"),
    aiSuggestion: document.querySelector("#ai-suggestion"),

    themeButton: document.querySelector("#theme-button"),
    languageButton: document.querySelector("#language-button"),
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

function statusLabel(status) {
    const labels = {
        open: "Open",
        assigned: "Assigned",
        answered: "Answered",
        closed: "Closed",
    };

    return labels[status] || status;
}

function statusClass(status) {
    const classes = {
        open: "new",
        assigned: "pending",
        answered: "answered",
        closed: "answered",
    };

    return classes[status] || "";
}

async function apiRequest(url, options = {}) {
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
        const message =
            data?.detail || "The request could not be completed.";

        throw new Error(message);
    }

    return data;
}
function renderCategoryOptions(
    selectedCategoryId = null
) {
    elements.categorySelect.innerHTML = `
        <option value="">
            Select a category
        </option>
    `;

    state.categories.forEach((category) => {
        const option =
            document.createElement("option");

        option.value = category.id;
        option.textContent =
            `${category.name_en} / ${category.name_tr}`;

        elements.categorySelect.appendChild(
            option
        );
    });

    if (selectedCategoryId !== null) {
        elements.categorySelect.value =
            String(selectedCategoryId);
    }
}


async function loadCategories(
    selectedCategoryId = null
) {
    try {
        state.categories = await apiRequest(
            "/categories"
        );

        renderCategoryOptions(
            selectedCategoryId
            ?? state.selectedQuestion?.category.id
            ?? null
        );
    } catch (error) {
        showCategoryMessage(
            error.message,
            true
        );
    }
}

function showCategoryMessage(
    message,
    isError = false,
    target = elements.categoryUpdateMessage
) {
    target.hidden = false;
    target.textContent = message;
    target.style.color =
        isError ? "#d83b4f" : "#158657";
}

async function updateQuestionCategory() {
    if (!state.selectedQuestion) {
        showCategoryMessage(
            "Please select a question first.",
            true
        );

        return;
    }

    const categoryId = Number(
        elements.categorySelect.value
    );

    if (!categoryId) {
        showCategoryMessage(
            "Please select a category.",
            true
        );

        return;
    }

    elements.updateCategoryButton.disabled = true;

    try {
        const result = await apiRequest(
            `/questions/${state.selectedQuestion.id
            }/category`,
            {
                method: "PATCH",
                body: JSON.stringify({
                    category_id: categoryId,
                }),
            }
        );

        state.selectedQuestion.category =
            result.category;

        elements.detailCategory.textContent =
            result.category.name_en;

        const listQuestion =
            state.questions.find(
                (question) =>
                    question.id
                    === state.selectedQuestion.id
            );

        if (listQuestion) {
            listQuestion.category =
                result.category.name_en;
        }

        renderQuestionList();

        showCategoryMessage(
            "Question category updated successfully."
        );
    } catch (error) {
        showCategoryMessage(
            error.message,
            true
        );
    } finally {
        elements.updateCategoryButton.disabled =
            false;
    }
}

async function loadQuestions() {
    elements.questionList.innerHTML = `
        <div class="empty-state">
            Loading questions...
        </div>
    `;

    try {
        state.questions = await apiRequest("/questions");

        updateStatistics();
        renderQuestionList();

        if (
            state.questions.length > 0
            && state.selectedQuestionId === null
        ) {
            await selectQuestion(state.questions[0].id);
        }
    } catch (error) {
        elements.questionList.innerHTML = `
            <div class="empty-state">
                ${escapeHtml(error.message)}
            </div>
        `;
    }
}

function updateStatistics() {
    const openCount = state.questions.filter(
        (question) => question.status === "open"
    ).length;

    const assignedCount = state.questions.filter(
        (question) => question.status === "assigned"
    ).length;

    const answeredCount = state.questions.filter(
        (question) => question.status === "answered"
    ).length;

    elements.newCount.textContent = openCount;
    elements.pendingCount.textContent = assignedCount;
    elements.answeredCount.textContent = answeredCount;
    elements.pendingNavCount.textContent = assignedCount;
}

function filteredQuestions() {
    const searchValue = state.search.trim().toLowerCase();

    return state.questions.filter((question) => {
        const matchesStatus =
            !state.status
            || question.status === state.status;

        const searchableText = [
            question.subject,
            question.question_text,
            question.student_name,
            question.category,
        ]
            .join(" ")
            .toLowerCase();

        const matchesSearch =
            !searchValue
            || searchableText.includes(searchValue);

        return matchesStatus && matchesSearch;
    });
}

function renderQuestionList() {
    const questions = filteredQuestions();

    if (questions.length === 0) {
        elements.questionList.innerHTML = `
            <div class="empty-state">
                No questions match this filter.
            </div>
        `;

        return;
    }

    elements.questionList.innerHTML = questions
        .map((question) => {
            const selected =
                question.id === state.selectedQuestionId;

            return `
                <article
                    class="question-card ${selected ? "selected" : ""}"
                    data-question-id="${question.id}"
                    tabindex="0"
                >
                    <div class="question-meta">
                        <span class="tag">
                            ${escapeHtml(question.category)}
                        </span>

                        <span>
                            ${escapeHtml(formatDate(question.created_at))}
                        </span>
                    </div>

                    <div class="question-title">
                        ${escapeHtml(question.subject)}
                    </div>

                    <div class="question-footer">
                        <span>
                            ${escapeHtml(question.student_name)}
                        </span>

                        <span
                            class="tag ${statusClass(question.status)}"
                        >
                            ${escapeHtml(statusLabel(question.status))}
                        </span>
                    </div>
                </article>
            `;
        })
        .join("");

    document
        .querySelectorAll("[data-question-id]")
        .forEach((card) => {
            const openQuestion = () => {
                selectQuestion(
                    Number(card.dataset.questionId)
                );
            };

            card.addEventListener("click", openQuestion);

            card.addEventListener("keydown", (event) => {
                if (
                    event.key === "Enter"
                    || event.key === " "
                ) {
                    openQuestion();
                }
            });
        });
}

async function loadQuestionAttachments(
    questionId
) {
    elements.detailAttachments.innerHTML =
        "Loading attachments...";

    try {
        const attachments = await apiRequest(
            `/questions/${questionId}/attachments`
        );

        if (attachments.length === 0) {
            elements.detailAttachments.innerHTML =
                "No attachments are available.";

            return;
        }

        elements.detailAttachments.innerHTML =
            attachments
                .map(
                    (attachment) => `
                        <a
                            class="secondary-button"
                            href="${attachment.download_url}"
                        >
                            <i class="ph ph-download-simple"></i>
                            ${escapeHtml(
                        attachment.file_name
                    )}
                        </a>
                    `
                )
                .join("");
    } catch (error) {
        elements.detailAttachments.innerHTML =
            escapeHtml(error.message);
    }
}

async function selectQuestion(questionId) {
    state.selectedQuestionId = questionId;
    renderQuestionList();
    clearMessage();
    elements.categoryUpdateMessage.hidden = true;

    try {
        const question = await apiRequest(
            `/questions/${questionId}`
        );

        state.selectedQuestion = question;
        displayQuestion(question);

        await Promise.all([
            loadSimilarQuestions(question),
            loadQuestionAttachments(question.id),
        ]);
    } catch (error) {
        showMessage(error.message, true);
    }
}

function displayQuestion(question) {
    elements.detailStatus.textContent =
        statusLabel(question.status);

    elements.detailStatus.className =
        `tag ${statusClass(question.status)}`;

    elements.detailCategory.textContent =
        question.category.name_en
        || question.category.name_tr;

    renderCategoryOptions(
        question.category.id
    );

    elements.detailLanguage.textContent =
        question.language.toUpperCase();

    elements.detailDate.textContent =
        formatDate(question.created_at);

    elements.detailSubject.textContent =
        question.subject;

    elements.detailQuestion.textContent =
        question.question_text;

    elements.studentName.textContent =
        question.student_name;

    elements.studentNumber.textContent =
        question.student_number || "-";

    elements.assignedStaff.textContent =
        question.assigned_staff || "Not assigned";

    elements.questionNumber.textContent =
        `#Q-${question.id}`;

    const latestAnswer =
        question.answers.length > 0
            ? question.answers[
            question.answers.length - 1
            ]
            : null;

    if (latestAnswer) {
        elements.answerText.value =
            latestAnswer.answer_text;

        elements.answerText.disabled = true;
        elements.sendAnswerButton.disabled = true;
        elements.sendAnswerButton.textContent = "Answered";
    } else {
        elements.answerText.value = "";
        elements.answerText.disabled = false;
        elements.sendAnswerButton.disabled = false;
        elements.sendAnswerButton.innerHTML = `
            <i class="ph ph-paper-plane-tilt"></i>
            Send Answer
        `;
    }
}

async function loadSimilarQuestions(question) {
    if (["answered", "closed"].includes(question.status)) {
        state.suggestion = "";
        state.suggestionId = null;
        state.suggestionUsed = false;
        elements.similarQuestions.innerHTML = `
            <div class="empty-state">
                This question has already been answered.
            </div>
        `;
        elements.aiSuggestion.textContent =
            "A new suggestion is not generated for an answered question.";
        return;
    }

    elements.similarQuestions.innerHTML = `
        <div class="empty-state">
            Searching institutional memory...
        </div>
    `;

    state.suggestion = "";
    state.suggestionId = null;
    state.suggestionUsed = false;
    elements.aiSuggestion.textContent =
        "Generating an AI answer suggestion...";

    try {
        const result = await apiRequest(
            `/questions/${question.id}/ai-suggestion`,
            {
                method: "POST",
            }
        );

        if (result.sources.length === 0) {
            elements.similarQuestions.innerHTML = `
                <div class="empty-state">
                    No similar records found.
                </div>
            `;

            elements.aiSuggestion.textContent =
                "No AI suggestion could be generated.";

            return;
        }

        elements.similarQuestions.innerHTML = result.sources
            .map(
                (item) => `
                    <a
                        class="link-item"
                        href="/knowledge/${item.id}"
                        target="_blank"
                    >
                        ${escapeHtml(item.question)}
                    </a>
                `
            )
            .join("");

        state.suggestion = result.suggestion;
        state.suggestionId = result.id;

        elements.aiSuggestion.textContent = result.suggestion;
    } catch (error) {
        elements.similarQuestions.innerHTML = `
            <div class="empty-state">
                ${escapeHtml(error.message)}
            </div>
        `;
        elements.aiSuggestion.textContent = error.message;
    }
}

async function sendAnswer() {
    const question = state.selectedQuestion;

    if (!question) {
        showMessage("Select a question first.", true);
        return;
    }

    const answerText = elements.answerText.value.trim();

    if (answerText.length < 3) {
        showMessage(
            "The answer must contain at least 3 characters.",
            true
        );
        return;
    }

    elements.sendAnswerButton.disabled = true;
    showMessage("Sending answer...");

    try {
        if (question.status === "open") {
            await apiRequest(
                `/questions/${question.id}/assign`,
                {
                    method: "PATCH",
                    body: JSON.stringify({
                        staff_id: STAFF_ID,
                    }),
                }
            );
        }

        await apiRequest(
            `/questions/${question.id}/answers`,
            {
                method: "POST",
                body: JSON.stringify({
                    staff_id: STAFF_ID,
                    answer_text: answerText,
                    used_ai_suggestion:
                        state.suggestionUsed,
                    ai_suggestion_id:
                        state.suggestionUsed
                            ? state.suggestionId
                            : null,
                }),
            }
        );

        showMessage("Answer sent successfully.");
        await loadQuestions();
        await selectQuestion(question.id);
    } catch (error) {
        showMessage(error.message, true);
        elements.sendAnswerButton.disabled = false;
    }
}

function useSuggestion() {
    if (!state.suggestion) {
        showMessage(
            "No institutional suggestion is available.",
            true
        );
        return;
    }

    if (elements.answerText.disabled) {
        showMessage(
            "This question has already been answered.",
            true
        );
        return;
    }

    elements.answerText.value = state.suggestion;
    state.suggestionUsed = true;

    showMessage(
        "Institutional answer added. Review it before sending."
    );
}

function showMessage(message, isError = false) {
    elements.answerMessage.hidden = false;
    elements.answerMessage.textContent = message;
    elements.answerMessage.style.color =
        isError ? "#d83b4f" : "#158657";
}

function clearMessage() {
    elements.answerMessage.hidden = true;
    elements.answerMessage.textContent = "";
}

elements.questionSearch.addEventListener(
    "input",
    (event) => {
        state.search = event.target.value;
        renderQuestionList();
    }
);

elements.statusFilter.addEventListener(
    "change",
    (event) => {
        state.status = event.target.value;
        renderQuestionList();
    }
);

document
    .querySelectorAll("[data-status-filter]")
    .forEach((button) => {
        button.addEventListener("click", () => {
            document
                .querySelectorAll("[data-status-filter]")
                .forEach((item) => {
                    item.classList.remove("active");
                });

            button.classList.add("active");
            state.status = button.dataset.statusFilter;
            elements.statusFilter.value = state.status;
            renderQuestionList();
        });
    });

elements.updateCategoryButton.addEventListener(
    "click",
    updateQuestionCategory
);

elements.sendAnswerButton.addEventListener(
    "click",
    sendAnswer
);

elements.useSuggestionButton.addEventListener(
    "click",
    useSuggestion
);

elements.themeButton.addEventListener(
    "click",
    () => {
        document.body.classList.toggle("dark-mode");
    }
);

elements.languageButton.addEventListener(
    "click",
    () => {
        showMessage(
            "Full language switching will be connected "
            + "after the main dashboard flow is completed."
        );
    }
);

Promise.all([
    loadCategories(),
    loadQuestions(),
]);
