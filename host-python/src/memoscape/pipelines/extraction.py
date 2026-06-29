PROMISE_CUES = ("i'll","i will","promise","i can","i'll send","send")
def extract_commitments(conv):
    out = []
    for turn in conv.get("turns",[]):
        text = turn.get("text","").lower()
        if any(cue in text for cue in PROMISE_CUES) and turn.get("commitment"):
            c = turn["commitment"]
            out.append({"person": c.get("to") or _other(conv, turn.get("speaker")),
                        "task": c["task"], "due": c.get("due",""), "confidence": c.get("confidence",0.8)})
    return out
def _other(conv, speaker):
    for p in conv.get("participants",[]):
        if p != speaker: return p
    return ""
