
import re
from typing import List, Tuple

WORD_RE = re.compile(r"\w+", re.UNICODE)
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\n+")

def split_sentences(text: str) -> List[str]:
    """Regex-basierte Satzsegmentierung"""
    return [
        s.strip()
        for s in SENTENCE_SPLIT_RE.split(text.strip())
        if len(s.strip()) > 3
    ]


def sentence_to_set(sentence: str) -> set[str]:
    """Normalisierte Token-Menge"""
    return set(WORD_RE.findall(sentence.lower()))

def jaccard_similarity(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)

def jaccard_clean(
    text: str,
    threshold: float = 0.7
) -> Tuple[float, str]:
    """
    Entfernt semantisch doppelte Sätze mittels Jaccard-Index.
    """

    sentences = split_sentences(text)

    if len(sentences) <= 1:
        return 1.0, text

    # Vorberechnete Wortmengen
    token_sets = [sentence_to_set(s) for s in sentences]

    kept_indices: List[int] = []

    for i, current_set in enumerate(token_sets):
        is_duplicate = False

        for j in kept_indices:
            similarity = jaccard_similarity(current_set, token_sets[j])
            if similarity >= threshold:
                is_duplicate = True
                break

        if not is_duplicate:
            kept_indices.append(i)

    cleaned_sentences = [sentences[i] for i in kept_indices]
    cleaned_text = " ".join(cleaned_sentences)

    ratio = len(cleaned_text) / max(len(text), 1)
    return ratio, cleaned_text
