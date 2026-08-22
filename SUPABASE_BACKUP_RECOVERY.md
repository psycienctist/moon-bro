# LunaTicK Supabase Backup and Recovery Runbook

## Purpose

LunaTicK’s production data now resides in Supabase. This runbook defines the **owner-only application backup** that supplements Supabase’s own platform backups. It is designed to protect the complete active LunaTicK dataset without exposing the service-role credential to the browser or committing it to the repository.

> A downloaded LunaTicK archive is a **logical, point-in-time export**. It is not an automated in-app restore button and must never be uploaded directly into production.

## Protection Layers

| Layer | What it protects | How it is used |
|---|---|---|
| **Supabase platform backups** | The full PostgreSQL project and schema, subject to the project plan and enabled features | Use the Supabase Dashboard’s **Database → Backups** recovery controls during a project-level incident. |
| **LunaTicK logical snapshot** | The application’s active public and private table records in a portable ZIP | Generate from **Settings → Backup & Recovery** as the authorized owner; keep the ZIP and manifest offline. |
| **GitHub source history** | Application code, versioned migrations, and test coverage | Use the `main` branch and tagged/committed releases to reconstruct application code. |

The official Supabase documentation recommends that free-tier projects regularly create logical exports and maintain them off-site. Paid projects may also have scheduled backups or Point-in-Time Recovery depending on the selected plan and enabled options. [1]

## Snapshot Scope

The owner-only export includes the complete rows of the following active LunaTicK application tables. It deliberately excludes Supabase system tables, Auth0 credentials, Streamlit secrets, and any service keys.

| Table | Contents | Sensitivity |
|---|---|---|
| `profiles` | Account-facing presence and private birth-chart fields | **Private** |
| `journal_entries` | Personal reflections | **Owner-only / highly private** |
| `boards`, `board_posts` | Community catalog and board content | Shared/public-facing |
| `chat_messages` | Community chat | Shared/public-facing |
| `lunatick_talk_posts`, `lunatick_talk_comments`, `user_votes` | LunaTicK Talk activity | Shared/public-facing |
| `card_trades` | Card connection requests | Private to participants |
| `migration_log` | Server-side migration audit metadata | Server-only operational record |
| `moderator_roles`, `moderation_actions` | Public-content moderation roles and accountability metadata | Server-only operational record |

No persistent user-uploaded media is currently included because LunaTicK Talk image attachments are intentionally disabled under the Supabase backend until a separate private object-storage phase is implemented.

## Owner Configuration

The Settings export control is visible only when Streamlit Cloud Secrets contains the signed-in founder’s Auth0 email address:

```toml
[backup]
owner_email = "YOUR_AUTH0_OWNER_EMAIL@example.com"
```

This value belongs in Streamlit Cloud Secrets only. It must not be committed to GitHub. It is compared server-side against the email claim in the active authenticated session.

## Creating and Verifying a Snapshot

Open **Settings → Backup & Recovery** while signed in as the configured owner. Select **Prepare verified Supabase backup**, then download both files:

1. `lunatick_supabase_backup_YYYYMMDDTHHMMSSZ.zip`
2. `lunatick_supabase_backup_YYYYMMDDTHHMMSSZ.manifest.json`

The ZIP contains `snapshot.json` and an internal `manifest.json`. The external manifest reports the archive SHA-256, snapshot SHA-256, exact read window, and per-table row counts.

Store both files together in encrypted, access-controlled offline storage. The archive contains private profile data and Journals, so it should never be emailed, posted to Community, committed to GitHub, or uploaded to an untrusted service.

To validate a downloaded archive locally, compare the reported hash with your local SHA-256 result:

```bash
shasum -a 256 lunatick_supabase_backup_YYYYMMDDTHHMMSSZ.zip
```

The reported value must exactly match `archive_sha256` in the external manifest. The snapshot SHA-256 applies to the `snapshot.json` file inside the archive.

## Snapshot Frequency

Create a new snapshot after material events: production releases that alter data behavior, moderator actions involving permanent deletion, onboarding a new tester cohort, or any incident. For a live community, create a fresh snapshot before a potentially destructive maintenance action and periodically while activity is increasing.

A logical export reads tables in deterministic pages but cannot hold all application-table reads inside one global database transaction. The manifest therefore records its read window. If members are actively writing at the time of export, create another snapshot immediately afterward for the cleanest recovery point.

## Recovery Procedure

Do not restore directly from a LunaTicK logical archive into the live project. Recovery is a deliberate owner operation:

1. **Stop or restrict application writes** and record the incident time.
2. **Choose the recovery layer.** Use Supabase Dashboard project restoration for a project-level failure; use the logical archive when a scoped, application-data recovery is appropriate.
3. **Preserve current evidence.** Create and retain a new verified export before replacing or deleting any data.
4. **Validate the archive.** Confirm archive and snapshot SHA-256 values and compare table counts against the manifest.
5. **Restore in a controlled Supabase environment first.** Validate schema compatibility, foreign-key order, and record counts before considering production changes.
6. **Review privacy impact.** Journal data must never be used for Community moderation, discovery, or routine review.
7. **Resume production only after validation** of Auth0 sign-in, profile persistence, Cosmic Cards, Community, and Journal ownership boundaries.

For platform-level restoration, Supabase restores project backups through its Dashboard and the project is unavailable while restoration occurs. Follow the project’s current backup availability and restoration controls. [1]

## References

[1]: https://supabase.com/docs/guides/platform/backups "Supabase Database Backups"
