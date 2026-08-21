# LunaTicK: SQLite-to-Supabase Migration Plan

**Status:** Planning only. No Supabase schema, credentials, migrations, or application writes have been changed.

## Executive Decision

LunaTicK should move from its local `lunatick.db` SQLite file to the existing, active **`lunatick`** Supabase project before a wider alpha invitation. The currently connected project is healthy and its public schema is empty, so it is a clean destination rather than a legacy system requiring a risky merge.

The database export is **not a current blocker**. The codebase is already protected in GitHub, the app remains a single-user alpha, and no shared production data needs preservation before the transition. The optional owner-gated snapshot utility is present in the repository but is not activated because no owner secret was configured. No open export path was pushed.

> **Cutover timing clarification:** This plan assumes that the Supabase cutover completes **before any tester invitation**. That is the preferred path. The current single-user state means Phase C has one identity to reconcile and no other person’s writing, profile, or Community activity at risk during the transition.

> **Architecture after migration:** Auth0 verifies identity, Streamlit restores the native session, and Supabase becomes the durable system of record for LunaTicK data. Auth0 is not being replaced.

## Why Move Now

SQLite is correct for a prototype, but the Streamlit Community Cloud runtime is not a durable shared database host. A Supabase PostgreSQL database gives LunaTicK persistent profiles, conversations, cards, journals, and community records across Streamlit restarts and future deployments. It also gives the app one shared source of truth when more than one person participates.

| Current limitation | Supabase outcome |
|---|---|
| Local SQLite exists inside a short-lived app runtime. | Persistent managed PostgreSQL data store. |
| Community features can lose shared state after rebuilds. | Shared multi-user records survive deployment changes. |
| Several modules create overlapping profile tables. | One canonical `profiles` table. |
| Public profile lookup relies on a local file. | Indexed, durable username lookup. |
| Future moderation and privacy controls would be scattered. | Centralized schema, policy, audit, and migration history. |

## Existing Storage Inventory

The following table families are declared in the current SQLite source. The first five are the active launch-critical scope.

| SQLite source | Current tables | Target treatment | Priority |
|---|---|---|---:|
| `auth.py` | `oidc_identities` | Consolidate into canonical `profiles`; preserve `auth_subject`, `user_hash`, username, display name, avatar, bio, and private email. | 1 |
| `cosmic_cards.py` | `user_profiles`, `card_trades` | Consolidate profile/chart fields into `profiles`; migrate trades separately. | 1 |
| `journal.py` | `journal_entries` | Dedicated private `journal_entries` table. | 2 |
| `boards.py` | `boards`, `board_posts` | Preserve board catalog and community posts. | 2 |
| `chat_room.py` | `chat_messages` | Durable community chat history. | 2 |
| `lunatick_talk_db.py` | `lunatick_talk_posts`, `lunatick_talk_comments`, duplicate `user_profiles`, `user_votes` | Retain social/voting records and eliminate duplicate profile storage. | 2 |
| `community_feed.py` | `community_posts`, `community_comments`, `community_flags`, `community_consent` | Keep only if this alternate feed is reactivated; otherwise defer rather than migrate dormant tables. | 3 |

## Target Data Model

The migration begins with a **single canonical profile row** per Auth0 identity. No public profile call should ever return private email, birth details, latitude/longitude, or identity-provider identifiers.

### Identity-Key Decision

`profiles.auth_subject` is the **primary key**. It is the immutable Auth0 subject (`sub`) received by the Streamlit server after native sign-in, and every user-owned record references it through `profile_auth_subject`. `profiles.user_hash` is retained only as a legacy migration and compatibility identifier: it is **not unique**, is never an authorization key, and is not exposed to the browser.

| Target table | Core fields | Privacy and purpose |
|---|---|---|
| `profiles` | `auth_subject` (PK), `user_hash` (legacy, non-unique), `username`, `display_name`, `avatar`, `bio`, `email`, birth/chart fields, timestamps | Canonical identity and profile record. Only selected presence fields are public. |
| `journal_entries` | `id`, `profile_auth_subject`, `phase`, `prompt_type`, `content`, timestamps | Strictly private writing. |
| `boards` | `slug`, `name`, `description` | Shared board catalog. |
| `board_posts` | `id`, `board_slug`, `profile_auth_subject`, `title`, `content`, timestamps | Community discussion. |
| `chat_messages` | `id`, `profile_auth_subject`, `content`, timestamps | Community chat. |
| `lunatick_talk_posts` | `id`, `profile_auth_subject`, `content`, moon metadata, anonymity/moderation fields, timestamps | Long-form social posts. |
| `lunatick_talk_comments` | `id`, `post_id`, `profile_auth_subject`, `content`, anonymity/moderation fields, timestamps | Comments. |
| `user_votes` | `profile_auth_subject`, `post_id`, `vote_type`, timestamps | One vote per user/post. |
| `card_trades` | `id`, `sender_auth_subject`, `receiver_auth_subject`, `message`, `status`, timestamps | Card exchange workflow. |
| `migration_log` | `id`, `run_id`, `stage`, `severity`, `entity`, `source_count`, `target_count`, `details`, timestamps | Server-only migration audit trail. |

The final schema uses PostgreSQL foreign keys, UTC timestamps, and an exact primary-key constraint named `idx_profiles_auth_subject`. PostgreSQL creates the required unique B-tree for this primary key, so no redundant second index is created. Existing SQLite integer IDs may be retained for imported social records where useful; all new records use PostgreSQL identity IDs or UUIDs consistently.

### Column-Level Privacy Matrix

| Table and columns | Classification | Exposure rule |
|---|---|---|
| `profiles.username`, `display_name`, `avatar`, `bio` | **public** | May be returned by public-profile lookup and displayed with authored Community content. |
| `profiles.created_at` | **authenticated** | Available only to signed-in product views if a future feature needs it; not included in default public lookup. |
| `profiles.birth_date`, `birth_time`, `birth_place`, `lat`, `lon`, `utc_offset`, Human Design fields, Cosmic Card inputs | **owner-only** | Read and written only by the matching `auth_subject`. |
| `profiles.auth_subject`, `user_hash`, `email` | **server-only** | Never returned to the browser through profile APIs; used solely for server-side identity resolution, migration, and auditing. |
| `journal_entries.profile_auth_subject`, `phase`, `prompt_type`, `content`, timestamps | **owner-only** | Only the journal owner may read or write the row. |
| `boards.slug`, `name`, `description`; published Community titles, content, timestamps, selected author-presence fields | **authenticated** | Available to signed-in Community participants; future anonymous public viewing is a separate product decision. |
| `chat_messages.content`, `lunatick_talk_posts.content`, `lunatick_talk_comments.content` | **authenticated** | Visible to signed-in Community participants, subject to moderation state. |
| Community moderation flags, hidden-state internals, vote attribution, report counts | **server-only** | Excluded from normal client responses; available only to trusted server-side moderation workflows. |
| `card_trades.sender_auth_subject`, `receiver_auth_subject`, `message`, `status` | **owner-only** | Visible only to the trade sender and receiver. |
| `migration_log` all columns | **server-only** | No browser access; used for migration reconciliation and incident review. |

### Critical Indexes and Constraints

| Name | Definition and purpose |
|---|---|
| `idx_profiles_auth_subject` | `PRIMARY KEY (auth_subject)` on `profiles`; immutable identity lookup and foreign-key target. |
| `idx_profiles_username` | Unique B-tree on normalized `username`; fast public-handle resolution and duplicate prevention. |
| `idx_journal_profile_phase` | `(profile_auth_subject, phase, created_at DESC)`; owner journal retrieval by lunar phase. |
| `idx_talk_posts_phase` | `(phase, created_at DESC)`; current-phase LunaTicK Talk feed ordering. |
| `idx_talk_comments_post_id` | `(post_id, created_at ASC)`; efficient comment-thread retrieval. |
| `idx_board_posts_board_created` / `idx_board_posts_profile_auth_subject` | Board timelines and profile foreign-key coverage. |
| `idx_chat_messages_created` / `idx_chat_messages_profile_auth_subject` | Recent chat retrieval and profile foreign-key coverage. |
| `idx_talk_posts_profile_auth_subject` / `idx_talk_comments_profile_auth_subject` | Author foreign-key coverage for social records. |
| `idx_user_votes_post_id` | Vote-to-post foreign-key coverage. |
| `idx_card_trades_sender_status` / `idx_card_trades_receiver_status` | `(sender_auth_subject, status)` and `(receiver_auth_subject, status)`; inbox and outbox views. |
| `user_votes` constraint | `PRIMARY KEY (profile_auth_subject, post_id)`; exactly one current vote per user and post. |

### Card Trade Lifecycle

`card_trades.status` is a constrained enum-like value with these states: `pending`, `accepted`, `declined`, `completed`, and `cancelled`.

| State | Meaning | Allowed transition summary |
|---|---|---|
| `pending` | Sender created a trade request. | Receiver may accept or decline; sender may cancel. |
| `accepted` | Receiver accepted the request. | Either participant may mark completed; cancellation is permitted only if the exchange has not completed. |
| `declined` | Receiver rejected the request. | Terminal. |
| `completed` | The exchange was fulfilled. | Terminal. |
| `cancelled` | The sender withdrew, or a participant cancelled an uncompleted accepted request. | Terminal. |

### Migration Logging

Each importer run receives a UUID `run_id`. The migration writes a `migration_log` row at the start and completion of each entity stage, plus an `error` row for every failed source record without storing sensitive payload content. Each record includes `stage`, `severity`, `entity`, source and target counts, a machine-readable `details` JSON object, and UTC timestamps. The importer exits non-zero if reconciliation counts differ or any error-level event exists. This makes migration results inspectable, repeatable, and reversible without using free-form server logs as the source of truth.

## Authentication and Access Boundary

LunaTicK should retain its current Auth0 plus Streamlit native OpenID Connect flow. Streamlit gives the app an authenticated `auth_subject`; the server-side Python code maps that subject to one `profiles` row.

During alpha, the Streamlit server may use a Supabase service credential stored only in Streamlit Community Cloud Secrets. The browser must never receive a service-role key. Because service-role requests bypass Row Level Security, the server-side data-access layer must always query and write using the authenticated caller’s `auth_subject` or resolved `profile_id`. Before any direct browser-to-Supabase calls are introduced, a separate Supabase JWT and Row Level Security design is required. [1] [2]

## Step-by-Step Delivery Plan

### Phase A — Create the Data Access Foundation

1. Add a small `supabase_store.py` repository module rather than putting raw API calls throughout the interface modules.
2. Add the minimum secure deployment secrets only after the user confirms the target project and credentials strategy: Supabase URL plus a **server-only** key.
3. Add a `DATA_BACKEND` switch with `sqlite` and `supabase` values. This supports a controlled cutover and a temporary rollback path while features are tested.
4. Keep Auth0, native Streamlit login, public profile UI, and navigation unchanged.

**Gate:** A signed-in user can load their canonical profile from Supabase in a development-safe path, while no existing app feature changes behavior.

### Phase B — Apply the Foundation Schema

1. Apply a named, versioned Supabase migration to create `profiles`, `journal_entries`, `boards`, `board_posts`, `chat_messages`, `lunatick_talk_posts`, `lunatick_talk_comments`, `user_votes`, and `card_trades`.
2. Add constraints and indexes before importing any records.
3. Consolidate the two SQLite `user_profiles` variants and `oidc_identities` into `profiles`; do not perpetuate duplicate profile tables.
4. Apply the privacy matrix through server-side access methods first, then enable and validate Row Level Security before any direct browser-to-Supabase data access is considered.
5. Run Supabase security and performance advisors after the schema is created.

**Gate:** The new schema contains no duplicate profile source of truth, all named indexes and privacy classifications exist, `migration_log` is writable only by the server-side migration path, and the database has a clean migration history. [3]

### Phase C — Migrate the Active Single-User Profile

1. Write a standalone, idempotent SQLite-to-Supabase importer. It reads the local file, validates each record, upserts profiles strictly by immutable `auth_subject`, treats `user_hash` as a non-unique legacy field, writes reconciliation events to `migration_log`, and prints counts without exposing private record content.
2. Start with the active authenticated profile and Cosmic Card/birth-chart fields.
3. Compare source and target counts and perform a record-level reconciliation for the single active profile.
4. Change `auth.py`, `cosmic_cards.py`, and the Settings profile editor to read and write through `supabase_store.py` when `DATA_BACKEND=supabase`.

**Gate:** Sign-in, profile save, avatar, bio, username lookup, birth chart, and Cosmic Card persistence work after a full deployment restart.

### Phase D — Migrate Community

1. Move boards and posts, then chat messages, then LunaTicK Talk posts/comments/votes.
2. Preserve post timestamps, authorship references, moderation flags, anonymity flags, and vote uniqueness.
3. Update Community modules to resolve author display values from `profiles`, while keeping the currently public fields limited to avatar, username, display name, and bio.
4. Defer `community_feed.py` unless it is intentionally reintroduced into the product; unused tables should not add needless migration scope.

**Gate:** A second test account can see intended public Community content, find a profile by username, and cannot view private profile or journal data.

### Phase E — Move Journals and Cut Over

1. Move `journal_entries` last because it is private writing and merits its own access tests.
2. Run source-to-target count reconciliation and spot-check entries using the owner account.
3. Set the production `DATA_BACKEND=supabase` value and deploy.
4. Keep the SQLite read path in code for one short validation window, but stop writing new data to it after cutover.
5. Remove the SQLite production path only after the app has completed the agreed validation window without data-integrity issues.

**Gate:** Restart the Streamlit app, then verify that profile data, Community, cards, and journals remain present. This is the real durability test.

## Rollback Strategy

A migration is not considered complete until rollback is possible.

| Event | Immediate response |
|---|---|
| Schema migration fails before data import | Stop; fix the named migration; do not alter the live SQLite workflow. |
| Profile import mismatch | Leave `DATA_BACKEND=sqlite`, correct the importer, rerun its idempotent upsert. |
| Feature regression after a Supabase deployment | Set `DATA_BACKEND=sqlite` temporarily and redeploy while the issue is diagnosed. |
| Successful cutover | Retain the SQLite code path briefly as a read-only contingency, then remove it deliberately after validation. |

## What We Do Not Do Yet

This plan deliberately does **not** create a new Supabase project, modify the existing `lunatick` project, add secrets, run SQL, migrate records, or expose a full-database export. Those are execution steps that should happen only after your explicit approval of the target schema and project credentials.

## Recommended Next Decision

The next concrete step should be to approve **Phase A and Phase B only**: establish the Supabase data-access module, write the first schema migration, and review it before applying it to the existing empty `lunatick` project. No user records move until the schema and access boundary are approved.

## References

[1]: https://docs.streamlit.io/develop/concepts/connections/authentication "Streamlit native authentication"
[2]: https://supabase.com/docs/guides/database/postgres/row-level-security "Supabase Row Level Security"
[3]: https://supabase.com/docs/guides/deployment/database-migrations "Supabase database migrations"
