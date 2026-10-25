"""Lunatick Tarot: reflective, non-fatalistic readings using the public-domain Rider–Waite–Smith deck.

Readings are symbolic prompts, not certain predictions. Artwork is served from Wikimedia Commons'
Special:FilePath endpoint; internet access is needed to display the card images.
"""
from __future__ import annotations

import random
from urllib.parse import quote
import streamlit as st

TAROT_MODULE_VERSION = "lunatick_tarot_v1"

MAJORS = [
("The Fool","beginnings, openness, a leap of faith","recklessness, hesitation, or a need to check your footing","Approach the next step with curiosity, while giving yourself enough information to feel grounded."),
("The Magician","initiative, resourcefulness, focused action","scattered effort, self-doubt, or using influence carelessly","You may have more tools than you realize. Choose one clear intention and put a practical skill to work."),
("The High Priestess","intuition, quiet knowledge, patient observation","noise, withheld information, or disconnect from your inner voice","Make room for stillness. You do not need to force an answer before you have listened carefully."),
("The Empress","nurturing, creativity, growth, abundance","overgiving, stagnation, or neglecting your own needs","Growth is supported by care. Include yourself in the care you offer others."),
("The Emperor","structure, boundaries, responsibility","rigidity, control, or a lack of useful structure","A steady framework can help you feel safer and act more confidently. Keep structure flexible enough to serve people."),
("The Hierophant","learning, shared wisdom, tradition, belonging","questioning conventions, restrictive rules, or finding your own path","Learn from trusted sources, then decide which principles genuinely fit your life."),
("The Lovers","connection, values, meaningful choice","misalignment, avoidance, or a need for honest communication","Bring your choices into line with your values. Clear, respectful honesty can deepen connection."),
("The Chariot","determination, direction, self-command","conflicting priorities, forcing progress, or losing focus","Progress comes from steering competing impulses toward one chosen destination."),
("Strength","courage, patience, compassionate confidence","harsh self-judgment, exhaustion, or reacting from fear","Gentleness is not weakness. A calm response may accomplish more than trying to overpower the situation."),
("The Hermit","reflection, solitude, inner guidance","isolation, overthinking, or reluctance to reconnect","Take space to hear yourself, but remember you can return to others when you are ready."),
("Wheel of Fortune","change, cycles, opportunity, turning points","resistance to change, unstable timing, or repeating patterns","You cannot control every turn, but you can notice the pattern and choose how to meet this moment."),
("Justice","fairness, accountability, clear-eyed decisions","bias, avoidance of responsibility, or an incomplete picture","Look at the facts with compassion and honesty. A balanced decision considers both impact and context."),
("The Hanged Man","pause, surrender, a fresh perspective","stalled action, needless sacrifice, or resisting a useful pause","A pause can be productive when it helps you see differently. Decide what is worth releasing and what needs action."),
("Death","ending, transition, renewal, letting go","clinging to an expired chapter, fear of change, or unfinished closure","This card is about transition, not literal death. Naming what has run its course can make room for renewal."),
("Temperance","balance, integration, patience, healing","extremes, impatience, or difficulty finding a workable middle","Small adjustments can restore balance. Give different needs time to find a sustainable rhythm."),
("The Devil","attachment, temptation, limiting patterns","recognizing a pattern, reclaiming agency, or loosening a bond","Notice where you feel stuck without shaming yourself. Naming a pattern is a first step toward choosing differently."),
("The Tower","disruption, revelation, unstable foundations","fear of change, delayed truth, or rebuilding after upheaval","A sudden change can be difficult, but it can also reveal what needs repair. Start with what is real and rebuild one piece at a time."),
("The Star","hope, renewal, perspective, quiet trust","discouragement, depleted faith, or needing rest","Hope does not require certainty. Let one small, restorative action remind you that recovery can begin gently."),
("The Moon","uncertainty, dreams, intuition, ambiguity","confusion clearing, checking assumptions, or fear shaping perception","Not everything is clear yet. Separate what you know from what you fear, and let evidence emerge before deciding."),
("The Sun","clarity, vitality, warmth, confidence","temporary low energy, overexposure, or overlooking a simple joy","Make room for what is working. A realistic moment of joy can be meaningful even when life remains complicated."),
("Judgement","reckoning, self-forgiveness, awakening, a new chapter","harsh self-criticism, avoiding a call, or difficulty moving on","Review the past to learn, not to punish yourself. You can acknowledge what happened and still choose a new response."),
("The World","completion, integration, accomplishment","unfinished business, a delayed milestone, or difficulty recognizing progress","Notice how far you have come. If something remains, define the final practical step rather than dismissing the whole journey."),
]

SUITS = {
"Wands": ("fire, energy, creativity, initiative", "bold action, inspiration, momentum", "burnout, impatience, scattered energy", "Choose a manageable action that gives your enthusiasm somewhere useful to go."),
"Cups": ("water, feelings, relationships, imagination", "emotional honesty, connection, compassion", "avoidance, overwhelm, unclear boundaries", "Make space for your feelings without treating every feeling as a final verdict."),
"Swords": ("air, thought, communication, discernment", "clarity, truth, decisions, perspective", "mental overload, conflict, assumptions", "Slow the story down. Identify the facts, name the concern, and choose the next clear conversation or decision."),
"Pentacles": ("earth, resources, work, body, daily life", "patience, stability, practical growth", "scarcity thinking, rigidity, neglected basics", "Support the larger goal with one concrete, sustainable step in everyday life."),
}
RANKS = [
("Ace","a seed of potential, a fresh opening","hesitation, an opening needing care"),
("Two","choice, balance, or collaboration","indecision, imbalance, or competing needs"),
("Three","learning through teamwork and practice","miscommunication, uneven effort, or a need to refine"),
("Four","stability, protection, or consolidation","holding too tightly, restlessness, or reconsidering security"),
("Five","friction, challenge, or adjustment","repair, perspective, or moving beyond unhelpful conflict"),
("Six","progress, support, or a transition","slow progress, lingering baggage, or accepting help"),
("Seven","assessment, perseverance, or discernment","second-guessing, impatience, or revising a strategy"),
("Eight","movement, dedication, or focused effort","delays, scattered attention, or a need to reset"),
("Nine","near-completion, independence, or resilience","fatigue, overextension, or asking for support"),
("Ten","culmination, responsibility, or a larger pattern","a burden to redistribute, a cycle ending, or simplifying"),
("Page","curiosity, a message, or beginner's mind","inexperience, distraction, or a lesson not yet integrated"),
("Knight","pursuit, momentum, or a chosen approach","overdoing it, inconsistency, or acting before reflecting"),
("Queen","mature understanding, stewardship, or inner mastery","neglecting your own needs, insecurity, or imbalance"),
("King","leadership, command, or responsible mastery","rigidity, overcontrol, or a need to lead more thoughtfully"),
]

def _image_url(card: dict) -> str:
    filename = card.get("image_file")
    return "https://commons.wikimedia.org/wiki/Special:FilePath/" + quote(filename) if filename else ""

def build_deck() -> list[dict]:
    deck = []
    for index, (name, upright, reversed_meaning, advice) in enumerate(MAJORS):
        deck.append({"name": name, "arcana": "Major Arcana", "upright": upright,
                     "reversed": reversed_meaning, "advice": advice,
                     "keywords": upright, "image_file": f"RWS_Tarot_{index:02d}_{name.replace(' ', '_')}.jpg"})
    for suit, (element, themes, shadows, advice) in SUITS.items():
        for rank_index, (rank, theme, shadow) in enumerate(RANKS):
            name = f"{rank} of {suit}"
            deck.append({
                "name": name, "arcana": "Minor Arcana", "suit": suit, "element": element,
                "upright": f"{theme}; {themes}",
                "reversed": f"{shadow}; {shadows}",
                "advice": advice,
                "keywords": f"{theme}; {element}",
                "image_file": f"RWS_Tarot_{rank.upper()}_of_{suit.upper()}.jpg" if rank in ("Ace","Page","Knight","Queen","King") else f"RWS_Tarot_{rank_index+1:02d}_of_{suit.upper()}.jpg",
            })
    return deck

DECK = build_deck()
POSITIONS = {
    "One-card reflection": ["Your focus"],
    "Three-card reflection": ["What shaped this", "What is present", "A helpful next step"],
    "Celtic Cross": ["Present situation", "The crossing influence", "The foundation", "Recent past", "What you are reaching toward", "Near-term direction", "Your stance", "Your environment", "Hopes and concerns", "A possible trajectory"],
}

def _draw_cards(count: int) -> list[tuple[dict, bool]]:
    chosen = random.sample(DECK, count)
    return [(card, random.random() < 0.28) for card in chosen]

def _display_card(card: dict, reversed_card: bool, position: str) -> None:
    with st.container(border=True):
        st.markdown(f"**{position}**")
        st.markdown(f"### {card['name']}" + (" · Reversed" if reversed_card else ""))
        url = _image_url(card)
        if url:
            st.image(url, width=180)
        meaning = card["reversed"] if reversed_card else card["upright"]
        st.caption("Reversed reading" if reversed_card else "Upright reading")
        st.write(meaning.capitalize() + ".")
        st.write("**A constructive way forward:** " + card["advice"])
        st.caption("Keywords: " + card["keywords"])

def render_tarot() -> None:
    st.markdown("## ✦ Tarot")
    st.caption("A reflective reading for perspective—not a fixed prediction or a substitute for your own judgment.")
    st.markdown(
        "<div style='border:1px solid rgba(188,140,255,.4);border-radius:12px;padding:.8rem 1rem;margin:.4rem 0 1rem;background:linear-gradient(145deg,rgba(35,22,65,.55),rgba(5,7,10,.8));'>"
        "<strong>Our reading promise</strong><br>Honest about challenges. Open to possibilities. No doom, fear tactics, or false certainty."
        "</div>", unsafe_allow_html=True
    )
    spread = st.selectbox("Choose a spread", list(POSITIONS), key="tarot_spread")
    intention = st.text_input("Optional question or intention", max_chars=240, placeholder="What would be useful to reflect on?")
    st.caption("You can leave this blank. Avoid entering private information you would not want saved in the app session.")
    if st.button("Draw my cards", type="primary", use_container_width=True, key="tarot_draw"):
        st.session_state["tarot_last_reading"] = {
            "spread": spread, "intention": intention.strip(),
            "cards": [(c["name"], rev) for c, rev in _draw_cards(len(POSITIONS[spread]))],
        }
    reading = st.session_state.get("tarot_last_reading")
    if not reading:
        st.markdown("Select a spread, set an intention if you like, and draw when you are ready.")
        return
    if reading["spread"] != spread:
        st.info("Choose **Draw my cards** to create a reading for the selected spread.")
        return
    if reading.get("intention"):
        st.markdown("**Your intention:** " + reading["intention"])
    lookup = {card["name"]: card for card in DECK}
    drawn = [(lookup[name], rev) for name, rev in reading["cards"]]
    st.markdown("### Your cards")
    for (card, reversed_card), position in zip(drawn, POSITIONS[spread]):
        _display_card(card, reversed_card, position)
    st.markdown("### Bringing the reading together")
    if len(drawn) == 1:
        card, rev = drawn[0]
        st.write(f"Your focus is **{card['name']}**. This card invites you to consider {card['reversed'] if rev else card['upright']}. Treat it as a question to explore, not a verdict. {card['advice']}")
    else:
        names = ", ".join(card["name"] for card, _ in drawn[:-1]) + " and " + drawn[-1][0]["name"]
        st.write(f"Together, **{names}** suggest a sequence rather than a fixed outcome. Notice what connects the themes, what feels most relevant to your real circumstances, and where you have room to choose your response.")
        st.write("The most challenging theme is not a sentence or a guarantee. It can be a prompt to prepare, set a boundary, seek support, or change course while options remain.")
    st.info("Reflection, not fate: keep what helps, question what does not, and let real-world evidence guide important decisions.")
    with st.expander("Browse the full 78-card deck"):
        for card in DECK:
            st.markdown(f"**{card['name']}** — {card['upright']}.")
            st.caption("Reversed: " + card["reversed"] + ".")
