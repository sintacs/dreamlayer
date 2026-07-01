"""lie_lens/linguistic.py — Linguistic deception marker extractor.

Extracts hedging, pronoun use, complexity, negation, and qualifier
rates from a plain-text utterance. Zero ML dependency — rule-based,
running entirely on the phone in O(n) time.

In production, a distilled BERT-tiny INT8 model running on the Alif
NPU provides richer semantic features; these rule-based features serve
as the fallback / host-side implementation.
"""
from __future__ import annotations
import re
from typing import Optional
from .schema import LinguisticFeatures, ContactBaseline

_HEDGE_WORDS = frozenset([
    "maybe", "perhaps", "possibly", "probably", "might", "could",
    "i think", "i believe", "i feel like", "sort of", "kind of",
    "i guess", "i suppose", "not sure", "uncertain", "roughly",
])
_NEGATIONS = frozenset([
    "not", "never", "no", "nobody", "nothing", "neither",
    "nor", "none", "cannot", "can't", "won't", "don't",
    "didn't", "isn't", "wasn't", "aren't", "weren't",
])
_QUALIFIERS = frozenset([
    "very", "really", "actually", "honestly", "literally",
    "absolutely", "definitely", "certainly", "clearly", "obviously",
    "frankly", "truthfully", "to be honest", "believe me",
])


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]


def _words(text: str) -> list[str]:
    return re.findall(r"[a-z']+", text.lower())


def extract_linguistic(utterance: str) -> LinguisticFeatures:
    """Extract linguistic deception markers from a plain-text utterance."""
    text_lower = utterance.lower()
    sentences = _sentences(text_lower)
    words = _words(text_lower)
    n_sentences = max(len(sentences), 1)
    n_words = max(len(words), 1)

    # Hedging rate (per sentence)
    hedge_hits = sum(
        1 for phrase in _HEDGE_WORDS
        if phrase in text_lower
    )
    hedging_rate = hedge_hits / n_sentences

    # First-person pronoun rate (lower = distancing)
    first_person = sum(1 for w in words if w in ("i", "me", "my", "mine", "myself"))
    first_person_rate = first_person / n_words

    # Complexity (avg words per sentence)
    complexity_score = n_words / n_sentences

    # Negation rate
    negation_hits = sum(1 for w in words if w in _NEGATIONS)
    negation_rate = negation_hits / n_sentences

    # Qualifier rate ("honestly", "believe me" = over-assertion)
    qualifier_hits = sum(
        1 for phrase in _QUALIFIERS
        if phrase in text_lower
    )
    qualifier_rate = qualifier_hits / n_sentences

    return LinguisticFeatures(
        hedging_rate=round(hedging_rate, 3),
        first_person_rate=round(first_person_rate, 3),
        complexity_score=round(complexity_score, 2),
        negation_rate=round(negation_rate, 3),
        qualifier_rate=round(qualifier_rate, 3),
        utterance=utterance,
    )


def compute_linguistic_z_score(
    lf: LinguisticFeatures,
    baseline: Optional[ContactBaseline],
) -> float:
    """Return scalar z-score of linguistic features vs per-contact baseline."""
    if baseline is None or not baseline.is_calibrated():
        # No baseline — heuristic: high hedging + low first-person + high qualifier
        score = 0.0
        score += min(lf.hedging_rate * 2.0, 0.4)
        score += min((0.05 - lf.first_person_rate) * 10, 0.3) if lf.first_person_rate < 0.05 else 0.0
        score += min(lf.qualifier_rate * 3.0, 0.3)
        return score * 3.0

    dims = [
        ("hedging_rate",      lf.hedging_rate),
        ("first_person_rate", lf.first_person_rate),
        ("negation_rate",     lf.negation_rate),
        ("qualifier_rate",    lf.qualifier_rate),
    ]
    z_scores = []
    for key, val in dims:
        mean = baseline.linguistic_mean.get(key, 0.0)
        std  = baseline.linguistic_std.get(key, 1.0)
        if std > 0:
            z_scores.append(abs(val - mean) / std)
    return sum(z_scores) / len(z_scores) if z_scores else 0.0
