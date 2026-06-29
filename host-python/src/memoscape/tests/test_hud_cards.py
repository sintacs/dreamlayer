from memoscape.hud import cards

def test_object_recall_payload():
    c = cards.object_recall({"object":"Keys","place":"Kitchen table",
                              "detail":"Beside blue notebook","last_seen":"7:42 PM","confidence":0.86})
    assert c["type"] == "ObjectRecallCard"
    assert c["primary"] == "Keys"
    assert "Kitchen table" in c["lines"]

def test_commitment_payload():
    c = cards.commitment_recall({"person":"Jordan","task":"Send the invoice",
                                  "due":"Tomorrow before noon","confidence":0.8})
    assert c["eyebrow"] == "You promised Jordan"
    assert c["primary"] == "Send the invoice"

def test_privacy_payload():
    c = cards.privacy_paused()
    assert c["primary"] == "Memory paused"
    assert "Nothing is being captured" in c["lines"]

def test_all_samples_have_type():
    assert all("type" in p for p in cards.ALL_SAMPLES.values())

def test_low_confidence_payload():
    c = cards.low_confidence()
    assert c["confidence"] < 0.4

def test_proactive_footer_with_person():
    c = cards.proactive_memory({"summary":"You discussed the deal","person":"Marcus","confidence":0.7})
    assert c["footer"] == "With Marcus"

def test_proactive_footer_no_person():
    c = cards.proactive_memory({"summary":"Something happened","person":None,"confidence":0.6})
    assert c.get("footer") is None

def test_error_card():
    c = cards.error("Connection lost")
    assert c["type"] == "ErrorCard"
    assert c["primary"] == "Connection lost"
