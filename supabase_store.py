"""Server-side Supabase access foundation for the LunaTicK data migration.

This module deliberately uses the existing ``requests`` dependency rather than
adding a client SDK. It must run only inside Streamlit server code. A legacy
service-role key or modern Secret API key is read from Streamlit Secrets and is
never sent to a browser.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Mapping, MutableMapping

import requests

VALID_BACKENDS = {"sqlite", "supabase"}
PUBLIC_PROFILE_FIELDS = ("username", "display_name", "avatar", "bio")


class StorageConfigurationError(RuntimeError):
    """Raised when a requested storage backend lacks safe configuration."""


class SupabaseRequestError(RuntimeError):
    """Raised when Supabase rejects a server-side data request."""


def resolve_data_backend(
    configured_value: str | None = None,
    environment: Mapping[str, str] | None = None,
) -> str:
    """Return the selected data backend, defaulting safely to SQLite.

    ``configured_value`` is intended for a server-side settings source such as
    Streamlit Secrets. Environment configuration is supported for local tests.
    """
    environment = environment if environment is not None else os.environ
    raw_value = configured_value or environment.get("DATA_BACKEND", "sqlite")
    backend = str(raw_value).strip().lower()
    if backend not in VALID_BACKENDS:
        raise StorageConfigurationError(
            f"DATA_BACKEND must be one of {sorted(VALID_BACKENDS)}, not {raw_value!r}."
        )
    return backend


def data_backend_from_streamlit_secrets() -> str:
    """Read the backend switch from server-side Streamlit Secrets, if present."""
    try:
        import streamlit as st

        storage_config = st.secrets.get("storage", {})
        configured_value = storage_config.get("data_backend")
    except Exception:
        configured_value = None
    return resolve_data_backend(configured_value)


@dataclass(frozen=True)
class SupabaseSettings:
    """The only Supabase settings required by the server-side REST adapter."""

    url: str
    service_role_key: str

    @classmethod
    def from_mapping(cls, config: Mapping[str, Any]) -> "SupabaseSettings":
        url = str(config.get("url", "")).rstrip("/")
        service_role_key = str(config.get("service_role_key", ""))
        if not url.startswith("https://"):
            raise StorageConfigurationError("Supabase URL must begin with https://")
        if not service_role_key:
            raise StorageConfigurationError("Supabase service_role_key is required server-side.")
        return cls(url=url, service_role_key=service_role_key)

    @classmethod
    def from_streamlit_secrets(cls) -> "SupabaseSettings":
        try:
            import streamlit as st

            return cls.from_mapping(st.secrets.get("supabase", {}))
        except StorageConfigurationError:
            raise
        except Exception as error:
            raise StorageConfigurationError(
                "Supabase settings are unavailable. Add the [supabase] secret block before "
                "setting DATA_BACKEND to supabase."
            ) from error


class SupabaseStore:
    """Narrow server-only PostgREST adapter for the phased LunaTicK migration."""

    def __init__(self, settings: SupabaseSettings, http_session: Any = requests):
        self._settings = settings
        self._http = http_session

    @property
    def _headers(self) -> dict[str, str]:
        """Build documented server-only REST headers for either Supabase key model.

        Modern ``sb_secret_`` keys are opaque values and must be sent on the
        ``apikey`` header only. Legacy service-role JWTs continue to use both
        ``apikey`` and ``Authorization`` for compatibility with PostgREST.
        """
        api_key = self._settings.service_role_key
        headers = {
            "apikey": api_key,
            "Content-Type": "application/json",
        }
        if not api_key.startswith("sb_secret_"):
            headers["Authorization"] = f"Bearer {api_key}"
        return headers

    def _request(
        self,
        method: str,
        table: str,
        *,
        params: Mapping[str, str] | None = None,
        payload: Any = None,
        prefer: str | None = None,
    ) -> Any:
        headers: MutableMapping[str, str] = dict(self._headers)
        if prefer:
            headers["Prefer"] = prefer
        response = self._http.request(
            method,
            f"{self._settings.url}/rest/v1/{table}",
            headers=headers,
            params=params,
            json=payload,
            timeout=15,
        )
        if not response.ok:
            raise SupabaseRequestError(
                f"Supabase {method} {table} failed with {response.status_code}: {response.text[:500]}"
            )
        if response.status_code == 204 or not response.content:
            return None
        return response.json()

    def healthcheck(self) -> bool:
        """Verify that the target schema responds without returning record data."""
        self._request("GET", "profiles", params={"select": "auth_subject", "limit": "1"})
        return True

    def upsert_profile(self, profile: Mapping[str, Any]) -> dict[str, Any]:
        """Upsert a canonical profile strictly by immutable ``auth_subject``."""
        auth_subject = str(profile.get("auth_subject", "")).strip()
        if not auth_subject:
            raise ValueError("auth_subject is required for profile upsert.")
        rows = self._request(
            "POST",
            "profiles",
            params={"on_conflict": "auth_subject"},
            payload=dict(profile),
            prefer="resolution=merge-duplicates,return=representation",
        )
        if not isinstance(rows, list) or len(rows) != 1:
            raise SupabaseRequestError("Profile upsert did not return exactly one profile row.")
        return rows[0]

    def get_profile_by_auth_subject(self, auth_subject: str) -> dict[str, Any] | None:
        rows = self._request(
            "GET",
            "profiles",
            params={
                "select": "auth_subject,user_hash,username,display_name,avatar,bio,email,"
                "birth_date,birth_time,birth_place,lat,lon,utc_offset,hd_profile,hd_authority",
                "auth_subject": f"eq.{auth_subject}",
                "limit": "1",
            },
        )
        return rows[0] if rows else None

    def get_public_profile_by_username(self, username: str) -> dict[str, Any] | None:
        """Return only fields approved by the public-profile privacy matrix."""
        normalized_username = username.strip().lower().lstrip("@")
        rows = self._request(
            "GET",
            "profiles",
            params={
                "select": ",".join(PUBLIC_PROFILE_FIELDS),
                "username": f"eq.{normalized_username}",
                "limit": "1",
            },
        )
        if not rows:
            return None
        return {field: rows[0].get(field) for field in PUBLIC_PROFILE_FIELDS}

    def username_is_available(self, username: str, auth_subject: str) -> bool:
        """Check uniqueness server-side while allowing the owner to retain a handle."""
        normalized_username = username.strip().lower().lstrip("@")
        rows = self._request(
            "GET",
            "profiles",
            params={
                "select": "auth_subject",
                "username": f"eq.{normalized_username}",
                "auth_subject": f"neq.{auth_subject}",
                "limit": "1",
            },
        )
        return not rows

    def log_migration_event(
        self,
        *,
        run_id: str,
        stage: str,
        severity: str,
        entity: str,
        source_count: int | None = None,
        target_count: int | None = None,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        """Write non-sensitive reconciliation data to the server-only migration log."""
        if severity not in {"info", "warning", "error"}:
            raise ValueError("severity must be info, warning, or error")
        self._request(
            "POST",
            "migration_log",
            payload={
                "run_id": run_id,
                "stage": stage,
                "severity": severity,
                "entity": entity,
                "source_count": source_count,
                "target_count": target_count,
                "details": dict(details or {}),
            },
            prefer="return=minimal",
        )
