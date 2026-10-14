import logging

import supabase_sync


def test_missing_credentials_warn_once_not_every_turn(monkeypatch, caplog):
    monkeypatch.setattr(supabase_sync, "_client", None)
    monkeypatch.setattr(supabase_sync, "_warned_missing", False)
    monkeypatch.setattr(supabase_sync, "_load_env", lambda: ("", ""))
    with caplog.at_level(logging.WARNING, logger=supabase_sync.logger.name):
        for _ in range(5):
            assert supabase_sync.get_client() is None
    hits = [r for r in caplog.records if "Missing SUPABASE_URL" in r.getMessage()]
    assert len(hits) == 1
