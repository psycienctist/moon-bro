from pathlib import Path

app_source = Path("app.py").read_text(encoding="utf-8")
theme_config = Path(".streamlit/config.toml").read_text(encoding="utf-8")
journal_source = Path("journal.py").read_text(encoding="utf-8")

assert 'base = "dark"' in theme_config
assert 'backgroundColor = "#05070a"' in theme_config
assert 'textColor = "#e6edf3"' in theme_config
assert 'color-scheme: dark !important;' in app_source
assert '[data-testid="stAppViewContainer"],\n    [data-testid="stMain"]' in app_source
assert '[data-testid="stHeader"],\n    [data-testid="stMain"]' not in app_source
assert '[data-testid="stHeader"] {\n        background: transparent !important;' in app_source
assert '[data-testid="stTextArea"] textarea' in app_source
assert 'color: #f0f6fc !important;' in app_source
assert '-webkit-text-fill-color: #f0f6fc !important;' in app_source
assert 'caret-color: #bc8cff !important;' in app_source
assert '[data-testid="stTextArea"] textarea::placeholder' in app_source
assert 'color: #9aa7bd !important;' in app_source
assert 'st.text_area(' in journal_source
assert 'key="journal_freewrite_input"' in journal_source
