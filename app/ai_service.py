from __future__ import annotations

from difflib import SequenceMatcher
from pathlib import Path
import math
import os
import re
import sqlite3
import unicodedata

from openai import OpenAI, OpenAIError


class AIConfigurationError(RuntimeError):
    pass


class AIProviderError(RuntimeError):
    pass


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    normalized = re.sub(r"[^\w\s]", " ", normalized)
    return " ".join(normalized.split())


def _tokens(value: str) -> set[str]:
    ignored_words = {
        "a",
        "an",
        "and",
        "are",
        "for",
        "from",
        "how",
        "is",
        "of",
        "the",
        "to",
        "what",
        "ve",
        "veya",
        "ile",
        "icin",
        "için",
        "mi",
        "mı",
        "mu",
        "mü",
        "ne",
        "nasıl",
    }
    return {
        token
        for token in _normalize_text(value).split()
        if len(token) > 1 and token not in ignored_words
    }


def _character_ngrams(value: str, size: int = 3) -> set[str]:
    compact = _normalize_text(value).replace(" ", "")

    if len(compact) <= size:
        return {compact} if compact else set()

    return {
        compact[index:index + size]
        for index in range(len(compact) - size + 1)
    }


def _similarity(query: str, candidate: str) -> float:
    query_tokens = _tokens(query)
    candidate_tokens = _tokens(candidate)

    token_score = 0.0

    if query_tokens and candidate_tokens:
        common_tokens = query_tokens & candidate_tokens
        token_score = len(common_tokens) / math.sqrt(
            len(query_tokens) * len(candidate_tokens)
        )

    query_ngrams = _character_ngrams(query)
    candidate_ngrams = _character_ngrams(candidate)
    ngram_score = 0.0

    if query_ngrams and candidate_ngrams:
        union = query_ngrams | candidate_ngrams
        ngram_score = len(
            query_ngrams & candidate_ngrams
        ) / len(union)

    sequence_score = SequenceMatcher(
        None,
        _normalize_text(query),
        _normalize_text(candidate),
    ).ratio()

    return (
        token_score * 0.55
        + ngram_score * 0.30
        + sequence_score * 0.15
    )


def find_similar_entries(
    database_path: Path,
    *,
    subject: str,
    question_text: str,
    language: str,
    category_id: int,
    limit: int = 3,
) -> list[dict]:
    query = f"{subject} {question_text}".strip()

    with sqlite3.connect(database_path) as connection:
        rows = connection.execute(
            """
            SELECT
                knowledge_entries.id,
                knowledge_entries.question,
                knowledge_entries.answer,
                categories.id,
                categories.name_tr,
                categories.name_en
            FROM knowledge_entries
            JOIN categories
                ON knowledge_entries.category_id = categories.id
            JOIN languages
                ON knowledge_entries.language_id = languages.id
            WHERE languages.code = ?
            """,
            (language.lower(),),
        ).fetchall()

    ranked_entries = []

    for row in rows:
        score = _similarity(query, row[1])

        if row[3] == category_id:
            score += 0.08

        ranked_entries.append(
            {
                "id": row[0],
                "question": row[1],
                "answer": row[2],
                "category_id": row[3],
                "category_tr": row[4],
                "category_en": row[5],
                "similarity": round(min(score, 1.0), 4),
            }
        )

    ranked_entries.sort(
        key=lambda entry: entry["similarity"],
        reverse=True,
    )
    return ranked_entries[:limit]


def build_prompt_context(entries: list[dict]) -> str:
    context_parts = []

    for index, entry in enumerate(entries, start=1):
        context_parts.append(
            "\n".join(
                [
                    f"Record {index} (knowledge ID {entry['id']}):",
                    f"Question: {entry['question']}",
                    f"Approved answer: {entry['answer']}",
                ]
            )
        )

    return "\n\n".join(context_parts)


def generate_ai_answer(
    *,
    subject: str,
    question_text: str,
    language: str,
    category_name: str,
    prompt_context: str,
) -> tuple[str, str]:
    api_key = os.getenv("GROQ_API_KEY")
    model_name = os.getenv(
        "GROQ_MODEL",
        "openai/gpt-oss-20b",
    )

    if not api_key:
        raise AIConfigurationError(
            "GROQ_API_KEY is not configured."
        )

    response_language = (
        "Turkish" if language.lower() == "tr" else "English"
    )
    system_message = (
        "You are an AI answer assistant for EMU student support staff. "
        "Use only the approved institutional records supplied below. "
        "Do not invent dates, rules, fees, links, or contact details. "
        "If the records are not sufficient, clearly tell the staff member "
        "that the information must be verified. Write one concise answer "
        f"suggestion in {response_language}. Return only the suggestion."
    )
    user_message = (
        f"Category: {category_name}\n"
        f"New question subject: {subject}\n"
        f"New question: {question_text}\n\n"
        "Approved institutional records:\n"
        f"{prompt_context}"
    )

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.groq.com/openai/v1",
    )

    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {
                    "role": "system",
                    "content": system_message,
                },
                {
                    "role": "user",
                    "content": user_message,
                },
            ],
            temperature=0.2,
            reasoning_effort="low",
            max_completion_tokens=700,
            extra_body={"reasoning_format": "hidden"},
        )
    except OpenAIError as error:
        raise AIProviderError(
            "The AI provider could not generate a suggestion."
        ) from error

    suggestion = response.choices[0].message.content

    if not suggestion or not suggestion.strip():
        raise AIProviderError(
            "The AI provider returned an empty suggestion."
        )

    return suggestion.strip(), model_name
