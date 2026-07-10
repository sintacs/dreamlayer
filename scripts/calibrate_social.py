#!/usr/bin/env python3
"""Rig 3 — Social Lens threshold/margin calibration from a labelled pair-set.

The Social Lens face-match threshold (0.65) and top-2 margin (0.08) are
placeholders set against a stub embedder. On a real device this is the harness
that replaces them with numbers earned from data: feed it genuine/impostor
embedding pairs, it computes the ROC, and it recommends the threshold (best
Youden's J) and a margin (a low-FPR operating point).

    python -m scripts.calibrate_social pairs.json            # human report
    python -m scripts.calibrate_social pairs.json --json out.json

`pairs.json`: {"genuine": [[embA, embB], …], "impostor": [[embC, embD], …]}
Embeddings are lists of floats (any dim, unit or not — cosine is scale-free).

This ships with a deterministic self-test (tests/test_perception_bench.py) over
synthetic clusters so the harness can't rot before the real device exists.
"""
from __future__ import annotations

import json
import math
import sys


def cosine(a, b) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (na * nb)


def roc(genuine_scores, impostor_scores, steps: int = 200):
    """Sweep the threshold; return points [{thr, tpr, fpr}] over [min,max]."""
    alls = genuine_scores + impostor_scores
    lo, hi = (min(alls), max(alls)) if alls else (0.0, 1.0)
    span = (hi - lo) or 1.0
    out = []
    for i in range(steps + 1):
        thr = lo + span * i / steps
        tp = sum(1 for s in genuine_scores if s >= thr)
        fp = sum(1 for s in impostor_scores if s >= thr)
        tpr = tp / len(genuine_scores) if genuine_scores else 0.0
        fpr = fp / len(impostor_scores) if impostor_scores else 0.0
        out.append({"thr": thr, "tpr": tpr, "fpr": fpr})
    return out


def auc_mann_whitney(genuine_scores, impostor_scores) -> float:
    """Exact ROC-AUC = P(genuine > impostor) over all pairs (ties count 0.5).
    Robust on perfectly-separable data where a trapezoid over the ROC is fiddly."""
    if not genuine_scores or not impostor_scores:
        return 0.0
    wins = 0.0
    for g in genuine_scores:
        for i in impostor_scores:
            wins += 1.0 if g > i else (0.5 if g == i else 0.0)
    return wins / (len(genuine_scores) * len(impostor_scores))


def recommend(genuine_scores, impostor_scores,
              prior_threshold: float = 0.65) -> dict:
    """Threshold = best Youden's J (tpr − fpr). Margin = the gap between the
    genuine median and the impostor 95th percentile (how much daylight a real
    match should have over the best impostor), floored at 0. With no data, the
    recommendation is the current prior (0.65 threshold, 0.08 margin)."""
    if not genuine_scores or not impostor_scores:
        return {"threshold": prior_threshold, "margin": 0.08,
                "at_threshold": {"tpr": 0.0, "fpr": 0.0}, "auc": 0.0,
                "n_genuine": len(genuine_scores),
                "n_impostor": len(impostor_scores)}
    points = roc(genuine_scores, impostor_scores)
    best = max(points, key=lambda p: p["tpr"] - p["fpr"])
    gen_sorted = sorted(genuine_scores)
    imp_sorted = sorted(impostor_scores)
    gen_median = gen_sorted[len(gen_sorted) // 2]
    imp_p95 = imp_sorted[min(len(imp_sorted) - 1, int(0.95 * len(imp_sorted)))]
    margin = max(0.0, round(gen_median - imp_p95, 3))
    return {
        "threshold": round(best["thr"], 3),
        "margin": margin,
        "at_threshold": {"tpr": round(best["tpr"], 3), "fpr": round(best["fpr"], 3)},
        "auc": round(auc_mann_whitney(genuine_scores, impostor_scores), 4),
        "n_genuine": len(genuine_scores), "n_impostor": len(impostor_scores),
    }


def calibrate(pairs: dict) -> dict:
    gen = [cosine(a, b) for a, b in pairs.get("genuine", [])]
    imp = [cosine(a, b) for a, b in pairs.get("impostor", [])]
    return recommend(gen, imp)


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        print(__doc__)
        return 2
    pairs = json.loads(open(argv[0]).read())
    report = calibrate(pairs)
    if "--json" in argv:
        out = argv[argv.index("--json") + 1]
        open(out, "w").write(json.dumps(report, indent=2))
    print("Social Lens calibration")
    print(f"  recommended threshold : {report['threshold']}")
    print(f"  recommended margin    : {report['margin']}")
    print(f"  at threshold          : TPR {report['at_threshold']['tpr']} · "
          f"FPR {report['at_threshold']['fpr']}")
    print(f"  AUC                   : {report['auc']}  "
          f"(n={report['n_genuine']}g/{report['n_impostor']}i)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
