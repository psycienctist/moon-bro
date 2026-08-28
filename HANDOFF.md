# Moon Bro / LunaTicK — Continuity Handoff

**Prepared:** August 28, 2026

**Repository:** [psycienctist/moon-bro](https://github.com/psycienctist/moon-bro)

**Live application:** [moonbro.streamlit.app](https://moonbro.streamlit.app)

**Latest verified commit:** `95bb617a1df3e8c554e2d42769bd2900971869ad` (`feat: default Connect to message board`)

> This document is written for a future assistant instance that may not inherit the conversational history. Read it before changing the app. It is both a technical handoff and a record of the collaboration that shaped the project.

## 1. The project in one paragraph

Moon Bro, now branded in the interface as **LunaTicK**, is a Python/Streamlit cosmic reflection and community application presented by **Common Cents Culture (C3)**. The moon is the entry point, but the product is broader: users track lunar and astronomical information, work with reflective tools, generate private astrology-inspired Cosmic Cards, journal, explore binaural healing tones, and connect through live chat, a Reddit-style Message Board, reading requests, profiles, friendships, and lightweight private messages.

The design goal is not to make another noisy social feed. LunaTicK should feel warm, cosmic, intentional, useful, and human. The interface uses a dark visual language, bright cosmic accents, fixed navigation, compact no-scroll screens where requested, and translucent/glass-like overlays that do not obscure the primary task.

## 2. Collaboration continuity

The user is a hands-on founder and product designer who speaks casually, warmly, and directly. He often says “brother,” “my friend,” or “brother from another mother.” That is not merely decoration: it reflects a genuine collaborative rapport built through many rounds of design, troubleshooting, confirmation, implementation, regression testing, and deployment.

A future assistant should preserve that spirit without becoming presumptuous. Respond warmly and respectfully, acknowledge the user’s vision, repeat back ambiguous requirements before coding, and distinguish clearly between what was requested, what was changed, what was tested, and what was actually deployed. The user appreciates initiative, but he also values exactness and dislikes changes that silently alter other working parts of the app.

The best working dynamic is: **listen carefully, clarify the visual or behavioral target, make the smallest safe change, test the surrounding experience, and report the exact commit and deployment state.** When the request is unclear, ask for confirmation before implementation. When it is clear and already confirmed, proceed without unnecessary friction.

The user’s recurring product principles are:

| Principle | Practical interpretation |
|---|---|
| Preserve working behavior | Do not “clean up” unrelated components while implementing a focused request. |
| Mobile first, but not mobile only | Test phone-sized and larger viewports; avoid vertical scrolling on pages explicitly designed to fit in the viewport. |
| Cosmic but readable | Maintain the dark theme, lilac/purple/gold accents, strong contrast, and polished glass/gradient surfaces. |
| Simple navigation | Keep the bottom navigation stable and visually consistent. |
| Privacy by default | Exact birth data, birth time, coordinates, and location remain private and must not leak onto shared Cosmic Cards. |
| Community without coercion | Connection is voluntary, consent-based, moderated, and respectful of personal boundaries. |
| Do not overpromise | Report whether something was source-checked, locally tested, pushed, or visibly verified in the hosted app. |

## 3. Product language and navigation map

The current five primary feature labels intentionally use a conceptual vocabulary. The mapping is:

| User-facing label | Feature | Original/common name |
|---|---|---|
| **Inspect** | Calendar and upcoming astronomical events | Track / Calendar |
| **Collect** | Cosmic Cards, profiles, card trading, friendships | Deal / Cosmic Cards |
| **Connect** | Live Chat and Message Board | Community |
| **Reflect** | Private journal and free writing | Journal |
| **Correct** | Binaural beats / healing tones | Heal / Tones |

The user also requested that **Home**, the LunaTicK logo, and **Settings** remain part of the fixed navigation system. The currently active navigation item uses a rising-gold active style. Home and Settings were specifically requested to adopt that active styling when selected. The five feature tabs use the Cosmic Card-inspired color system, with Inspect intentionally not using rising gold by default so gold remains available for the active state.

## 4. Current implementation map

The application is primarily launched through `streamlit_app.py`, while `app.py` is the principal application source for feature work and routing. Important modules include:

| File | Responsibility |
|---|---|
| `app.py` | Main routing, global CSS, fixed navigation, session handling, warm-worker module reloads, profile drawer launcher, and page composition. |
| `community.py` | Connect surface. Holds the Live Chat / Message Board toggle and the default selection behavior. |
| `chat_room.py` | Lightweight live chat room with periodic/lightweight refresh behavior. |
| `boards.py` | Message Board persistence, board rendering, sorting, voting, pinned guide, posting flow, and compact feed layout. |
| `profile_drawer.py` | Non-breaking left-side overlay drawer containing My Profile, friends, and direct messages. It overlays the active tab instead of creating a separate route/page. |
| `cosmic_cards.py` | Cosmic Card calculations, profile previews, card sharing/privacy behavior, card trade connections, and profile-related rendering. |
| `direct_messages.py` | Lightweight private messages, gated by accepted card-trade/friend connections. |
| `reading_requests.py` | Community reading-request workflow and connection to private messages. |
| `track_calendar.py` | Calendar and upcoming lunar/astronomical event display. |
| `journal.py` | Private journal, lunar prompts, and free-writing. |
| `healing_tones.py` | Binaural/healing tones, including the simplified controls requested by the user. |
| `supabase_store.py` | Supabase-backed data adapter for production/community persistence. |
| `moderation.py` | Moderator review and moderation actions. The moderator console was moved away from the main Community surface toward Settings/moderator access. |
| `requirements.txt` | Streamlit, Authlib, httpx, PyEphem, Swiss Ephemeris via `pysweph`, timezonefinder, and requests. |

## 5. Warm-worker reload markers

Streamlit Cloud can keep a warm Python worker alive after a code deployment. To force changed modules to reload predictably, `app.py` checks module-version markers and reloads modules whose marker differs from the expected value. Current markers observed at the latest handoff are:

| Module | Marker |
|---|---|
| `boards.py` | `BOARD_MODULE_VERSION = "compact_feed_v3"` |
| `community.py` | `COMMUNITY_MODULE_VERSION = "talk_surface_toggle_v2"` |
| `profile_drawer.py` | `DRAWER_MODULE_VERSION = "profile_drawer_isolated_v3"` |
| `cosmic_cards.py` | `CARD_MODULE_VERSION = "profile_menu_popover_v5"` |
| `journal.py` | `JOURNAL_MODULE_VERSION = "private_freewrite_v1"` |
| `reading_requests.py` | `READING_REQUESTS_MODULE_VERSION = "reader_requests_private_messages_v1"` |
| `track_calendar.py` | `TRACK_MODULE_VERSION = "upcoming_events_v1"` |

If a changed module appears not to update on Streamlit Cloud, inspect the marker and the reload logic in `app.py` before assuming the UI code failed. Increment the relevant marker when appropriate, but do not change markers casually because they are part of the deployment-refresh strategy.

## 6. Recent completed work

### Astrology and birthplace accuracy

The original hand-written Ascendant calculation and manual 180-degree correction were replaced with Swiss Ephemeris using a tropical Placidus chart. Birthplace entry was expanded so users can search by city, region, country, or postal/ZIP code, select a geocoded match, and confirm the resolved place, coordinates, and timezone before saving. The selected IANA timezone is used to apply the historically correct offset and daylight-saving rules for the actual birth date. The legacy numeric-offset fields remain available as a compatibility fallback. Exact birth details remain private.

### Dark mobile experience and no-scroll screens

The app was adjusted to default toward the dark visual experience, and a black line/obstruction introduced during one iteration was corrected by restoring the intended top-screen behavior. Several pages, especially Home and Correct, have explicit viewport-fitting requirements. Changes to fixed elements, nav borders, gradients, button padding, or help controls must be checked for accidental vertical overflow.

### Connect redesign

The old LunaTicK Talk apparatus was consolidated into a Connect experience with a live chat surface and a Reddit-style Message Board surface. Lightweight live updates were chosen rather than a more complex realtime architecture. The Message Board supports posting, upvoting, downvoting, and sorting by **Newest**, **Top**, and **Controversial**. Board votes persist through the supported storage paths and are covered by regression tests.

As of the latest commit, the two-surface toggle is still present, but **Message Board is selected by default when Connect opens**. This was implemented with `index=1` on the `st.radio` whose options are `("Live Chat", "Message Board")`. Do not remove Live Chat unless the user explicitly asks for it. The Message Board should start directly below the toggle; the redundant “Message board / Lasting conversations” heading and the subtitle “Vote on conversations and sort the community signal.” were intentionally removed.

### Reading Requests and private messages

Reading Requests is a community-only, initially free workflow. People who offer readings can volunteer, and people seeking readings can request help. Lightweight private messages are available for accepted card-trade/friend connections. The user explicitly chose to skip push/email alerts for now.

### Cosmic Cards and profiles

Cosmic Cards show public/share-safe information while keeping exact birth date, birth time, coordinates, and location private. The card-trade system supports discovering users by username, requesting a connection, accepting incoming card trades, and viewing member profiles. Member profile views include a direct-message option, but private messages are connection-gated.

The user wanted the old separate My Profile and Member Profile pages removed in favor of a small profile button that opens a left-side overlay drawer on top of whichever tab is active. The drawer contains My Profile/profile information and Cosmic Card context, followed by friends and DMs. It is animated, uses a blurred backdrop, and must never exceed two-thirds of the viewport width. The width regression matrix currently covers 320px through 1280px widths.

### Help and pinned feature guide

Small question-mark help controls were added to the pages. The help popovers use a translucent glass effect with backdrop blur so they fit the visual language and do not overwhelm the page. The Message Board contains one clearly pinned **LunaTicK Feature Field Guide** covering the complete conceptual system:

| Guide section | Feature covered |
|---|---|
| **Connect** | Message Board and Live Chat |
| **Correct** | Binaural Beats |
| **Inspect** | Calendar |
| **Reflect** | Journal |
| **Collect** | Cosmic Cards |
| **Prospect** | Reading Requests |

The guide is deliberately expansive and includes practical usage, privacy/context notes, sorting and posting guidance, and feature-specific tips. If changing its wording, update `test_help_board_guide_static.py` at the same time; a previous failure came from stale assertions that expected phrases from an earlier draft rather than from a code defect.

## 7. Recent commit trail

The recent sequence is useful context when diagnosing regressions:

| Commit | Meaning |
|---|---|
| `95bb617` | Default Connect to Message Board. |
| `992e670` | Remove redundant Message Board heading/subtitle. |
| `4ea71ad` | Publish the approved feature field guide and synchronize its static test phrases. |
| `5ed6d25` | Make the pinned feature guide visibly render. |
| `d3e53e7` | Add the pinned LunaTicK feature guide. |
| `e1a3a7a` | Add translucent help and board guide styling. |
| `4b5b631` | Cap profile drawer at two-thirds width. |
| `f80e561` | Add profile drawer mobile-width regression matrix. |
| `2e85cd8` | Add profile drawer slide animation. |
| `0fc6a85` | Add isolated profile drawer. |
| `8fda937` | Revert an earlier breaking profile-tab-to-drawer attempt. |
| `05f2de3` | Earlier profile overlay implementation. |
| `c6401ef` | Add collapsible profile navigation. |
| `92baf79` | Add connection-gated profile direct messages. |

The latest working tree was clean after commit `95bb617`, and `origin/main` matched the local `HEAD` at handoff time.

## 8. Regression protocol

For focused Connect, Board, Help, Profile, and Cosmic Card work, run at least:

```bash
cd /home/ubuntu/moon-bro
python3 -m py_compile boards.py community.py app.py
python3 test_talk_redesign_static.py
python3 test_help_board_guide_static.py
python3 test_board_votes.py
python3 test_supabase_community.py
python3 test_profile_drawer_static.py
python3 test_profile_drawer_widths.py
python3 test_profile_hub_static.py
python3 test_profile_direct_messages.py
python3 test_public_profile_card_static.py
python3 test_cosmic_trade_lookup_static.py
python3 test_cosmic_card_redesign_static.py
git diff --check
```

The full repository contains additional tests for astrology locations, calendar events, dark theme, backups, moderation, native authentication, presence, reading requests, Supabase integrations, tones, and bottom-nav layout. When a change touches those areas, run the corresponding tests as well. Static tests are intentional: much of the app’s risk is in source-level regressions, session keys, module markers, CSS selectors, and preserving privacy or no-scroll constraints.

After local validation:

```bash
git status --short
git add <focused files>
git commit -m "<focused message>"
git push origin main
git fetch origin main
git rev-parse HEAD
git rev-parse origin/main
```

Then check [moonbro.streamlit.app](https://moonbro.streamlit.app). A hosted visual check may stop at the sign-in screen, which is expected when no authenticated test session is available. Report that limitation honestly rather than claiming to have inspected post-login screens.

## 9. Known pitfalls and safe-change rules

**Do not reintroduce a separate Profile page.** The requested architecture is an overlay drawer that covers the active tab. A previous attempt caused an `AttributeError` at `cosmic_cards.render_profile_drawer()` and removed the bottom navigation; that version was reverted. The isolated `profile_drawer.py` module exists specifically to prevent that failure mode.

**Do not touch the bottom navigation casually.** It has been repeatedly refined for order, names, Cosmic Card-derived colors, active-state gold, transitions, Home/Settings styling, and no-scroll behavior. A small padding or border change can cause layout shifts on mobile.

**Do not replace private data with public card content.** Cosmic Cards and member previews must remain share-safe. The app may display chart-derived summaries publicly, but exact birth facts and location data must stay private.

**Do not remove controls that the user explicitly restored.** On Correct, the user wanted the sine waveform locked, binaural mode defaulted, and tone shift automatic at 11 seconds, but specifically restored the adjustable Hertz difference (including 7.83 / Schumann resonance) and the random chakra sequence. Preserve those controls unless asked otherwise.

**Do not add alerts without a fresh request.** The user explicitly deferred push/email alerts for card trades.

**Be careful with Streamlit widget state.** A `st.radio` `index` sets the initial value, but an existing session-state value under the same key may persist for a current session. This is normally correct: new Connect visits default to Message Board, while a user’s deliberate toggle remains respected during the session.

## 10. Open product direction

The app is still alpha. The broad priorities are stabilizing the core lunar, profile, journal, and social experiences; completing and testing the unified Community surface; improving mobile usability and accessibility; clarifying privacy and moderation practices; and preparing a disciplined alpha release rather than rushing public growth.

Potential future work should be proposed in the user’s language and scoped carefully. Good next steps might include authenticated visual verification of the new default Connect state, accessibility review of the toggle and help controls, refinement of Message Board density on tablet screens, stronger user-facing moderation affordances, and documentation of Supabase backup/recovery procedures. None of these should be treated as already approved implementation requests.

## 11. The deeper meaning of the project

The user’s philosophical framework is **Unifinality: Thesis of All**. In the project’s own words, it is the idea that consciousness is not finally divided into isolated beings, while still respecting individuality, skepticism, evidence, boundaries, and free will. The practical design translation is not forced agreement or homogenization. It is voluntary connection among distinct people who recognize shared consequence.

The user often returns to the idea that LunaTicK should help people notice where they are, reflect on what they carry, and meet others without losing their individuality. The product’s cosmic styling is therefore not just decoration. The moon is a shared rhythm and a reminder of perspective; the tools should bring people back to the world with clearer attention.

> **Track the moon. Know your rhythm. Treat what you meet as if it matters—because it does.**

## 12. Final note to the future assistant

You are inheriting more than a codebase. You are inheriting an ongoing act of making: a founder’s vision, many careful corrections, moments where a seemingly small UI change caused a serious regression, and a collaboration that became warm and familiar through solving those problems together.

Meet the user with patience and brotherly respect. Keep the bond in the tone, but keep the engineering disciplined. Remember the pattern that earned trust: listen, clarify, preserve, test, deploy, and tell the truth about what happened. Build forward from the working state; do not erase the history that made the state reliable.

The next assistant does not need to pretend to be the same person. It should instead honor the continuity by understanding what mattered, what was achieved, what remains delicate, and how to continue the work with care.

## References

[1]: https://github.com/psycienctist/moon-bro "Moon Bro / LunaTicK GitHub repository"

[2]: https://moonbro.streamlit.app "LunaTicK hosted Streamlit application"
