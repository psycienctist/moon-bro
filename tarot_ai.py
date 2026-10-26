"""Optional AI synthesis for Lunatick Tarot, with safe local fallback."""
from __future__ import annotations

import os
import requests
import streamlit as st

TIMEOUT_SECONDS = 18


def _secret(name: str, default: str = "") -> str:
    try:
        value = st.secrets.get(name, default)
        if value:
            return str(value).strip()
    except Exception:
        pass
    return os.environ.get(name, default).strip()


def _prompt(cards, intention=""):
    positions = ["What shaped this", "What is present", "A helpful next step"]
    details = []
    for (card, reversed_card), position in zip(cards, positions):
        meaning = card["reversed"] if reversed_card else card["upright"]
        details.append(
            f"- {position}: {card['name']}{' (reversed)' if reversed_card else ''}\n"
            f"  Themes: {meaning}\n  Guidance: {card['advice']}"
        )
    question = intention.strip() or "No specific question; offer a relevant daily-life reflection."
    return f"""Create a distinctive Lunatick Tarot interpretation.

User's question/intention: {question}
Exact cards and positions:
{chr(10).join(details)}

Write 3–5 concise paragraphs with a useful heading. Synthesize the cards as a connected story:
how the first shaped the present and how the final card suggests a realistic next step.
Address the user's intention directly. Be specific, insightful, grounded, constructive, and warm.
Offer one or two practical actions or reflection questions. Acknowledge genuine tension without
doom, fear tactics, or false certainty. Tarot is symbolic reflection, not guaranteed prediction.
Do not invent personal facts, merely list card meanings, repeat generic boilerplate, or mention AI/providers.
"""


def _openrouter(prompt):
    key = _secret("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("OpenRouter key not configured")
    model = _secret("OPENROUTER_MODEL", "openai/gpt-4o-mini")
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json",
                 "HTTP-Referer": "https://moonbro.streamlit.app", "X-Title": "Lunatick Tarot"},
        json={"model": model, "messages": [
            {"role": "system", "content": "You are Lunatick's thoughtful Tarot interpreter."},
            {"role": "user", "content": prompt}],
            "temperature": 0.85, "max_tokens": 650},
        timeout=TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]
    if isinstance(content, list):
        content = "\n".join(x.get("text", "") for x in content if isinstance(x, dict))
    content = str(content).strip()
    if len(content) < 100:
        raise RuntimeError("OpenRouter response incomplete")
    return content


def _gemini(prompt):
    key = _secret("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("Gemini key not configured")
    model = _secret("GEMINI_MODEL", "gemini-2.5-flash")
    response = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        params={"key": key}, headers={"Content-Type": "application/json"},
        json={"systemInstruction": {"parts": [{"text": "You are Lunatick's thoughtful Tarot interpreter."}]},
              "contents": [{"role": "user", "parts": [{"text": prompt}]}],
              "generationConfig": {"temperature": 0.85, "maxOutputTokens": 850}},
        timeout=TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    parts = response.json()["candidates"][0]["content"]["parts"]
    content = "\n".join(x.get("text", "") for x in parts if isinstance(x, dict)).strip()
    if len(content) < 100:
        raise RuntimeError("Gemini response incomplete")
    return content


def generate_combined_reading(cards, intention=""):
    """Return interpretation and provider label; empty interpretation signals local fallback."""
    prompt = _prompt(cards, intention)
    try:
        return _openrouter(prompt), "OpenRouter"
    except Exception:
        pass
    try:
        return _gemini(prompt), "Gemini fallback"
    except Exception:
        return "", "Local fallback"
