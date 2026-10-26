#!/bin/sh
# Render .streamlit/secrets.toml from environment variables, then start the app.
#
# Why this exists: LunaTicK reads its credentials through Streamlit Secrets
# (st.secrets), which only accepts TOML files - it does not read environment
# variables. Base44 delivers external-service credentials as environment
# variables in /run/base44/app.env (outside the repo), so this entry point
# materializes the small subset that needs the nested TOML structure the app
# expects:
#
#   AUTH0_CLIENT_ID / AUTH0_CLIENT_SECRET / AUTH0_SERVER_METADATA_URL
#   AUTH_COOKIE_SECRET / AUTH0_DATABASE_CONNECTION   -> [auth] / [auth.auth0]
#   DEEPSEEK_API_KEY                                 -> top-level key
#   SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY         -> [supabase]
#   DATA_BACKEND                                     -> [storage] data_backend
#
# The generated file is .streamlit/secrets.toml, which is gitignored, so no
# credential is ever written into the repository. No value is ever echoed.
#
# The OIDC redirect URL has to match the address the browser actually uses.
# In the Base44 sandbox that address is derived from BASE44_PUBLIC_HOST_SUFFIX
# (the preview proxy host), so it is built here at container start instead of
# being hardcoded. AUTH_REDIRECT_URI overrides it when set.

set -eu

SECRETS_FILE="${STREAMLIT_SECRETS_FILE:-.streamlit/secrets.toml}"
PUBLIC_HOST="${BASE44_PUBLIC_HOST_SUFFIX:-}"
REDIRECT_URI="${AUTH_REDIRECT_URI:-}"

if [ -z "$REDIRECT_URI" ] && [ -n "$PUBLIC_HOST" ]; then
    REDIRECT_URI="https://3000-${PUBLIC_HOST}/oauth2callback"
fi

if [ -n "${AUTH0_CLIENT_ID:-}${AUTH0_CLIENT_SECRET:-}${AUTH0_SERVER_METADATA_URL:-}${AUTH_COOKIE_SECRET:-}${DEEPSEEK_API_KEY:-}${SUPABASE_URL:-}" ]; then
    mkdir -p "$(dirname "$SECRETS_FILE")"
    {
        if [ -n "${AUTH_COOKIE_SECRET:-}${REDIRECT_URI:-}" ]; then
            echo "[auth]"
            [ -n "${REDIRECT_URI:-}" ] && printf 'redirect_uri = "%s"\n' "$REDIRECT_URI"
            [ -n "${AUTH_COOKIE_SECRET:-}" ] && printf 'cookie_secret = "%s"\n' "$AUTH_COOKIE_SECRET"
            echo
        fi

        if [ -n "${AUTH0_CLIENT_ID:-}${AUTH0_CLIENT_SECRET:-}${AUTH0_SERVER_METADATA_URL:-}" ]; then
            echo "[auth.auth0]"
            printf 'client_id = "%s"\n' "${AUTH0_CLIENT_ID:-}"
            printf 'client_secret = "%s"\n' "${AUTH0_CLIENT_SECRET:-}"
            printf 'server_metadata_url = "%s"\n' "${AUTH0_SERVER_METADATA_URL:-}"
            printf 'database_connection = "%s"\n' "${AUTH0_DATABASE_CONNECTION:-Username-Password-Authentication}"
            echo
        fi

        if [ -n "${SUPABASE_URL:-}${SUPABASE_SERVICE_ROLE_KEY:-}" ]; then
            echo "[supabase]"
            printf 'url = "%s"\n' "${SUPABASE_URL:-}"
            printf 'service_role_key = "%s"\n' "${SUPABASE_SERVICE_ROLE_KEY:-}"
            echo
        fi

        echo "[storage]"
        printf 'data_backend = "%s"\n' "${DATA_BACKEND:-sqlite}"

        if [ -n "${DEEPSEEK_API_KEY:-}" ]; then
            echo
            printf 'DEEPSEEK_API_KEY = "%s"\n' "$DEEPSEEK_API_KEY"
        fi
    } > "$SECRETS_FILE"
    echo "base44: wrote $SECRETS_FILE from environment (values not shown)"
else
    echo "base44: no credentials in the environment; starting with the app's defaults (login gate only)"
fi

# Sandbox-only origin allowlist.
#
# The preview proxy serves the app from https://3000-<public host suffix> while
# forwarding the request with Host: 3000-<sandbox id>.$BASE44_SANDBOX_HOST_DOMAIN.
# Streamlit treats an Origin host that differs from the request Host as
# cross-site and closes the client WebSocket ("Rejecting WebSocket connection
# with disallowed Origin or Host header"), which leaves the page permanently
# disconnected. Streamlit's own server.corsAllowedOrigins option is exactly the
# narrow extension point for that, so the preview origin is added to it here
# instead of editing the repository's shared .streamlit/config.toml.
#
# Gated on BASE44_PREVIEW_MODE being exactly "1" so a normal (non-Base44) run
# keeps Streamlit's default origin protection untouched. Streamlit's run
# command reads this through click's option envvar support.
if [ "${BASE44_PREVIEW_MODE:-}" = "1" ] && [ -n "$PUBLIC_HOST" ]; then
    STREAMLIT_SERVER_CORS_ALLOWED_ORIGINS="https://3000-${PUBLIC_HOST}"
    export STREAMLIT_SERVER_CORS_ALLOWED_ORIGINS
    echo "base44: allowing the preview origin $STREAMLIT_SERVER_CORS_ALLOWED_ORIGINS"
fi

# Run the command this script was given (the Streamlit start command from
# docker-compose.base44.yml), replacing this shell so signals reach Streamlit.
if [ "$#" -gt 0 ]; then
    exec "$@"
fi
