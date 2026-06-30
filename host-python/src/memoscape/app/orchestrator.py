from __future__ import annotations
import os
from ..memory.db import MemoryDB
from ..memory.retrieval import Retriever
from ..memory.proactive import ProactiveEngine
from ..memory.privacy import PrivacyGate
from ..memory.embeddings import MockEmbeddingProvider, OpenAIEmbeddingProvider
from ..pipelines import vision, speech
from ..pipelines.ingest import IngestPipeline
from ..pipelines.extraction import extract_commitments
from ..config import CONFIG
from . import intents, answer_builder
from ..hud import cards


class Orchestrator:
    def __init__(self, bridge, db_path=":memory:", config=None):
        cfg = config or CONFIG
        self.bridge = bridge
        self.db = MemoryDB(db_path)

        # Use real OpenAI embeddings when key is available, mock otherwise
        if getattr(cfg, "openai_api_key", "") or os.environ.get("OPENAI_API_KEY"):
            self.embedder = OpenAIEmbeddingProvider(cfg)
        else:
            self.embedder = MockEmbeddingProvider()

        self.retriever = Retriever(self.db, self.embedder)
        self.privacy   = PrivacyGate()
        self.proactive = ProactiveEngine(self.db, privacy=self.privacy)

        # Wire IngestPipeline: tier-1+2+3 when key present, tier-1+2 otherwise
        if getattr(cfg, "openai_api_key", "") or os.environ.get("OPENAI_API_KEY"):
            self.pipeline = IngestPipeline.with_llm(self.db, cfg)
        else:
            self.pipeline = IngestPipeline(self.db)

        bridge.on_event(self._on_event)

    def boot(self, lua_root):
        info = self.bridge.connect()
        self.bridge.load_lua_app(lua_root)
        self.bridge.send_command("show_ready")
        return info

    def ingest_scene(self, scene):
        if not self.privacy.allow_capture():
            return None
        mem = vision.extract_object_memory(scene)
        emb = self.embedder.embed(
            f"{mem['object']} {mem['place']} {mem['detail']}"
        )
        mid = self.db.add_memory(
            "object",
            f"{mem['object']} at {mem['place']}",
            embedding=emb,
            confidence=mem["confidence"],
            meta=mem,
        )
        self.bridge.send_card(
            cards.saved_memory(mem["object"]), event="memory_saved"
        )
        return mid

    def ingest_conversation(self, conv, place_id=None, context=None):
        """Ingest a conversation via the three-tier NLP pipeline.

        Accepts both raw transcript strings and legacy structured dicts
        (the old {participants, turns, summary} fixture format).

        For structured dicts, commitment rows are written via
        extract_commitments() so that db.commitments() lookups continue
        to work. The full transcript is also run through IngestPipeline
        for object/person/task events.
        """
        if not self.privacy.allow_capture():
            return []

        db_ids = []

        if isinstance(conv, str):
            transcript = conv
        else:
            # Structured fixture dict — extract the summary as the transcript
            parsed     = speech.extract_conversation(conv)
            transcript = parsed.get("summary", "")

            # Store the top-level conversation memory
            emb = self.embedder.embed(transcript)
            conv_mid = self.db.add_memory(
                "conversation",
                transcript,
                embedding=emb,
                confidence=0.7,
                place_id=place_id,
                meta={"person": parsed["participants"][-1]
                      if parsed.get("participants") else None},
            )
            db_ids.append(conv_mid)

            # Write commitment rows from structured turns (legacy path)
            for c in extract_commitments(conv):
                cid = self.db.add_commitment(
                    c["person"], c["task"], c["due"], conv_mid, c["confidence"]
                )
                db_ids.append(cid)

        # Run IngestPipeline on the transcript for object/person/task events
        events = self.pipeline.ingest(transcript, context=context)
        import json as _json
        for ev in events:
            emb = self.embedder.embed(ev.summary)
            self.db.conn.execute(
                "UPDATE memories SET embedding=? WHERE id=?",
                (_json.dumps(emb), ev.db_id),
            )
            db_ids.append(ev.db_id)
        self.db.conn.commit()

        self.bridge.send_card(cards.saved_memory(""), event="memory_saved")
        return db_ids

    def ask(self, query):
        self.bridge.send_command("ask")
        intent = intents.classify(query)
        if intent["intent"] == "object_recall":
            card = answer_builder.build_object_answer(
                self.retriever.search(query, kind="object")
            )
        elif intent["intent"] == "commitment_recall":
            card = answer_builder.build_commitment_answer(
                self.db.commitments(person=intent.get("person"))
            )
        else:
            card = cards.low_confidence()
        self.bridge.send_card(card)
        return card

    def on_place(self, signature):
        if not self.privacy.allow_capture():
            return None
        p    = self.proactive.on_place(signature)
        card = answer_builder.build_proactive(p)
        if card:
            self.bridge.send_card(card, event="proactive_trigger")
        return card

    def pause(self):
        self.privacy.pause()
        self.bridge.inject_event("privacy_pause")
        self.bridge.send_card(cards.privacy_paused(), event="privacy_pause")

    def resume(self):
        self.privacy.resume()
        self.bridge.inject_event("privacy_resume")
        self.bridge.send_command("resume")

    def _on_event(self, name, payload):
        if name == "long_press":
            self.pause() if not self.privacy.paused else self.resume()
