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

    fake_http.responses.append(FakeResponse(200, []))
    assert store.username_is_available("moon_orbit", "auth0|user-1") is True
    username_query = fake_http.calls[-1]["params"]
    assert username_query == {
        "select": "auth_subject",
        "username": "eq.moon_orbit",
        "auth_subject": "neq.auth0|user-1",
        "limit": "1",
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
