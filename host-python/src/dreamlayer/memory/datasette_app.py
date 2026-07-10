"""Datasette memory explorer — turn the memory SQLite into a browsable local web
UI, zero-code, local-first. *The point of the whole privacy architecture, made
demonstrable: your memory is one file, and here is the SQL prompt over it.*

ADD-alongside: new module. Lazy-imports datasette (extras group `infra`); when
absent, `command()` still returns the exact CLI a user can run once they install
it, and `available` is False — no behaviour change to the memory engine.

Read-only by construction: the launch runs Datasette **immutable** (`-i`), bound
to 127.0.0.1, so browsing can never write to (or expose off-box) your memory.
"""
from __future__ import annotations
import json
import logging
from pathlib import Path

log = logging.getLogger("dreamlayer.datasette_app")

try:
    import datasette  # type: ignore  # noqa: F401
    _HAS_DATASETTE = True
except ImportError:
    _HAS_DATASETTE = False

# Canned queries shipped with the explorer — the three the privacy story wants a
# newcomer to run first, plus the "what did I deliberately keep" pin query the
# Nod-to-Remember demo leans on. All SELECT-only, all over the real schema
# (see memory/schema.sql).
CANNED_QUERIES = {
    "taught-this-month": {
        "title": "Everything I was taught this month",
        "sql": (
            "SELECT summary, created_at FROM memories "
            "WHERE kind = 'taught' AND created_at >= strftime('%Y-%m-01','now') "
            "ORDER BY created_at DESC"
        ),
    },
    "open-commitments-by-person": {
        "title": "Open commitments, by person",
        "sql": (
            "SELECT person, task, due FROM commitments "
            "ORDER BY person, COALESCE(due, '9999-12-31')"
        ),
    },
    "places-that-trigger-cards": {
        "title": "Places that trigger the most cards",
        "sql": (
            "SELECT p.name AS place, COUNT(m.id) AS cards "
            "FROM places p JOIN memories m ON m.place_id = p.id "
            "GROUP BY p.id ORDER BY cards DESC"
        ),
    },
    "pinned-things": {
        "title": "Things I deliberately kept (pinned)",
        "sql": (
            "SELECT kind, summary, created_at FROM memories "
            "WHERE json_extract(meta, '$.pinned') = 1 "
            "ORDER BY created_at DESC"
        ),
    },
}

METADATA_FILENAME = ".datasette-metadata.json"


class MemoryExplorer:
    available = _HAS_DATASETTE

    def __init__(self, db_path: str):
        self.db_path = db_path

    # -- metadata (canned queries) --------------------------------------------

    def _db_stem(self) -> str:
        return Path(self.db_path).stem or "memory"

    def metadata_dict(self) -> dict:
        """Datasette metadata binding the canned queries to this file. Keyed by
        the db's stem, because Datasette names a database by its filename."""
        return {
            "title": "DreamLayer — your memory, as a file",
            "description_html": (
                "Local, read-only. This is the entire record the platform keeps "
                "about you — no audio table, no video table, just meaning you can "
                "read, query, and delete."
            ),
            "databases": {self._db_stem(): {"queries": dict(CANNED_QUERIES)}},
        }

    def write_metadata(self, out_dir: str | Path | None = None) -> str:
        """Write the metadata JSON next to the db (or into ``out_dir``); returns
        its path. Safe to call repeatedly — it just re-renders the same file."""
        base = Path(out_dir) if out_dir else Path(self.db_path).resolve().parent
        base.mkdir(parents=True, exist_ok=True)
        path = base / METADATA_FILENAME
        path.write_text(json.dumps(self.metadata_dict(), indent=2), encoding="utf-8")
        return str(path)

    # -- launch ----------------------------------------------------------------

    def command(self, port: int = 8001, metadata_path: str | None = None,
                immutable: bool = True) -> str:
        """The local-only launch command (host 127.0.0.1, immutable by design)."""
        parts = ["datasette", "serve"]
        if immutable:
            parts += ["-i", self.db_path]
        else:
            parts.append(self.db_path)
        parts += ["--host", "127.0.0.1", "--port", str(port)]
        if metadata_path:
            parts += ["--metadata", metadata_path]
        return " ".join(parts)

    def serve(self, port: int = 8001):
        """Return a configured Datasette app instance, or None with no dep."""
        if not _HAS_DATASETTE:
            log.info("[datasette] not installed; run: %s", self.command(port))
            return None
        try:
            from datasette.app import Datasette  # type: ignore
            return Datasette([self.db_path], immutables=[self.db_path],
                             metadata=self.metadata_dict())
        except Exception as exc:
            log.error("[datasette] init failed: %s", exc)
            return None
