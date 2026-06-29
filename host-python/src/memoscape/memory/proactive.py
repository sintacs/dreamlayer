from __future__ import annotations
import json
class ProactiveEngine:
    def __init__(self, db, min_conf=0.45):
        self.db = db; self.min_conf = min_conf
    def on_place(self, signature: str):
        place = next((p for p in self.db.places() if p["signature"] == signature), None)
        if not place: return None
        best = None
        for m in self.db.memories():
            if m.get("place_id") == place["id"] and (m.get("confidence") or 0) >= self.min_conf:
                if best is None or m["confidence"] > best["confidence"]: best = m
        if not best: return None
        meta = json.loads(best.get("meta") or "{}")
        return {"summary": best["summary"], "person": meta.get("person"), "confidence": best["confidence"]}
