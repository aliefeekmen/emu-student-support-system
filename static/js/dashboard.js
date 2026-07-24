const STAFF_ID = 2;

const state = {
    questions: [],
    selectedQuestionId: null,
    selectedQuestion: null,
    suggestion: "",
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

async function selectQuestion(questionId) {
    state.selectedQuestionId = questionId;
    renderQuestionList();
    clearMessage();

    try {
        const question = await apiRequest(
            `/questions/${questionId}`
        );

        state.selectedQuestion = question;
        displayQuestion(question);
        await loadSimilarQuestions(question);
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

function getSearchKeyword(subject) {
    const ignoredWords = new Set([
        "about",
        "with",
        "from",
        "this",
        "that",
        "question",
        "problem",
        "sorunu",
        "hakkinda",
        "hakkında",
    ]);

    return subject
        .split(/\s+/)
        .map((word) => word.replace(/[^\p{L}\p{N}]/gu, ""))
        .find(
            (word) =>
                word.length >= 4
                && !ignoredWords.has(word.toLowerCase())
        ) || subject;
}

async function loadSimilarQuestions(question) {
    const keyword = getSearchKeyword(question.subject);

    elements.similarQuestions.innerHTML = `
        <div class="empty-state">
            Searching institutional memory...
        </div>
    `;

    state.suggestion = "";

    try {
        const result = await apiRequest(
            `/knowledge?language=${
                encodeURIComponent(question.language)
            }&search=${
                encodeURIComponent(keyword)
            }&limit=3`
        );

        if (result.items.length === 0) {
            elements.similarQuestions.innerHTML = `
                <div class="empty-state">
                    No similar records found.
                </div>
            `;

            elements.aiSuggestion.textContent =
                "AI integration will be added after the "
                + "official train/test split is provided.";

            return;
        }

        elements.similarQuestions.innerHTML = result.items
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

        state.suggestion = result.items[0].answer;

        elements.aiSuggestion.textContent =
            "AI is not enabled yet. Closest institutional "
            + `answer: ${state.suggestion}`;
    } catch (error) {
        elements.similarQuestions.innerHTML = `
            <div class="empty-state">
                ${escapeHtml(error.message)}
            </div>
        `;
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
                    used_ai_suggestion: false,
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

loadQuestions();