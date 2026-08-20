# 🌙 LunaTicK

> **Track the moon. Know your rhythm. Meet the world with more awareness.**

**LunaTicK** is a cosmic reflection and connection app presented by **Common Cents Culture (C3)**. It brings lunar tracking, personal reflection, creative self-inquiry, and community into one evolving digital space.

LunaTicK is built for people who want more than a dashboard. The moon is the entry point: a shared rhythm above every border, schedule, and identity. From that point of attention, the app invites a more deliberate relationship with time, self, other people, and the living world.

---

## Our Mission

LunaTicK exists to make attention more intentional.

Modern life is loud, accelerated, and designed to fragment attention. We move from alert to alert, task to task, argument to argument, often without a rhythm larger than the next demand placed in front of us. The lunar cycle offers no escape from reality. It offers orientation inside it.

Our mission is to create tools that help people notice where they are, reflect on what they are carrying, and connect with others without losing their individuality. LunaTicK combines useful lunar information with spaces for journaling, expression, conversation, and reflection because self-knowledge and social responsibility are not separate projects.

> **The moon belongs to no faction. Its rhythm reaches everyone.**

---

## Presented by Common Cents Culture (C3)

**Common Cents Culture (C3)** is the cultural home behind LunaTicK. C3 is interested in a practical question with radical consequences: what changes when people recover common sense, clear attention, moral courage, and a real sense of shared consequence?

C3 does not exist to manufacture conformity. It exists to support voluntary connection among people who remain distinct, sovereign, and responsible for how they meet one another. We believe a healthier culture is not built by erasing difference. It is built by refusing to let difference become an excuse for contempt, disposability, or indifference.

LunaTicK is one expression of that work. It is a place to observe, reflect, create, and connect under a rhythm shared by everyone.

---

## The Philosophical Foundation: Unifinality

LunaTicK is informed by **Unifinality: Thesis of All**, a philosophical framework centered on a direct claim:

> **There is one subject. It is you.**

Unifinality argues that the many perspectives of life are real without being finally separate at the level of being. It does not deny individuality, pain, science, or the material world. It argues that difference is real as perspective, while final separation is not the deepest truth of reality.

For LunaTicK, this is not a feature flag, a required belief, or a replacement for evidence. It is an ethical orientation. If another person, creature, or place is not finally outside the field of what we are, then attention, care, accountability, and restraint become forms of intelligence rather than signs of weakness.

This orientation does not ask users to abandon skepticism. It asks for a more demanding kind of openness: do not let an assumption of separateness become permission to neglect what suffers, dismiss what differs, or treat the world as disposable.

The practical question is simple:

> **Even if one rejects Unifinality as ontology, what is lost by treating every person and every living encounter with the moral seriousness one would demand for oneself?**

LunaTicK does not claim to answer that question for anyone. It creates a place to encounter it.

---

## What LunaTicK Does

LunaTicK combines real lunar information with reflective and communal tools.

| Space | Purpose |
|---|---|
| **Moon Monitor** | Follow lunar phase, illumination, cycle age, countdowns, and relevant astronomical context. |
| **Tones** | Explore a browser-based healing-tone generator with selectable presets, waveform, frequency, volume, and start/stop controls. |
| **Cosmic Cards** | Create a personal birth-chart-inspired collectible profile with planetary, zodiac, Human Design, and rarity-oriented details. |
| **Journal** | Capture reflections through lunar prompts, free writing, and personal context. |
| **Calendar** | Review upcoming lunar, eclipse, and astronomical events. |
| **Chat, Boards, and LunaTicK Talk** | Share thoughts, discover conversations, and participate in the emerging social layer of the app. |
| **Community** | An upcoming unified home for Chat, Boards, and LunaTicK Talk, designed to make connection simpler without flattening each space into the same thing. |

---

## Our Design Principles

LunaTicK is being built around a small set of commitments.

| Principle | What it means in practice |
|---|---|
| **Rhythm over rush** | The app should help users orient themselves, not manufacture more noise. |
| **Reflection without retreat** | Introspection matters when it improves how we act in the world. |
| **Difference without contempt** | Individuality, boundaries, and perspective are real; cruelty and indifference are not made wise by invoking them. |
| **Connection without coercion** | Community must remain voluntary, consent-based, and respectful of personal sovereignty. |
| **Beauty with purpose** | Cosmic visual design should make the product feel alive without obscuring what it does. |
| **Tools before posturing** | The app should earn trust through useful features, clear language, and reliable behavior. |

---

## Current Status

LunaTicK is in active **alpha development**. The foundation is present, but this is not yet a finished public product. Features, navigation, data flows, design details, and community systems are being tested and refined.

That is intentional. A healthy launch is not simply a moment of visibility; it is a promise that the experience is coherent enough to deserve other people’s time, attention, and trust.

The current development priorities are:

1. Stabilize the core lunar, profile, journal, and social experiences.
2. Complete and test the unified Community surface.
3. Strengthen mobile usability, accessibility, and user feedback loops.
4. Establish clear privacy, moderation, and data-handling practices before broader community growth.
5. Prepare a disciplined alpha release rather than a rushed public unveiling.

---

## Technology

LunaTicK is currently built with:

| Layer | Technology |
|---|---|
| Application | Python and Streamlit |
| Lunar calculations | PyEphem |
| Interface | Streamlit components with custom cosmic CSS |
| Data | Local SQLite-backed feature storage during the current alpha phase |
| Integrations | Optional alert and notification workflows, with ongoing development toward broader community infrastructure |

---

## Local Development

Clone the repository and install its current dependencies:

```bash
git clone https://github.com/psycienctist/moon-bro.git
cd moon-bro
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Run the Streamlit entry point:

```bash
streamlit run streamlit_app.py
```

For local feature work, use `app.py` as the primary application source. Please test changes on both desktop and phone-sized viewports before proposing them for the main branch.

---

## A Note on Community

LunaTicK is not interested in building another feed that monetizes distraction, outrage, or isolation. The social layer is meant to become a place where people can share what they are carrying, exchange perspective, and encounter one another without being reduced to inventory for an algorithm.

That requires care. Community does not mean forced agreement. It means disagreement without dehumanization, expression without needless cruelty, and connection that leaves room for personal boundaries.

The first responsibility of a community is not to become large. It is to become worth entering.

---

## Contributing

The project is evolving quickly. Thoughtful feedback, issue reports, testing notes, design observations, and implementation contributions are welcome.

Before opening a pull request, please:

1. Keep changes focused and explain the user-facing reason for them.
2. Preserve existing working behavior unless the change explicitly replaces it.
3. Test the relevant Streamlit view on desktop and phone-sized layouts.
4. Avoid adding dependencies without a clear need.
5. Treat user data, user expression, and community trust as first-order design concerns.

---

## The Point

LunaTicK begins with the moon because the moon is there: visible, recurring, indifferent to fashion, and shared by everyone looking up.

The aim is not to escape into the sky. The aim is to return to the world with clearer attention.

> **Track the moon. Know your rhythm. Treat what you meet as if it matters—because it does.**

---

**LunaTicK**  
Presented by **Common Cents Culture (C3)** 