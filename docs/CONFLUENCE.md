# Confluence — two wearers, one entangled sky

When two DreamLayer wearers bond, their palette weathers entangle: each
display renders the blend of both nervous systems' weather. Converge and the
shared sky settles into one coherent front (palettes blended 50/50, no seam —
the absence is the message); drift and the sky splits — your weather keeps
your half, theirs renders on their half as a ready RGB, and a visible seam
stands between the fronts, widening with divergence. Togetherness =
1 − |your inner state − theirs|, EMA-smoothed, hysteresis-banded so the sky
never flaps. Nothing is said, nothing is measured out loud.

**The bond** (bond.py): explicit, mutual, revocable. Propose → a short human
code passes between the two of you → accept → confirm; both sides derive the
same HMAC key from (bond_id, code). Only WeatherPackets ever cross — a state
scalar, four palette slots, a sequence number; forged/replayed/stranger
traffic drops silently; your Veil silences your side completely; a quiet
peer fades to solo after 12 s; dissolve is unilateral; bonds expire in 8 h.

**Over the same bond:**
- **TinCan** (tincan.py) — silent gesture pings: taps play as light pulses at
  the partner's bearing. ≤5 pulses, one ping per 4 s, veil-gated.
- **Crossing** (crossing.py) — shared future ghosts where both rhythms
  already meet. Only salted place-hashes cross (salt = bond key, unlinkable
  across bonds); each side intersects locally; the shared ghost renders
  through Premonition's kind-6 path on both horizons.
- **Duet Rehearsal** (duet.py) — two performers, one figment: both wearers'
  beats land in one trace, either corrects any beat, both keep separately
  signed copies with independent revocation.
- **Weather Gift** (gift.py) — hand a WeatherLedger moment across: their sky
  plays your morning for 30 s, verbatim palette history.

Device: CONFLUENCE + TINCAN BLE types (lockstep with entangle.py/tincan.py);
dream_renderer draws the peer half-band + seam ticks and the ping pulse
train. Demo: `python scripts/run_demo_confluence.py` — the full dinner arc.
Tests: `src/dreamlayer/tests/test_confluence.py` (33).

## GhostMode — the bond, lifted to a group (2+ wearers)

A bond is a doorway between two wearers; **GhostMode** (mesh.py) is a *circle*
of them — a room, a hiking party, a crowd. One `form()` mints a `(group_id,
code)`; everyone else `join()`s with the code and derives the same group key
(`ghostmesh|group_id|code`). The same contract holds, one level up: only
*feeling* crosses (a `MeshPacket` body is a weather scalar, a bearing + band,
or a gesture symbol — **never speech, places, or names**), members are
anonymous on the wire (a random `member_id`), forged/replayed/stranger/self
traffic drops, the Veil silences your side, a quiet member fades after 12 s,
the group expires in 8 h. Any human name you attach (`alias`) lives only on
*your* device — it never crosses. Transport is a seam (`MeshTransport`): an
in-memory bus for tests, **BLE LE Coded PHY** (long-range, robust in a crowd,
tiny packets) on Halo.

**The Beacon** (beacon.py) rides the mesh with one job: point you at your
people. Each member emits a coarse **bearing + distance band relative to
themselves** (never coordinates); on your rim it renders as a pulse train at
that bearing — nearer pulses faster and brighter (reuses the TinCan shape). A
`BeaconCard` lists who's found and roughly where ("Maya · ahead-left · close")
using your *local* alias, never a wire name. No map, no "where are you" text.
Veil-gated; only bearing/presence crosses. Tests:
`src/dreamlayer/tests/test_ghostmode.py` (15).
