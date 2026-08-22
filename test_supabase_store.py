"""Offline tests for the Phase A Supabase access foundation."""

from __future__ import annotations

from typing import Any

import supabase_store


class FakeResponse:
    def __init__(self, status_code: int, payload: Any = None, text: str = ""):
        self.status_code = status_code
        self._payload = payload
        self.text = text
        self.content = b"" if payload is None else b"payload"

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 300

    def json(self) -> Any:
        return self._payload


class FakeHttp:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.responses: list[FakeResponse] = []

    def request(self, method: str, url: str, **kwargs: Any) -> FakeResponse:
        self.calls.append({"method": method, "url": url, **kwargs})
        return self.responses.pop(0)


def main() -> None:
    assert supabase_store.resolve_data_backend() == "sqlite"
    assert supabase_store.resolve_data_backend("SUPABASE") == "supabase"
    try:
        supabase_store.resolve_data_backend("postgres")
        raise AssertionError("Invalid backend must fail")
    except supabase_store.StorageConfigurationError:
        pass

    settings = supabase_store.SupabaseSettings.from_mapping(
        {"url": "https://example.supabase.co", "service_role_key": "server-only-key"}
    )
    fake_http = FakeHttp()
    store = supabase_store.SupabaseStore(settings, fake_http)

    fake_http.responses.append(FakeResponse(200, [{"auth_subject": "auth0|user-1"}]))
    profile = store.upsert_profile(
        {
            "auth_subject": "auth0|user-1",
            "user_hash": "legacy-hash",
            "username": "moon_orbit",
            "display_name": "Moon Orbit",
            "avatar": "🌙",
            "bio": "Testing the foundation.",
        }
    )
    assert profile["auth_subject"] == "auth0|user-1"
    assert fake_http.calls[-1]["params"] == {"on_conflict": "auth_subject"}
    assert fake_http.calls[-1]["headers"]["Authorization"] == "Bearer server-only-key"

    secret_settings = supabase_store.SupabaseSettings.from_mapping(
        {"url": "https://example.supabase.co", "service_role_key": "sb_secret_lunatick_test"}
    )
    secret_store = supabase_store.SupabaseStore(secret_settings, FakeHttp())
    assert secret_store._headers == {
        "apikey": "sb_secret_lunatick_test",
        "Content-Type": "application/json",
    }
    assert "Authorization" not in secret_store._headers
    assert supabase_store.public_display_name("someone@example.test") == "Moon Wanderer"
    assert supabase_store.public_display_name("Public Moon") == "Public Moon"

    fake_http.responses.append(
        FakeResponse(
            200,
            [
                {
                    "username": "moon_orbit",
                    "display_name": "Moon Orbit",
                    "avatar": "🌙",
                    "bio": "Testing the foundation.",
                    "email": "must-not-leak@example.com",
                    "auth_subject": "must-not-leak",
                }
            ],
        )
    )
    public_profile = store.get_public_profile_by_username("@MOON_ORBIT")
    assert public_profile == {
        "username": "moon_orbit",
        "display_name": "Moon Orbit",
        "avatar": "🌙",
        "bio": "Testing the foundation.",
    }
    assert "email" not in public_profile
    assert fake_http.calls[-1]["params"]["select"] == "username,display_name,avatar,bio"

    fake_http.responses.append(
        FakeResponse(
            200,
            [{"username": "moon_orbit", "display_name": "someone@example.test", "avatar": "🌙", "bio": ""}],
        )
    )
    sanitized_public_profile = store.get_public_profile_by_username("moon_orbit")
    assert sanitized_public_profile["display_name"] == "Moon Wanderer"

    fake_http.responses.append(FakeResponse(200, []))
    assert store.username_is_available("moon_orbit", "auth0|user-1") is True
    username_query = fake_http.calls[-1]["params"]
    assert username_query == {
        "select": "auth_subject",
        "username": "eq.moon_orbit",
        "auth_subject": "neq.auth0|user-1",
        "limit": "1",
    }

    fake_http.responses.append(FakeResponse(200, [{"auth_subject": "auth0|user-1", "birth_date": "1990-01-01"}]))
    updated_profile = store.update_profile_fields(
        "auth0|user-1", {"birth_date": "1990-01-01", "not_a_profile_field": "blocked"}
    )
    assert updated_profile["birth_date"] == "1990-01-01"
    assert fake_http.calls[-1]["method"] == "PATCH"
    assert fake_http.calls[-1]["params"] == {"auth_subject": "eq.auth0|user-1"}
    assert fake_http.calls[-1]["json"] == {"birth_date": "1990-01-01"}

    fake_http.responses.append(FakeResponse(200, []))
    assert store.list_card_profiles("auth0|user-1") == []
    card_query = fake_http.calls[-1]["params"]
    assert card_query["birth_date"] == "not.is.null"
    assert card_query["auth_subject"] == "neq.auth0|user-1"
    assert "email" not in card_query["select"]

    fake_http.responses.append(FakeResponse(200, []))
    assert store.has_pending_card_trade("auth0|user-1", "auth0|user-2") is False
    assert fake_http.calls[-1]["params"]["sender_auth_subject"] == "eq.auth0|user-1"
    assert fake_http.calls[-1]["params"]["receiver_auth_subject"] == "eq.auth0|user-2"

    fake_http.responses.append(FakeResponse(201, [{"id": 7}]))
    trade = store.create_card_trade("auth0|user-1", "auth0|user-2", "Hello")
    assert trade == {"id": 7}
    assert fake_http.calls[-1]["json"] == {
        "sender_auth_subject": "auth0|user-1",
        "receiver_auth_subject": "auth0|user-2",
        "message": "Hello",
        "status": "pending",
    }

    fake_http.responses.append(FakeResponse(200, []))
    assert store.list_card_trades("auth0|user-1", "incoming") == []
    assert fake_http.calls[-1]["params"]["receiver_auth_subject"] == "eq.auth0|user-1"

    fake_http.responses.append(FakeResponse(200, [{"id": 7}]))
    assert store.resolve_card_trade(7, "auth0|user-2", True) is True
    assert fake_http.calls[-1]["params"]["status"] == "eq.pending"
    assert fake_http.calls[-1]["json"]["status"] == "accepted"
    assert "resolved_at" in fake_http.calls[-1]["json"]

    fake_http.responses.append(
        FakeResponse(200, [{"sender_auth_subject": "auth0|user-2", "receiver_auth_subject": "auth0|user-1"}])
    )
    assert store.list_accepted_card_contacts("auth0|user-1") == ["auth0|user-2"]
    assert fake_http.calls[-1]["params"]["status"] == "eq.accepted"

    fake_http.responses.append(
        FakeResponse(
            200,
            [{"auth_subject": "auth0|user-2", "username": "other_moon", "display_name": "Other Moon", "avatar": "🪐", "email": "private@example.test"}],
        )
    )
    author_summaries = store.get_public_profile_summaries(["auth0|user-2"])
    assert author_summaries == {
        "auth0|user-2": {"username": "other_moon", "display_name": "Other Moon", "avatar": "🪐"}
    }
    assert fake_http.calls[-1]["params"]["select"] == "auth_subject,username,display_name,avatar"

    fake_http.responses.append(
        FakeResponse(200, [{"auth_subject": "auth0|user-2", "username": "other_moon", "display_name": "someone@example.test", "avatar": "🪐"}])
    )
    sanitized_summary = store.get_public_profile_summaries(["auth0|user-2"])
    assert sanitized_summary["auth0|user-2"]["display_name"] == "Moon Wanderer"

    fake_http.responses.append(FakeResponse(201))
    store.seed_boards([{"slug": "general", "name": "General", "description": "Open discussion"}])
    assert fake_http.calls[-1]["json"] == [{"slug": "general", "name": "General", "description": "Open discussion"}]

    fake_http.responses.append(FakeResponse(201, [{"id": 22}]))
    board_post = store.create_board_post("general", "auth0|user-1", "Title", "Body")
    assert board_post == {"id": 22}
    assert fake_http.calls[-1]["json"]["profile_auth_subject"] == "auth0|user-1"

    fake_http.responses.append(FakeResponse(201, [{"id": 23}]))
    chat_message = store.create_chat_message("auth0|user-1", "Hello")
    assert chat_message == {"id": 23}
    assert fake_http.calls[-1]["json"] == {"profile_auth_subject": "auth0|user-1", "content": "Hello"}

    fake_http.responses.append(FakeResponse(201, [{"id": 24}]))
    talk_post = store.create_talk_post("auth0|user-1", "A reflection", "Cancer", "Full Moon", True)
    assert talk_post == {"id": 24}
    assert "display_name" not in fake_http.calls[-1]["json"]
    assert fake_http.calls[-1]["json"]["profile_auth_subject"] == "auth0|user-1"

    fake_http.responses.append(FakeResponse(204))
    fake_http.responses.append(FakeResponse(201))
    fake_http.responses.append(FakeResponse(200, [{"vote_type": "up"}, {"vote_type": "down"}, {"vote_type": "up"}]))
    fake_http.responses.append(FakeResponse(204))
    assert store.set_talk_vote("auth0|user-1", 24, "up") == (2, 1)
    assert fake_http.calls[-1]["json"] == {"upvotes": 2, "downvotes": 1}

    fake_http.responses.append(FakeResponse(204))
    store.hide_talk_post(24)
    assert fake_http.calls[-1]["json"] == {"is_hidden": True}

    moderation_start = len(fake_http.calls)
    fake_http.responses.append(FakeResponse(200, [{"auth_subject": "auth0|user-2", "username": "other_moon", "display_name": "Other Moon"}]))
    candidate = store.find_profile_for_moderation("@OTHER_MOON")
    assert candidate == {"auth_subject": "auth0|user-2", "username": "other_moon", "display_name": "Other Moon"}
    assert fake_http.calls[-1]["params"]["select"] == "auth_subject,username,display_name"

    fake_http.responses.append(FakeResponse(200, []))
    assert store.get_moderator_role("auth0|user-1") is None
    assert fake_http.calls[-1]["params"]["is_active"] == "eq.true"

    fake_http.responses.append(FakeResponse(201, [{"auth_subject": "auth0|user-1", "role": "founder"}]))
    founder_role = store.upsert_moderator_role("auth0|user-1", "founder", "auth0|user-1")
    assert founder_role["role"] == "founder"
    assert fake_http.calls[-1]["json"]["is_active"] is True

    fake_http.responses.append(FakeResponse(200, [{"id": 22, "profile_auth_subject": "auth0|user-2", "title": "Title", "content": "Body", "is_hidden": False}]))
    public_rows = store.list_moderation_content("board_post")
    assert public_rows[0]["id"] == 22
    assert fake_http.calls[-1]["params"]["select"] == "id,board_slug,profile_auth_subject,title,content,created_at,is_hidden"

    fake_http.responses.append(FakeResponse(204))
    store.set_moderation_visibility("board_post", 22, True)
    assert fake_http.calls[-1]["method"] == "PATCH"
    assert fake_http.calls[-1]["json"] == {"is_hidden": True}

    fake_http.responses.append(FakeResponse(201))
    store.log_moderation_action(
        "auth0|user-1", "board_post", "hide", target_id=22, target_auth_subject="auth0|user-2", reason="Test"
    )
    moderation_payload = fake_http.calls[-1]["json"]
    assert moderation_payload["target_type"] == "board_post"
    assert moderation_payload["action"] == "hide"
    assert "content" not in moderation_payload

    fake_http.responses.append(FakeResponse(204))
    store.delete_moderation_content("board_post", 22)
    assert fake_http.calls[-1]["method"] == "DELETE"
    assert fake_http.calls[-1]["url"].endswith("/board_posts")
    moderation_calls = fake_http.calls[moderation_start:]
    assert all("journal_entries" not in call["url"] for call in moderation_calls)

    fake_http.responses.append(FakeResponse(201, [{"id": 25}]))
    journal_entry = store.create_journal_entry("auth0|user-1", "Full Moon", "phase", "Private reflection")
    assert journal_entry == {"id": 25}
    assert fake_http.calls[-1]["json"] == {
        "profile_auth_subject": "auth0|user-1",
        "phase": "Full Moon",
        "prompt_type": "phase",
        "content": "Private reflection",
    }

    fake_http.responses.append(FakeResponse(200, []))
    assert store.list_journal_entries("auth0|user-1", limit=5) == []
    journal_query = fake_http.calls[-1]["params"]
    assert journal_query["profile_auth_subject"] == "eq.auth0|user-1"
    assert journal_query["select"] == "id,phase,prompt_type,content,created_at"
    assert "email" not in journal_query["select"]

    fake_http.responses.append(FakeResponse(201, [{"id": 31, "entry_date": "2026-08-28"}]))
    calendar_entry = store.upsert_calendar_entry(
        "auth0|user-1", "2026-08-28", "Observed a quiet evening.", "started", 3
    )
    assert calendar_entry["id"] == 31
    calendar_write = fake_http.calls[-1]
    assert calendar_write["params"] == {"on_conflict": "profile_auth_subject,entry_date"}
    assert calendar_write["json"] == {
        "profile_auth_subject": "auth0|user-1",
        "entry_date": "2026-08-28",
        "note": "Observed a quiet evening.",
        "cycle_marker": "started",
        "severity": 3,
    }

    fake_http.responses.append(FakeResponse(200, []))
    assert store.list_calendar_entries("auth0|user-1", "2026-08-01", "2026-09-01") == []
    calendar_query = fake_http.calls[-1]["params"]
    assert calendar_query["profile_auth_subject"] == "eq.auth0|user-1"
    assert calendar_query["entry_date"] == "lt.2026-09-01"
    assert calendar_query["select"] == "entry_date,note,cycle_marker,severity,updated_at"
    assert "email" not in calendar_query["select"]

    fake_http.responses.append(FakeResponse(204))
    store.delete_calendar_entry("auth0|user-1", "2026-08-28")
    calendar_delete = fake_http.calls[-1]
    assert calendar_delete["method"] == "DELETE"
    assert calendar_delete["params"] == {
        "profile_auth_subject": "eq.auth0|user-1",
        "entry_date": "eq.2026-08-28",
    }

    fake_http.responses.append(FakeResponse(201))
    store.log_migration_event(
        run_id="run-001",
        stage="profile_import",
        severity="info",
        entity="profiles",
        source_count=1,
        target_count=1,
        details={"note": "counts reconciled"},
    )
    migration_payload = fake_http.calls[-1]["json"]
    assert migration_payload["run_id"] == "run-001"
    assert migration_payload["source_count"] == 1
    assert "details" in migration_payload

    print("Supabase store backend, privacy filter, and migration-log tests passed.")


if __name__ == "__main__":
    main()
