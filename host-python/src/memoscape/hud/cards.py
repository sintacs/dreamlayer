from __future__ import annotations
from . import themes as T

def _card(type_, **kw):
    p = {"type": type_}
    p.update({k: v for k, v in kw.items() if v is not None})
    return p

def ready():               return _card("ReadyCard", primary="Memoscape", footer="Ready", accent=T.ACCENT_MEMORY)
def saved_memory(label):   return _card("SavedMemoryCard", eyebrow="Saved", primary=label or "Memory saved", accent=T.ACCENT_SUCCESS, confidence=1.0)
def query_listening():     return _card("QueryListeningCard", eyebrow="Listening", primary="…", accent=T.ACCENT_ATTENTION)
def loading():             return _card("LoadingCard", primary="Thinking…", accent=T.ACCENT_MEMORY)
def object_recall(o):      return _card("ObjectRecallCard", primary=o["object"], lines=[o["place"], o.get("detail")], footer=o.get("last_seen"), accent=T.ACCENT_MEMORY, confidence=o.get("confidence"))
def commitment_recall(c):  return _card("CommitmentRecallCard", eyebrow=f"You promised {c.get('person','')}", primary=c["task"], footer=c.get("due"), accent=T.ACCENT_MEMORY, confidence=c.get("confidence"))
def proactive_memory(p):   return _card("ProactiveMemoryCard", eyebrow="Last time here", primary=p["summary"], footer=(f"With {p['person']}" if p.get("person") else None), accent=T.ACCENT_ATTENTION, confidence=p.get("confidence"))
def person_context(p):     return _card("PersonContextCard", eyebrow=p["person"], primary=p["headline"], lines=[p.get("detail")], accent=T.ACCENT_MEMORY, confidence=p.get("confidence"))
def privacy_paused():      return _card("PrivacyPausedCard", primary="Memory paused", lines=["Nothing is being captured"], accent=T.STATUS_PAUSED)
def error(msg="Try again"): return _card("ErrorCard", eyebrow="Something went wrong", primary=msg, accent=T.ACCENT_ERROR)
def low_confidence():      return _card("LowConfidenceCard", eyebrow="Not sure", primary="No clear memory", lines=["Try rephrasing"], accent=T.STATUS_PAUSED, confidence=0.2)

ALL_SAMPLES = {
    "ready": ready(), "saved": saved_memory("Keys on table"),
    "listening": query_listening(), "loading": loading(),
    "object_recall": object_recall({"object":"Keys","place":"Kitchen table","detail":"Beside blue notebook","last_seen":"Last seen 7:42 PM","confidence":0.86}),
    "commitment": commitment_recall({"person":"Jordan","task":"Send the invoice","due":"Tomorrow before noon","confidence":0.8}),
    "proactive": proactive_memory({"summary":"You discussed the invoice","person":"Jordan","confidence":0.7}),
    "person": person_context({"person":"Jordan","headline":"Owes you a reply","detail":"Invoice thread","confidence":0.6}),
    "paused": privacy_paused(), "error": error("Disconnected"), "low_conf": low_confidence(),
}
