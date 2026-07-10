"""Rig-3 perception harness self-test: the Social-Lens calibration produces a
sane threshold/margin on deterministic synthetic clusters, so the harness that
will set the real numbers on-device can't silently rot. No real model needed."""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))  # repo root for scripts

from scripts.calibrate_social import calibrate, cosine, recommend, roc


def _unit(seed_vec):
    n = math.sqrt(sum(x * x for x in seed_vec)) or 1.0
    return [x / n for x in seed_vec]


def _cluster(center, jitter, n):
    """Deterministic points around a center (no RNG — index-derived jitter)."""
    out = []
    for i in range(n):
        d = ((i * 7) % 11 - 5) * jitter
        out.append(_unit([center[0] + d, center[1] - d, center[2] + d * 0.5]))
    return out


class TestCalibration:
    def _pairs(self):
        # two well-separated identities; genuine = within-cluster, impostor = across
        a = _cluster([1.0, 0.0, 0.0], 0.02, 12)
        b = _cluster([0.0, 1.0, 0.0], 0.02, 12)
        genuine = [[a[i], a[i + 1]] for i in range(0, len(a) - 1, 2)]
        genuine += [[b[i], b[i + 1]] for i in range(0, len(b) - 1, 2)]
        impostor = [[a[i], b[i]] for i in range(len(a))]
        return {"genuine": genuine, "impostor": impostor}

    def test_separable_data_gives_high_auc(self):
        report = calibrate(self._pairs())
        assert report["auc"] > 0.95
        assert 0.0 < report["threshold"] < 1.0
        assert report["margin"] >= 0.0

    def test_threshold_separates_the_populations(self):
        pairs = self._pairs()
        report = calibrate(pairs)
        thr = report["threshold"]
        gen = [cosine(a, b) for a, b in pairs["genuine"]]
        imp = [cosine(a, b) for a, b in pairs["impostor"]]
        # most genuine above, most impostor below — a real separating threshold
        assert sum(s >= thr for s in gen) / len(gen) >= 0.8
        assert sum(s < thr for s in imp) / len(imp) >= 0.8

    def test_roc_is_monotone_nonincreasing_in_fpr_vs_threshold(self):
        pts = roc([0.9, 0.8, 0.85], [0.2, 0.1, 0.3])
        fprs = [p["fpr"] for p in pts]
        assert fprs == sorted(fprs, reverse=True)   # higher thr → lower fpr

    def test_degenerate_inputs_dont_crash(self):
        assert recommend([], [])["threshold"] == 0.65   # falls back to the prior
