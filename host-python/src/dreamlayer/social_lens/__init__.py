"""social_lens — Personal contacts facial recognition for Brilliant Halo.

MODE 1 ONLY: matches faces against YOUR own address book.
100% on-device (phone). Zero third-party face databases. Legal everywhere.

Public API
----------
    from dreamlayer.social_lens import SocialLens

    fr = SocialLens(contact_registry=my_contacts)

    # On double-tap (IMU trigger):
    result = fr.identify(camera_frame)
    if result:
        card = result.to_hud_card()   # send to HUD renderer

Architecture
------------
  Stage 1  embedder   — 512-d MobileFaceNet embedding from camera frame
  Stage 2  index      — FAISS HNSW cosine search over personal contacts
  Stage 3  enricher   — load full contact record (name, company, notes, last-met)
  Stage 4  renderer   — SocialLensCard HUD output

Name-you-were-told capture
---------------------------
    # someone says "Hi, I'm Maya" — offer to remember it
    card = fr.offer_introduction("hi, I'm Maya", frame=camera_frame)
    if card:                       # a name was heard; nothing saved yet
        send_to_hud(card)
        # ... on a deliberate double-tap:
        fr.confirm_introduction()  # now Maya is your own contact

  Voluntary (nothing saved without confirm), spoken (closed offline
  grammar of self-introductions only), in-place (writes to your local
  contacts, no lookup, no network), and veiled-silent. A confirmed
  introduction is recallable by face on the very next identify().

Privacy
-------
  Your embeddings never leave the device.
  No stranger lookup. No public DB. No cloud.
  Only matches — and only remembers — people you were introduced to
  and chose to keep. "I've met them before, remind me," never
  "identify this stranger."
"""
from .analyzer import SocialLens
from .introduction import (
    IntroductionCapture, IntroductionOffer, parse_introduction,
)
from .schema import ContactRecord, SocialLensResult, MatchResult

__all__ = [
    "SocialLens", "ContactRecord", "SocialLensResult", "MatchResult",
    "IntroductionCapture", "IntroductionOffer", "parse_introduction",
]
