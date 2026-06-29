from memoscape.simulator import scenarios

def test_object_recall_returns_keys():
    _, card = scenarios.object_recall()
    assert card["type"] == "ObjectRecallCard"
    assert card["primary"] == "Keys"
    assert "Kitchen table" in card["lines"]

def test_object_wallet_returns_bedroom():
    _, card = scenarios.object_wallet()
    assert card["type"] == "ObjectRecallCard"
    assert card["primary"] == "Wallet"
    assert "Bedroom dresser" in card["lines"]

def test_object_glasses_returns_livingroom():
    _, card = scenarios.object_glasses()
    assert card["type"] == "ObjectRecallCard"
    assert card["primary"] == "Glasses"
    assert "Living room couch" in card["lines"]

def test_commitment_recall_returns_jordan_invoice():
    _, card = scenarios.commitment_recall()
    assert card["type"] == "CommitmentRecallCard"
    assert card["primary"] == "Send the invoice"
    assert card["eyebrow"] == "You promised Jordan"

def test_commitment_multi_returns_marcus():
    _, card = scenarios.commitment_multi()
    assert card["type"] == "CommitmentRecallCard"
    assert card["eyebrow"] == "You promised Marcus"
    assert card["primary"] == "Send the contract"

def test_commitment_multi_person_sofia():
    _, card = scenarios.commitment_multi_person()
    assert card["type"] == "CommitmentRecallCard"
    assert card["eyebrow"] == "You promised Sofia"
    assert card["primary"] == "Book the van"

def test_low_conf_scene_returns_low_confidence_card():
    _, card = scenarios.low_confidence_recall()
    assert card["type"] in ("LowConfidenceCard",)

def test_empty_db_returns_low_confidence():
    _, card = scenarios.no_memory_recall()
    assert card["type"] == "LowConfidenceCard"

def test_unknown_query_returns_low_confidence():
    _, card = scenarios.unknown_query()
    assert card["type"] == "LowConfidenceCard"
