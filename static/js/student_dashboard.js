const STUDENT_ID = 1;

const state = {
    questions: [],
    selectedQuestionId: null,
    search: "",
};

const elements = {
    questionsSection: document.querySelector(
        "#questions-section"
    ),

    newQuestionSection: document.querySelector(
        "#new-question-section"
    ),

    questionList: document.querySelector(
        "#student-question-list"
    ),

    questionSearch: document.querySelector(
        "#student-question-search"
    ),

    totalCount: document.querySelector(
        "#student-total-count"
    ),

    pendingCount: document.querySelector(
        "#student-pending-count"
    ),

    answeredCount: document.querySelector(
        "#student-answered-count"
    ),

    detailStatus: document.querySelector(
        "#student-detail-status"
    ),

    detailCategory: document.querySelector(
        "#student-detail-category"
    ),

    detailDate: document.querySelector(
        "#student-detail-date"
    ),

    detailSubject: document.querySelector(
        "#student-detail-subject"
    ),

    detailQuestion: document.querySelector(
        "#student-detail-question"
    ),

    detailAnswer: document.querySelector(
        "#student-detail-answer"
    ),

    pageMessage: document.querySelector(
        "#student-page-message"
    ),

    openFormButton: document.querySelector(
        "#open-question-form"
    ),

    closeFormButton: document.querySelector(
        "#close-question-form"
    ),

    questionForm: document.querySelector(
        "#new-question-form"
    ),

    categorySelect: document.querySelector(
        "#new-question-category"
    ),

    languageSelect: document.querySelector(
        "#new-question-language"
    ),

    subjectInput: document.querySelector(
        "#new-question-subject"
    ),

    questionInput: document.querySelector(
        "#new-question-text"
    ),

    submitButton: document.querySelector(
        "#submit-question-button"
    ),

    formMessage: document.querySelector(
        "#form-message"
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

function statusLabel(status) {
    const labels = {
        open: "Open",
        assigned: "Under Review",
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
        throw new Error(
            data?.detail
            || "The request could not be completed."
        );
    }

    return data;
}

async function loadCategories() {
    try {
        const categories = await apiRequest("/categories");

        elements.categorySelect.innerHTML = `
            <option value="">
                Select a category
            </option>
        `;

        categories.forEach((category) => {
            const option = document.createElement("option");

            option.value = category.id;
            option.textContent = category.name_en;

            elements.categorySelect.appendChild(option);
        });
    } catch (error) {
        showFormMessage(error.message, true);
    }
}

async function loadStudentQuestions(
    selectNewest = false
) {
    elements.questionList.innerHTML = `
        <div class="empty-state">
            Loading your questions...
        </div>
    `;

    try {
        state.questions = await apiRequest(
            `/students/${STUDENT_ID}/questions`
        );

        updateStatistics();
        renderQuestions();

        if (state.questions.length === 0) {
            clearQuestionDetail();
            return;
        }

        const selectedExists = state.questions.some(
            (question) =>
                question.id === state.selectedQuestionId
        );

        if (selectNewest || !selectedExists) {
            state.selectedQuestionId =
                state.questions[0].id;
        }

        selectQuestion(state.selectedQuestionId);
    } catch (error) {
        elements.questionList.innerHTML = `
            <div class="empty-state">
                ${escapeHtml(error.message)}
            </div>
        `;
    }
}

function updateStatistics() {
    const total = state.questions.length;

    const pending = state.questions.filter(
        (question) =>
            question.status === "open"
            || question.status === "assigned"
    ).length;

    const answered = state.questions.filter(
        (question) =>
            question.status === "answered"
            || question.status === "closed"
    ).length;

    elements.totalCount.textContent = total;
    elements.pendingCount.textContent = pending;
    elements.answeredCount.textContent = answered;
}

function filteredQuestions() {
    const searchValue = state.search
        .trim()
        .toLowerCase();

    if (!searchValue) {
        return state.questions;
    }

    return state.questions.filter((question) => {
        const searchableText = [
            question.subject,
            question.question_text,
            question.category.name_en,
            question.category.name_tr,
        ]
            .join(" ")
            .toLowerCase();

        return searchableText.includes(searchValue);
    });
}

function renderQuestions() {
    const questions = filteredQuestions();

    if (questions.length === 0) {
        elements.questionList.innerHTML = `
            <div class="empty-state">
                No questions found.
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
                    data-student-question-id="${question.id}"
                    tabindex="0"
                >
                    <div class="question-meta">
                        <span class="tag">
                            ${escapeHtml(
                                question.category.name_en
                            )}
                        </span>

                        <span>
                            ${escapeHtml(
                                formatDate(question.created_at)
                            )}
                        </span>
                    </div>

                    <div class="question-title">
                        ${escapeHtml(question.subject)}
                    </div>

                    <div class="question-footer">
                        <span>#Q-${question.id}</span>

                        <span
                            class="tag ${statusClass(
                                question.status
                            )}"
                        >
                            ${escapeHtml(
                                statusLabel(question.status)
                            )}
                        </span>
                    </div>
                </article>
            `;
        })
        .join("");

    document
        .querySelectorAll(
            "[data-student-question-id]"
        )
        .forEach((card) => {
            const chooseQuestion = () => {
                selectQuestion(
                    Number(
                        card.dataset.studentQuestionId
                    )
                );
            };

            card.addEventListener(
                "click",
                chooseQuestion
            );

            card.addEventListener(
                "keydown",
                (event) => {
                    if (
                        event.key === "Enter"
                        || event.key === " "
                    ) {
                        chooseQuestion();
                    }
                }
            );
        });
}

function selectQuestion(questionId) {
    const question = state.questions.find(
        (item) => item.id === questionId
    );

    if (!question) {
        clearQuestionDetail();
        return;
    }

    state.selectedQuestionId = questionId;
    renderQuestions();

    elements.detailStatus.textContent =
        statusLabel(question.status);

    elements.detailStatus.className =
        `tag ${statusClass(question.status)}`;

    elements.detailCategory.textContent =
        question.category.name_en;

    elements.detailDate.textContent =
        formatDate(question.created_at);

    elements.detailSubject.textContent =
        question.subject;

    elements.detailQuestion.textContent =
        question.question_text;

    if (question.latest_answer) {
        elements.detailAnswer.textContent =
            question.latest_answer;
    } else {
        elements.detailAnswer.textContent =
            "Your question is waiting for a staff answer.";
    }
}

function clearQuestionDetail() {
    state.selectedQuestionId = null;

    elements.detailStatus.textContent =
        "No questions";

    elements.detailStatus.className = "tag";

    elements.detailCategory.textContent = "-";
    elements.detailDate.textContent = "-";

    elements.detailSubject.textContent =
        "No question selected";

    elements.detailQuestion.textContent =
        "Submit your first question to see it here.";

    elements.detailAnswer.textContent =
        "No answer is available.";
}

function showQuestionPage() {
    elements.questionsSection.hidden = false;
    elements.newQuestionSection.hidden = true;

    setActiveNavigation("questions");
}

function showQuestionForm() {
    elements.questionsSection.hidden = true;
    elements.newQuestionSection.hidden = false;

    setActiveNavigation("new-question");

    elements.subjectInput.focus();
}

function setActiveNavigation(pageName) {
    document
        .querySelectorAll("[data-student-page]")
        .forEach((button) => {
            button.classList.toggle(
                "active",
                button.dataset.studentPage === pageName
            );
        });
}

async function submitQuestion(event) {
    event.preventDefault();

    const categoryId = Number(
        elements.categorySelect.value
    );

    const language =
        elements.languageSelect.value;

    const subject =
        elements.subjectInput.value.trim();

    const questionText =
        elements.questionInput.value.trim();

    if (!categoryId) {
        showFormMessage(
            "Please select a category.",
            true
        );

        return;
    }

    elements.submitButton.disabled = true;

    showFormMessage("Sending your question...");

    try {
        const result = await apiRequest(
            "/questions",
            {
                method: "POST",
                body: JSON.stringify({
                    student_id: STUDENT_ID,
                    category_id: categoryId,
                    language,
                    subject,
                    question_text: questionText,
                }),
            }
        );

        state.selectedQuestionId = result.id;

        elements.questionForm.reset();
        elements.languageSelect.value = "tr";

        showFormMessage(
            "Question submitted successfully."
        );

        await loadStudentQuestions(true);
        showQuestionPage();
    } catch (error) {
        showFormMessage(error.message, true);
    } finally {
        elements.submitButton.disabled = false;
    }
}

function showFormMessage(
    message,
    isError = false
) {
    elements.formMessage.hidden = false;
    elements.formMessage.textContent = message;

    elements.formMessage.style.color =
        isError ? "#d83b4f" : "#158657";
}

elements.questionSearch.addEventListener(
    "input",
    (event) => {
        state.search = event.target.value;
        renderQuestions();
    }
);

elements.openFormButton.addEventListener(
    "click",
    showQuestionForm
);

elements.closeFormButton.addEventListener(
    "click",
    showQuestionPage
);

document
    .querySelectorAll("[data-student-page]")
    .forEach((button) => {
        button.addEventListener("click", () => {
            if (
                button.dataset.studentPage
                === "new-question"
            ) {
                showQuestionForm();
            } else {
                showQuestionPage();
            }
        });
    });

elements.questionForm.addEventListener(
    "submit",
    submitQuestion
);

Promise.all([
    loadCategories(),
    loadStudentQuestions(),
]);