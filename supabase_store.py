"""Server-side Supabase access foundation for the LunaTicK data migration.

This module deliberately uses the existing ``requests`` dependency rather than
adding a client SDK. It must run only inside Streamlit server code. A legacy
service-role key or modern Secret API key is read from Streamlit Secrets and is
never sent to a browser.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, MutableMapping

import requests

VALID_BACKENDS = {"sqlite", "supabase"}
PUBLIC_PROFILE_FIELDS = ("username", "display_name", "avatar", "bio")
PUBLIC_DISPLAY_NAME_FALLBACK = "Moon Wanderer"


def public_display_name(value: Any) -> str:
    """Return a public-safe display name, never an email-like value."""
    name = str(value or "").strip()[:48]
    return name if name and "@" not in name else PUBLIC_DISPLAY_NAME_FALLBACK
BACKUP_TABLES = frozenset(
    {
        "profiles",
        "journal_entries",
        "boards",
        "board_posts",
        "chat_messages",
        "lunatick_talk_posts",
        "lunatick_talk_comments",
        "user_votes",
        "card_trades",
        "migration_log",
        "moderator_roles",
        "moderation_actions",
    }
)
CARD_PROFILE_FIELDS = (
    "auth_subject",
    "user_hash",
    "username",
    "display_name",
    "avatar",
    "bio",
    "birth_date",
    "birth_time",
    "birth_place",
    "lat",
    "lon",
    "utc_offset",
)
PROFILE_MUTABLE_FIELDS = frozenset(
    {
        "username",
        "display_name",
        "avatar",
        "bio",
        "email",
        "birth_date",
        "birth_time",
        "birth_place",
        "lat",
        "lon",
        "utc_offset",
    }
)


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

    def list_backup_rows(
        self,
        table: str,
        columns: str,
        *,
        order: str,
        limit: int = 1000,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Read one ordered backup page from an explicitly approved LunaTicK table."""
        if table not in BACKUP_TABLES:
            raise ValueError(f"{table!r} is not approved for LunaTicK backup export.")
        page_size = max(1, min(int(limit), 1000))
        page_offset = max(0, int(offset))
        rows = self._request(
            "GET",
            table,
            params={
                "select": columns,
                "order": order,
                "limit": str(page_size),
                "offset": str(page_offset),
            },
        )
        return list(rows or [])

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

    def update_profile_fields(
        self, auth_subject: str, fields: Mapping[str, Any]
    ) -> dict[str, Any]:
        """Patch approved profile fields by immutable subject without an identity upsert."""
        subject = str(auth_subject or "").strip()
        if not subject:
            raise ValueError("auth_subject is required for a profile update.")
        payload = {key: value for key, value in dict(fields).items() if key in PROFILE_MUTABLE_FIELDS}
        if not payload:
            raise ValueError("At least one approved profile field is required for an update.")
        rows = self._request(
            "PATCH",
            "profiles",
            params={"auth_subject": f"eq.{subject}"},
            payload=payload,
            prefer="return=representation",
        )
        if not isinstance(rows, list) or len(rows) != 1:
            raise SupabaseRequestError("Profile update did not return exactly one profile row.")
        return rows[0]

    def list_card_profiles(self, exclude_auth_subject: str) -> list[dict[str, Any]]:
        """Return private card inputs server-side for derived, non-identifying card summaries."""
        subject = str(exclude_auth_subject or "").strip()
        rows = self._request(
            "GET",
            "profiles",
            params={
                "select": ",".join(CARD_PROFILE_FIELDS),
                "birth_date": "not.is.null",
                "auth_subject": f"neq.{subject}",
                "order": "created_at.asc",
                "limit": "100",
            },
        )
        return list(rows or [])

    def has_pending_card_trade(self, sender_auth_subject: str, receiver_auth_subject: str) -> bool:
        """Detect a duplicate pending card trade before creating another request."""
        rows = self._request(
            "GET",
            "card_trades",
            params={
                "select": "id",
                "sender_auth_subject": f"eq.{sender_auth_subject}",
                "receiver_auth_subject": f"eq.{receiver_auth_subject}",
                "status": "eq.pending",
                "limit": "1",
            },
        )
        return bool(rows)

    def create_card_trade(
        self, sender_auth_subject: str, receiver_auth_subject: str, message: str = ""
    ) -> dict[str, Any]:
        """Create one pending card trade using canonical immutable profile subjects."""
        rows = self._request(
            "POST",
            "card_trades",
            payload={
                "sender_auth_subject": sender_auth_subject,
                "receiver_auth_subject": receiver_auth_subject,
                "message": message.strip(),
                "status": "pending",
            },
            prefer="return=representation",
        )
        if not isinstance(rows, list) or len(rows) != 1:
            raise SupabaseRequestError("Card trade creation did not return exactly one row.")
        return rows[0]

    def list_card_trades(self, auth_subject: str, direction: str = "all") -> list[dict[str, Any]]:
        """List the active profile's card trades without joining private profile fields."""
        filters: dict[str, str] = {
            "select": "id,sender_auth_subject,receiver_auth_subject,message,status,created_at",
            "order": "created_at.desc",
            "limit": "100",
        }
        if direction == "incoming":
            filters["receiver_auth_subject"] = f"eq.{auth_subject}"
        elif direction == "outgoing":
            filters["sender_auth_subject"] = f"eq.{auth_subject}"
        elif direction == "all":
            filters["or"] = (
                f"(sender_auth_subject.eq.{auth_subject},receiver_auth_subject.eq.{auth_subject})"
            )
        else:
            raise ValueError("Card-trade direction must be incoming, outgoing, or all.")
        return list(self._request("GET", "card_trades", params=filters) or [])

    def resolve_card_trade(
        self, trade_id: int, receiver_auth_subject: str, accept: bool
    ) -> bool:
        """Resolve only the specified receiver's pending card trade."""
        status = "accepted" if accept else "declined"
        rows = self._request(
            "PATCH",
            "card_trades",
            params={
                "id": f"eq.{int(trade_id)}",
                "receiver_auth_subject": f"eq.{receiver_auth_subject}",
                "status": "eq.pending",
            },
            payload={"status": status, "resolved_at": datetime.now(timezone.utc).isoformat()},
            prefer="return=representation",
        )
        return bool(rows)

    def list_accepted_card_contacts(self, auth_subject: str) -> list[str]:
        """Return counterpart subjects from accepted card trades for server-side card summaries."""
        rows = self._request(
            "GET",
            "card_trades",
            params={
                "select": "sender_auth_subject,receiver_auth_subject",
                "status": "eq.accepted",
                "or": (
                    f"(sender_auth_subject.eq.{auth_subject},receiver_auth_subject.eq.{auth_subject})"
                ),
                "limit": "100",
            },
        )
        contacts: set[str] = set()
        for row in rows or []:
            sender = str(row.get("sender_auth_subject") or "")
            receiver = str(row.get("receiver_auth_subject") or "")
            counterpart = receiver if sender == auth_subject else sender
            if counterpart:
                contacts.add(counterpart)
        return sorted(contacts)

    def get_public_profile_summaries(
        self, auth_subjects: list[str] | tuple[str, ...] | set[str]
    ) -> dict[str, dict[str, Any]]:
        """Return minimal display-safe profile fields for server-rendered Community authors."""
        subjects = sorted({str(subject).strip() for subject in auth_subjects if str(subject).strip()})
        if not subjects:
            return {}
        rows = self._request(
            "GET",
            "profiles",
            params={
                "select": "auth_subject,username,display_name,avatar",
                "auth_subject": f"in.({','.join(subjects)})",
                "limit": str(min(len(subjects), 100)),
            },
        )
        return {
            str(row["auth_subject"]): {
                "username": row.get("username"),
                "display_name": public_display_name(row.get("display_name")),
                "avatar": row.get("avatar"),
            }
            for row in rows or []
        }

    def seed_boards(self, boards: list[Mapping[str, str]] | tuple[Mapping[str, str], ...]) -> None:
        """Create or refresh the fixed Community board catalog without importing SQLite data."""
        payload = [
            {
                "slug": str(board["slug"]),
                "name": str(board["name"]),
                "description": str(board.get("description") or ""),
            }
            for board in boards
        ]
        if not payload:
            return
        self._request(
            "POST",
            "boards",
            params={"on_conflict": "slug"},
            payload=payload,
            prefer="resolution=merge-duplicates,return=minimal",
        )

    def list_boards(self) -> list[dict[str, Any]]:
        """Return the fixed board catalog in a stable server-side order."""
        return list(
            self._request(
                "GET",
                "boards",
                params={"select": "slug,name,description", "order": "slug.asc", "limit": "100"},
            )
            or []
        )

    def list_board_post_slugs(self) -> list[str]:
        """Return visible post board slugs for server-side board-count calculation."""
        rows = self._request(
            "GET",
            "board_posts",
            params={"select": "board_slug", "is_hidden": "eq.false", "limit": "1000"},
        )
        return [str(row.get("board_slug") or "") for row in rows or []]

    def create_board_post(
        self, board_slug: str, profile_auth_subject: str, title: str, content: str
    ) -> dict[str, Any]:
        """Create a board post with only the immutable profile subject as author identity."""
        rows = self._request(
            "POST",
            "board_posts",
            payload={
                "board_slug": board_slug,
                "profile_auth_subject": profile_auth_subject,
                "title": title,
                "content": content,
            },
            prefer="return=representation",
        )
        if not isinstance(rows, list) or len(rows) != 1:
            raise SupabaseRequestError("Board post creation did not return exactly one row.")
        return rows[0]

    def list_board_posts(self, board_slug: str | None = None, limit: int = 30) -> list[dict[str, Any]]:
        """List visible board posts without joining private profile columns."""
        params: dict[str, str] = {
            "select": "id,board_slug,profile_auth_subject,title,content,created_at",
            "is_hidden": "eq.false",
            "order": "created_at.desc",
            "limit": str(max(1, min(int(limit), 100))),
        }
        if board_slug:
            params["board_slug"] = f"eq.{board_slug}"
        return list(self._request("GET", "board_posts", params=params) or [])

    def create_chat_message(self, profile_auth_subject: str, content: str) -> dict[str, Any]:
        """Create one Community chat message tied only to its canonical profile subject."""
        rows = self._request(
            "POST",
            "chat_messages",
            payload={"profile_auth_subject": profile_auth_subject, "content": content},
            prefer="return=representation",
        )
        if not isinstance(rows, list) or len(rows) != 1:
            raise SupabaseRequestError("Chat message creation did not return exactly one row.")
        return rows[0]

    def list_chat_messages(self, limit: int = 50) -> list[dict[str, Any]]:
        """List visible chat messages in chronological display order."""
        return list(
            self._request(
                "GET",
                "chat_messages",
                params={
                    "select": "id,profile_auth_subject,content,created_at",
                    "is_hidden": "eq.false",
                    "order": "created_at.desc",
                    "limit": str(max(1, min(int(limit), 100))),
                },
            )
            or []
        )

    def create_talk_post(
        self,
        profile_auth_subject: str,
        content: str,
        user_moon_sign: str | None,
        current_moon_phase: str | None,
        is_anonymous: bool,
        image_path: str | None = None,
    ) -> dict[str, Any]:
        """Create one LunaTicK Talk post without persisting a display-name snapshot."""
        rows = self._request(
            "POST",
            "lunatick_talk_posts",
            payload={
                "profile_auth_subject": profile_auth_subject,
                "content": content,
                "user_moon_sign": user_moon_sign,
                "current_moon_phase": current_moon_phase,
                "is_anonymous": bool(is_anonymous),
                "image_path": image_path,
            },
            prefer="return=representation",
        )
        if not isinstance(rows, list) or len(rows) != 1:
            raise SupabaseRequestError("LunaTicK Talk post creation did not return exactly one row.")
        return rows[0]

    def list_talk_posts(
        self, limit: int = 20, phase_filter: str | None = None
    ) -> list[dict[str, Any]]:
        """List visible LunaTicK Talk posts, including only server-side author subjects."""
        params: dict[str, str] = {
            "select": (
                "id,profile_auth_subject,user_moon_sign,current_moon_phase,content,image_path,"
                "upvotes,downvotes,created_at,is_anonymous,is_hidden"
            ),
            "is_hidden": "eq.false",
            "order": "created_at.desc",
            "limit": str(max(1, min(int(limit), 100))),
        }
        if phase_filter:
            params["current_moon_phase"] = f"eq.{phase_filter}"
        return list(self._request("GET", "lunatick_talk_posts", params=params) or [])

    def create_talk_comment(
        self, post_id: int, profile_auth_subject: str, content: str, is_anonymous: bool
    ) -> dict[str, Any]:
        """Create one Talk comment linked to the post and immutable author subject."""
        rows = self._request(
            "POST",
            "lunatick_talk_comments",
            payload={
                "post_id": int(post_id),
                "profile_auth_subject": profile_auth_subject,
                "content": content,
                "is_anonymous": bool(is_anonymous),
            },
            prefer="return=representation",
        )
        if not isinstance(rows, list) or len(rows) != 1:
            raise SupabaseRequestError("LunaTicK Talk comment creation did not return exactly one row.")
        return rows[0]

    def list_talk_comments(self, post_id: int) -> list[dict[str, Any]]:
        """List visible comments for one Talk post in chronological order."""
        return list(
            self._request(
                "GET",
                "lunatick_talk_comments",
                params={
                    "select": (
                        "id,post_id,profile_auth_subject,content,created_at,upvotes,downvotes,"
                        "is_anonymous,is_hidden"
                    ),
                    "post_id": f"eq.{int(post_id)}",
                    "is_hidden": "eq.false",
                    "order": "created_at.asc",
                    "limit": "200",
                },
            )
            or []
        )

    def get_talk_vote(self, profile_auth_subject: str, post_id: int) -> str | None:
        """Return the active profile's vote on one post, if present."""
        rows = self._request(
            "GET",
            "user_votes",
            params={
                "select": "vote_type",
                "profile_auth_subject": f"eq.{profile_auth_subject}",
                "post_id": f"eq.{int(post_id)}",
                "limit": "1",
            },
        )
        return str(rows[0].get("vote_type")) if rows else None

    def set_talk_vote(
        self, profile_auth_subject: str, post_id: int, vote_type: str | None
    ) -> tuple[int, int]:
        """Replace one profile's post vote and reconcile denormalized vote counts server-side."""
        if vote_type not in {"up", "down", None}:
            raise ValueError("vote_type must be up, down, or None")
        self._request(
            "DELETE",
            "user_votes",
            params={
                "profile_auth_subject": f"eq.{profile_auth_subject}",
                "post_id": f"eq.{int(post_id)}",
            },
            prefer="return=minimal",
        )
        if vote_type:
            self._request(
                "POST",
                "user_votes",
                payload={
                    "profile_auth_subject": profile_auth_subject,
                    "post_id": int(post_id),
                    "vote_type": vote_type,
                },
                prefer="return=minimal",
            )
        votes = self._request(
            "GET",
            "user_votes",
            params={"select": "vote_type", "post_id": f"eq.{int(post_id)}", "limit": "1000"},
        )
        upvotes = sum(1 for vote in votes or [] if vote.get("vote_type") == "up")
        downvotes = sum(1 for vote in votes or [] if vote.get("vote_type") == "down")
        self._request(
            "PATCH",
            "lunatick_talk_posts",
            params={"id": f"eq.{int(post_id)}"},
            payload={"upvotes": upvotes, "downvotes": downvotes},
            prefer="return=minimal",
        )
        return upvotes, downvotes

    def create_journal_entry(
        self, profile_auth_subject: str, phase: str, prompt_type: str, content: str
    ) -> dict[str, Any]:
        """Create one private reflection for its canonical owner profile."""
        rows = self._request(
            "POST",
            "journal_entries",
            payload={
                "profile_auth_subject": profile_auth_subject,
                "phase": phase,
                "prompt_type": prompt_type,
                "content": content,
            },
            prefer="return=representation",
        )
        if not isinstance(rows, list) or len(rows) != 1:
            raise SupabaseRequestError("Journal entry creation did not return exactly one row.")
        return rows[0]

    def list_journal_entries(self, profile_auth_subject: str, limit: int = 5) -> list[dict[str, Any]]:
        """List only the active profile's private reflections, newest first."""
        return list(
            self._request(
                "GET",
                "journal_entries",
                params={
                    "select": "id,phase,prompt_type,content,created_at",
                    "profile_auth_subject": f"eq.{profile_auth_subject}",
                    "order": "created_at.desc",
                    "limit": str(max(1, min(int(limit), 100))),
                },
            )
            or []
        )

    def hide_talk_post(self, post_id: int) -> None:
        """Mark one Talk post hidden through the server-only moderation path."""
        self._request(
            "PATCH",
            "lunatick_talk_posts",
            params={"id": f"eq.{int(post_id)}"},
            payload={"is_hidden": True},
            prefer="return=minimal",
        )

    def find_profile_for_moderation(self, username: str) -> dict[str, Any] | None:
        """Resolve a prospective moderator by public handle without reading private profile data."""
        normalized_username = username.strip().lower().lstrip("@")
        rows = self._request(
            "GET",
            "profiles",
            params={
                "select": "auth_subject,username,display_name",
                "username": f"eq.{normalized_username}",
                "limit": "1",
            },
        )
        return rows[0] if rows else None

    def get_moderator_role(self, auth_subject: str) -> dict[str, Any] | None:
        """Return the active server-side moderation role for one canonical identity."""
        rows = self._request(
            "GET",
            "moderator_roles",
            params={
                "select": "auth_subject,role,is_active,granted_by_auth_subject,granted_at,revoked_at",
                "auth_subject": f"eq.{auth_subject}",
                "is_active": "eq.true",
                "limit": "1",
            },
        )
        return rows[0] if rows else None

    def upsert_moderator_role(
        self, auth_subject: str, role: str, granted_by_auth_subject: str
    ) -> dict[str, Any]:
        """Grant or reactivate a founder/moderator role through the server-only path."""
        if role not in {"founder", "moderator"}:
            raise ValueError("role must be founder or moderator")
        rows = self._request(
            "POST",
            "moderator_roles",
            params={"on_conflict": "auth_subject"},
            payload={
                "auth_subject": auth_subject,
                "role": role,
                "is_active": True,
                "granted_by_auth_subject": granted_by_auth_subject,
                "revoked_at": None,
            },
            prefer="resolution=merge-duplicates,return=representation",
        )
        if not isinstance(rows, list) or len(rows) != 1:
            raise SupabaseRequestError("Moderator role update did not return exactly one row.")
        return rows[0]

    def revoke_moderator_role(self, auth_subject: str) -> None:
        """Deactivate a delegated role without deleting its authorization history."""
        self._request(
            "PATCH",
            "moderator_roles",
            params={"auth_subject": f"eq.{auth_subject}"},
            payload={"is_active": False, "revoked_at": datetime.now(timezone.utc).isoformat()},
            prefer="return=minimal",
        )

    def list_moderator_roles(self, limit: int = 100) -> list[dict[str, Any]]:
        """List role records for the protected moderator-management console."""
        return list(
            self._request(
                "GET",
                "moderator_roles",
                params={
                    "select": "auth_subject,role,is_active,granted_by_auth_subject,granted_at,revoked_at",
                    "order": "granted_at.asc",
                    "limit": str(max(1, min(int(limit), 100))),
                },
            )
            or []
        )

    def list_moderation_actions(self, limit: int = 100) -> list[dict[str, Any]]:
        """List accountability metadata only; this never returns moderated content text."""
        return list(
            self._request(
                "GET",
                "moderation_actions",
                params={
                    "select": "id,moderator_auth_subject,target_type,target_id,target_auth_subject,action,reason,details,created_at",
                    "order": "created_at.desc",
                    "limit": str(max(1, min(int(limit), 100))),
                },
            )
            or []
        )

    def list_moderation_content(self, target_type: str, limit: int = 100) -> list[dict[str, Any]]:
        """List public Community records for a protected moderation console only."""
        catalog = {
            "board_post": (
                "board_posts",
                "id,board_slug,profile_auth_subject,title,content,created_at,is_hidden",
            ),
            "chat_message": (
                "chat_messages",
                "id,profile_auth_subject,content,created_at,is_hidden",
            ),
            "talk_post": (
                "lunatick_talk_posts",
                "id,profile_auth_subject,content,current_moon_phase,created_at,is_anonymous,is_hidden",
            ),
            "talk_comment": (
                "lunatick_talk_comments",
                "id,post_id,profile_auth_subject,content,created_at,is_anonymous,is_hidden",
            ),
        }
        try:
            table, columns = catalog[target_type]
        except KeyError as error:
            raise ValueError("Unsupported public moderation target type.") from error
        return list(
            self._request(
                "GET",
                table,
                params={
                    "select": columns,
                    "order": "created_at.desc",
                    "limit": str(max(1, min(int(limit), 100))),
                },
            )
            or []
        )

    def set_moderation_visibility(self, target_type: str, target_id: int, is_hidden: bool) -> None:
        """Hide or restore one public Community record without accessing private data."""
        tables = {
            "board_post": "board_posts",
            "chat_message": "chat_messages",
            "talk_post": "lunatick_talk_posts",
            "talk_comment": "lunatick_talk_comments",
        }
        try:
            table = tables[target_type]
        except KeyError as error:
            raise ValueError("Unsupported public moderation target type.") from error
        self._request(
            "PATCH",
            table,
            params={"id": f"eq.{int(target_id)}"},
            payload={"is_hidden": bool(is_hidden)},
            prefer="return=minimal",
        )

    def delete_moderation_content(self, target_type: str, target_id: int) -> None:
        """Permanently delete one public Community record after an audited confirmation."""
        tables = {
            "board_post": "board_posts",
            "chat_message": "chat_messages",
            "talk_post": "lunatick_talk_posts",
            "talk_comment": "lunatick_talk_comments",
        }
        try:
            table = tables[target_type]
        except KeyError as error:
            raise ValueError("Unsupported public moderation target type.") from error
        self._request(
            "DELETE",
            table,
            params={"id": f"eq.{int(target_id)}"},
            prefer="return=minimal",
        )

    def log_moderation_action(
        self,
        moderator_auth_subject: str,
        target_type: str,
        action: str,
        *,
        target_id: int | None = None,
        target_auth_subject: str | None = None,
        reason: str = "",
        details: Mapping[str, Any] | None = None,
    ) -> None:
        """Write minimal moderator accountability metadata without copying content."""
        if target_type not in {"board_post", "chat_message", "talk_post", "talk_comment", "moderator_role"}:
            raise ValueError("Unsupported moderation target type.")
        if action not in {"hide", "restore", "delete", "grant_role", "revoke_role"}:
            raise ValueError("Unsupported moderation action.")
        if target_id is None and not target_auth_subject:
            raise ValueError("A moderation target id or subject is required.")
        self._request(
            "POST",
            "moderation_actions",
            payload={
                "moderator_auth_subject": moderator_auth_subject,
                "target_type": target_type,
                "target_id": int(target_id) if target_id is not None else None,
                "target_auth_subject": target_auth_subject,
                "action": action,
                "reason": reason.strip()[:240],
                "details": dict(details or {}),
            },
            prefer="return=minimal",
        )

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
        profile = {field: rows[0].get(field) for field in PUBLIC_PROFILE_FIELDS}
        profile["display_name"] = public_display_name(profile.get("display_name"))
        return profile

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
