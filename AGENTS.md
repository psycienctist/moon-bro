# AGENTS.md — working in this repository

Non-obvious things a future session needs. Manifests and the README already
describe the app itself (Python/Streamlit, PyEphem, pysweph, SQLite).

## Run it here

```bash
docker compose -f docker-compose.base44.yml up -d --build   # host port 3000 -> container 8501
docker compose -f docker-compose.base44.yml logs -f web
curl -s http://localhost:3000/_stcore/health                 # Streamlit's own health endpoint
```

* `Dockerfile.base44` bakes **dependencies only** (`requirements.txt`); the
  source is bind-mounted, and Streamlit runs with `--server.runOnSave`, so edits
  to `app.py` and the feature modules appear without a rebuild. Rebuild only
  when `requirements.txt` changes.
* The entry point is `streamlit_app.py`, which delegates to `app.py`.
* Watch mode uses polling (`--server.fileWatcherType=poll`) because the source
  arrives through a bind mount.
* Runtime data is `lunatick.db` in the repository root (gitignored, created on
  first page load). Local SQLite is the default backend: `[storage]
  data_backend = "sqlite"`; Supabase is optional and off unless configured.

## Credentials: Streamlit reads secrets from a TOML file, not the environment

`st.secrets` has no environment-variable fallback, but Base44 delivers
credentials as environment variables in `/run/base44/app.env`. `docker/base44-entrypoint.sh`
bridges the two: on container start it renders `.streamlit/secrets.toml`
(gitignored) from `AUTH0_CLIENT_ID`, `AUTH0_CLIENT_SECRET`,
`AUTH0_SERVER_METADATA_URL`, `AUTH_COOKIE_SECRET`,
`AUTH0_DATABASE_CONNECTION` (optional), `DEEPSEEK_API_KEY` (optional, Home
reading interpretation) and `SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY`
(optional). No credential value is ever echoed. Never commit `secrets.toml` —
see `.streamlit/secrets.toml.example` for the shape Streamlit expects.

## Sandbox-specific wiring (gated on `BASE44_PREVIEW_MODE=1`)

* **WebSocket origin.** The preview proxy serves the app from
  `https://3000-$BASE44_PUBLIC_HOST_SUFFIX` while forwarding
  `Host: 3000-<sandbox id>.$BASE44_SANDBOX_HOST_DOMAIN`. Streamlit treats a
  mismatched Origin as cross-site and closes the client WebSocket
  (`Rejecting WebSocket connection with disallowed Origin or Host header`),
  leaving the page permanently disconnected. The entry point therefore adds the
  preview origin to Streamlit's own `server.corsAllowedOrigins`. With the flag
  unset nothing is added and Streamlit's defaults apply unchanged.
* The same entry point derives `[auth] redirect_uri` as
  `https://3000-$BASE44_PUBLIC_HOST_SUFFIX/oauth2callback`, because that address
  changes whenever the sandbox is recreated. `AUTH_REDIRECT_URI` overrides it.
  Any URL you use must be registered in the Auth0 application's
  **Allowed Callback URLs**.

## The whole UI is behind Auth0

`app.py` calls `auth.render_login_page()` and `st.stop()`s when there is no
signed-in OIDC identity. Without Auth0 secrets the app still boots and serves the
sign-in screen, but `Continue to secure sign-in` raises `StreamlitAuthError`.
`redirect_uri` and `cookie_secret` under `[auth]` are both mandatory for
Streamlit's auth. Auth0's own login page is framed for the top-level document,
so sign-in is most reliable in a separate browser tab at the port-3000 URL
rather than inside the preview iframe.

## Tests

`pytest` is not in `requirements.txt`, so install it in the running container
before running the suite (it is not persisted across a recreate):

```bash
docker compose -f docker-compose.base44.yml exec -T web sh -c \
  "pip install pytest && python -m pytest test_moon.py"
```

`test_*_static.py` tests read the source files directly; the rest import the
feature modules.
