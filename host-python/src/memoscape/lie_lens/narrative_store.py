"""lie_lens/narrative_store.py — Per-contact baseline storage + anomaly log.

In production this wraps the Halo Narrative agentic memory system.
In the host-Python layer it provides an in-process dict-based store
with the same interface, so all other modules can be tested without
hardware.
"""
from __future__ import annotations
import time
from typing import Optional
from .schema import (
    ContactBaseline, AnomalyLog, CredibilityVector,
    ActionUnits, ProsodyFeatures, LinguisticFeatures,
)


class NarrativeStore:
    """In-process narrative memory store.

    Stores per-contact baselines and anomaly logs. Provides incremental
    Bayesian update of means and standard deviations from new observations.
    """

    def __init__(self):
        self._baselines: dict[str, ContactBaseline] = {}
        self._anomalies: dict[str, list[AnomalyLog]] = {}
        self._contact_embeddings: dict = {}

    # ------------------------------------------------------------------
    # Contact embeddings
    # ------------------------------------------------------------------

    def set_contact_embeddings(self, embeddings: dict) -> None:
        """Load contact_id → 512-d embedding dict."""
        self._contact_embeddings = embeddings

    def get_contact_embeddings(self) -> dict:
        return self._contact_embeddings

    # ------------------------------------------------------------------
    # Baseline
    # ------------------------------------------------------------------

    def get_baseline(self, contact_id: str) -> Optional[ContactBaseline]:
        return self._baselines.get(contact_id)

    def update_baseline(
        self,
        contact_id: str,
        aus: Optional[ActionUnits] = None,
        prosody: Optional[ProsodyFeatures] = None,
        linguistic: Optional[LinguisticFeatures] = None,
    ) -> ContactBaseline:
        """Incrementally update the baseline for a contact."""
        bl = self._baselines.get(contact_id) or ContactBaseline(
            contact_id=contact_id
        )
        n = bl.sample_count

        if aus is not None:
            vec = aus.as_vector()
            if n == 0:
                bl.au_mean = list(vec)
                bl.au_std  = [0.1] * 17
            else:
                bl.au_mean = [
                    (bl.au_mean[i] * n + vec[i]) / (n + 1)
                    for i in range(17)
                ]
                bl.au_std = [
                    max(
                        ((bl.au_std[i] ** 2 * n +
                          (vec[i] - bl.au_mean[i]) ** 2) / (n + 1)) ** 0.5,
                        0.01,
                    )
                    for i in range(17)
                ]

        if prosody is not None:
            self._update_dict_stats(
                bl.prosody_mean, bl.prosody_std, n,
                {
                    "pitch_variance": prosody.pitch_variance,
                    "jitter_pct":     prosody.jitter_pct,
                    "shimmer_pct":    prosody.shimmer_pct,
                    "hesitation_rate":prosody.hesitation_rate,
                    "speech_rate_norm":prosody.speech_rate_norm,
                },
            )

        if linguistic is not None:
            self._update_dict_stats(
                bl.linguistic_mean, bl.linguistic_std, n,
                {
                    "hedging_rate":      linguistic.hedging_rate,
                    "first_person_rate": linguistic.first_person_rate,
                    "negation_rate":     linguistic.negation_rate,
                    "qualifier_rate":    linguistic.qualifier_rate,
                },
            )

        bl.sample_count = n + 1
        self._baselines[contact_id] = bl
        return bl

    @staticmethod
    def _update_dict_stats(
        mean_dict: dict, std_dict: dict, n: int, new_vals: dict
    ) -> None:
        for key, val in new_vals.items():
            old_mean = mean_dict.get(key, 0.0)
            old_std  = std_dict.get(key, 1.0)
            new_mean = (old_mean * n + val) / (n + 1)
            new_std  = max(
                ((old_std ** 2 * n + (val - new_mean) ** 2) / (n + 1)) ** 0.5,
                0.01,
            )
            mean_dict[key] = new_mean
            std_dict[key]  = new_std

    # ------------------------------------------------------------------
    # Anomaly log
    # ------------------------------------------------------------------

    def log_anomaly(
        self,
        contact_id: str,
        credibility: CredibilityVector,
        user_label: Optional[str] = None,
    ) -> AnomalyLog:
        entry = AnomalyLog(
            contact_id=contact_id,
            timestamp=time.monotonic(),
            credibility=credibility,
            user_label=user_label,
        )
        self._anomalies.setdefault(contact_id, []).append(entry)
        return entry

    def get_anomalies(self, contact_id: str) -> list[AnomalyLog]:
        return self._anomalies.get(contact_id, [])
