"""test_cli_memories.py — `dreamlayer memories`: your data is one file, and here
is the read-only SQL prompt over it. Exercises path/browse, the veil gate, and
the Datasette metadata (canned queries)."""
from __future__ import annotations

from pathlib import Path

from dreamlayer import cli
from dreamlayer.memory.datasette_app import CANNED_QUERIES, MemoryExplorer


def _db(tmp_path) -> Path:
    p = tmp_path / "dreamlayer.db"
    p.write_bytes(b"SQLite format 3\x00")   # existence is all browse checks
    return p


def test_memories_path_reports_existing_file(tmp_path, capsys):
    db = _db(tmp_path)
    assert cli.main(["memories", "path", "--db", str(db)]) == 0
    out = capsys.readouterr().out
    assert str(db) in out and "KB" in out


def test_memories_path_reports_missing(tmp_path, capsys):
    missing = tmp_path / "nope.db"
    assert cli.main(["memories", "path", "--db", str(missing)]) == 0
    assert "no file yet" in capsys.readouterr().out


def test_memories_browse_print_builds_readonly_localhost_cmd(tmp_path, capsys):
    db = _db(tmp_path)
    rc = cli.main(["memories", "browse", "--db", str(db), "--print", "--port", "8010"])
    out = capsys.readouterr().out
    assert rc == 0
    # read-only (-i / immutable), localhost only, our port and file, with canned queries
    assert "datasette serve" in out and " -i " in out
    assert "127.0.0.1" in out and "8010" in out and str(db) in out
    assert "--metadata" in out
    # the metadata file was actually rendered next to the db
    assert (tmp_path / ".datasette-metadata.json").exists()


def test_memories_browse_missing_db_guides(tmp_path, capsys):
    rc = cli.main(["memories", "browse", "--db", str(tmp_path / "nope.db"), "--print"])
    assert rc == 2 and "no memory file" in capsys.readouterr().err


def test_memories_browse_refuses_under_veil_env(tmp_path, capsys, monkeypatch):
    db = _db(tmp_path)
    monkeypatch.setenv("DREAMLAYER_VEIL", "1")
    rc = cli.main(["memories", "browse", "--db", str(db), "--print"])
    assert rc == 2 and "veil" in capsys.readouterr().err.lower()


def test_memories_browse_refuses_under_veil_lockfile(tmp_path, capsys):
    db = _db(tmp_path)
    (tmp_path / "veil.lock").write_text("up", encoding="utf-8")
    rc = cli.main(["memories", "browse", "--db", str(db), "--print"])
    assert rc == 2 and "veil" in capsys.readouterr().err.lower()


def test_metadata_binds_canned_queries_to_the_file(tmp_path):
    db = _db(tmp_path)
    ex = MemoryExplorer(str(db))
    md = ex.metadata_dict()
    dbs = md["databases"]
    assert db.stem in dbs
    queries = dbs[db.stem]["queries"]
    assert set(queries) == set(CANNED_QUERIES)
    # the queries hit the real schema, and are SELECT-only
    joined = " ".join(q["sql"] for q in queries.values())
    assert "FROM memories" in joined and "FROM commitments" in joined
    assert "DELETE" not in joined.upper() and "UPDATE" not in joined.upper()


def test_command_is_immutable_by_default(tmp_path):
    ex = MemoryExplorer(str(_db(tmp_path)))
    assert ex.command(port=9) .startswith("datasette serve -i ")
