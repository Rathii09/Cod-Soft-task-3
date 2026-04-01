from __future__ import annotations

import argparse
import json
import os
import re
import string
from typing import Dict, List, Tuple, TypedDict

SECTION_KEYWORDS: Dict[str, Tuple[str, ...]] = {
    "summary": ("summary", "profile", "objective"),
    "experience": ("experience", "employment", "work history"),
    "education": ("education", "university", "college", "degree"),
    "skills": ("skills", "technical skills", "competencies"),
    "projects": ("projects", "portfolio"),
}

POINTS_PER_SECTION = 8  # 5 sections × 8 points = 40 max section score.
MAX_KEYWORDS_FOR_FULL_SCORE = 8  # 8 keywords map to the 40-point max keyword score.
MAX_KEYWORD_SCORE = 40
MIN_KEYWORDS_FOR_FEEDBACK = 4
SECTION_COUNT = len(SECTION_KEYWORDS)
MAX_SECTION_SCORE = POINTS_PER_SECTION * SECTION_COUNT
FULL_LENGTH_SCORE = 20
PARTIAL_LENGTH_SCORE = 10
TARGET_MIN_WORDS = 200
TARGET_MAX_WORDS = 900
SOFT_MIN_WORDS = 150
SOFT_MAX_WORDS = 1200
TOTAL_MAX_SCORE = MAX_SECTION_SCORE + MAX_KEYWORD_SCORE + FULL_LENGTH_SCORE

if TOTAL_MAX_SCORE != 100:
    raise ValueError("Scoring constants must sum to 100. Update component maxima.")

SKILL_KEYWORDS: Tuple[str, ...] = (
    "python",
    "java",
    "sql",
    "excel",
    "aws",
    "docker",
    "git",
    "linux",
    "javascript",
    "react",
    "api",
    "data analysis",
    "machine learning",
    "project management",
    "communication",
    "leadership",
)


class ATSScore(TypedDict):
    score: int
    section_score: int
    keyword_score: int
    length_score: int
    word_count: int
    sections_found: List[str]
    sections_missing: List[str]
    keywords_found: List[str]
    feedback: List[str]


def normalize_text(text: str) -> str:
    text = text.replace("\u00a0", " ")
    text = text.lower()
    text = text.translate(str.maketrans(string.punctuation, " " * len(string.punctuation)))
    text = re.sub(r"\s+", " ", text).strip()
    return text


def find_keywords(text: str, keywords: Tuple[str, ...]) -> List[str]:
    found: List[str] = []
    for keyword in keywords:
        if " " in keyword:
            if keyword in text:
                found.append(keyword)
        else:
            if re.search(rf"\b{re.escape(keyword)}\b", text):
                found.append(keyword)
    return found


def score_sections(text: str) -> Tuple[int, List[str], List[str]]:
    found_sections: List[str] = []
    missing_sections: List[str] = []

    for section, candidates in SECTION_KEYWORDS.items():
        if any(candidate in text for candidate in candidates):
            found_sections.append(section)
        else:
            missing_sections.append(section)

    section_score = len(found_sections) * POINTS_PER_SECTION
    return section_score, found_sections, missing_sections


def score_keywords(text: str) -> Tuple[int, List[str]]:
    found_keywords = find_keywords(text, SKILL_KEYWORDS)
    keyword_score = int(
        round(
            min(len(found_keywords), MAX_KEYWORDS_FOR_FULL_SCORE)
            / MAX_KEYWORDS_FOR_FULL_SCORE
            * MAX_KEYWORD_SCORE
        )
    )
    return keyword_score, found_keywords


def score_length(word_count: int) -> Tuple[int, str]:
    """Return the length score and an optional feedback message for CV length."""
    if TARGET_MIN_WORDS <= word_count <= TARGET_MAX_WORDS:
        return FULL_LENGTH_SCORE, ""
    if SOFT_MIN_WORDS <= word_count <= SOFT_MAX_WORDS:
        return PARTIAL_LENGTH_SCORE, "Aim for 200-900 words for a concise one-page CV."
    return 0, "CV length is far from typical one-page ranges (200-900 words)."


def score_cv(text: str) -> ATSScore:
    cleaned = normalize_text(text)
    if not cleaned:
        raise ValueError("CV text is empty after cleaning.")

    word_count = len(re.findall(r"\b\w+\b", cleaned))
    section_score, sections_found, sections_missing = score_sections(cleaned)
    keyword_score, keywords_found = score_keywords(cleaned)
    length_score, length_feedback = score_length(word_count)

    feedback: List[str] = []
    if sections_missing:
        feedback.append(f"Add missing sections: {', '.join(sections_missing)}.")
    if len(keywords_found) < MIN_KEYWORDS_FOR_FEEDBACK:
        feedback.append("Highlight more role-relevant skills to improve keyword coverage.")
    if length_feedback:
        feedback.append(length_feedback)

    total_score = min(section_score + keyword_score + length_score, TOTAL_MAX_SCORE)

    return {
        "score": total_score,
        "section_score": section_score,
        "keyword_score": keyword_score,
        "length_score": length_score,
        "word_count": word_count,
        "sections_found": sections_found,
        "sections_missing": sections_missing,
        "keywords_found": keywords_found,
        "feedback": feedback,
    }


def read_text_from_file(path: str) -> str:
    if not os.path.isfile(path):
        raise FileNotFoundError(f"File not found: {path}")

    _, ext = os.path.splitext(path)
    if ext.lower() not in {".txt", ".md"}:
        raise ValueError("Only .txt or .md files are supported. Export your CV as text.")

    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Score a CV for ATS readiness based on sections, keywords, and length."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-f", "--file", help="Path to a .txt/.md CV file.")
    group.add_argument("-t", "--text", help="Paste CV text directly.")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.text is None and args.file is None:
        raise ValueError("Provide CV text with --text or a file with --file.")
    cv_text = args.text if args.text is not None else read_text_from_file(args.file)
    results = score_cv(cv_text)
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
