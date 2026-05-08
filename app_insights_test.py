import random
from datetime import datetime

# 50 unique insight templates
INSIGHT_TEMPLATES = [
    "Your {moon_sign} moon is moving through {current_zodiac}. This is a time to {moon_action}. Your aspect today is {aspect} — {aspect_meaning}.",
    "The {phase_name} is amplifying your {moon_sign} nature. Trust your instinct to {moon_action}.",
    "With the moon in {current_zodiac}, your {moon_sign} energy is being called to {moon_action}.",
    "Today's {aspect} aspect suggests {aspect_meaning}. Use this for {moon_action}.",
    "The {phase_name} invites {moon_sign} natives to {moon_action}. Your soul knows this.",
    "As a {moon_sign}, the {current_zodiac} transit is asking you to {moon_action}.",
    "The moon at {distance_km}km carries {proximity} intensity. Your {moon_sign} feels it.",
    "Your {moon_sign} moon responds to {phase_name} by naturally {moon_action}.",
    "The {aspect} between today's moon and your natal chart means {aspect_meaning}.",
    "In {current_zodiac}, the moon speaks to your {moon_sign} about {moon_theme}.",
    "The {phase_name} is a threshold moment. For {moon_sign}, it's time to {moon_action}.",
    "Your {moon_sign} thrives when you {moon_action}. The {phase_name} agrees.",
    "With moon at {distance_km}km, emotional {proximity_intensity} is heightened for your {moon_sign}.",
    "The {aspect} aspect reveals: {aspect_meaning}. What is your {moon_sign} trying to tell you?",
    "During {phase_name}, your {moon_sign} is strongest when you {moon_action}.",
    "The moon in {current_zodiac} teaches your {moon_sign} about {moon_theme}.",
    "Your {moon_sign} nature is {moon_state} right now. The {phase_name} confirms it.",
    "Today's {aspect} aspect with your chart says: {aspect_meaning}.",
    "The moon at {distance_km}km creates {proximity} energy. Your {moon_sign} feels {moon_state}.",
    "In this {phase_name}, {moon_sign} hearts are called toward {moon_action}.",
    "The {aspect} between current and natal positions shows {aspect_meaning}.",
    "Your {moon_sign} recognizes itself in the {current_zodiac} transit. Time to {moon_action}.",
    "The {phase_name} always invites {moon_sign} to {moon_action}. This is your rhythm.",
    "With moon in {current_zodiac}, inner truth for {moon_sign} is about {moon_theme}.",
    "The {aspect} aspect today reveals emotional {aspect_meaning}. Honor it.",
    "At {distance_km}km, the moon's pull on your {moon_sign} is {proximity_intensity}.",
    "Your {moon_sign} moon is in dialogue with {current_zodiac} about {moon_theme}.",
    "The {phase_name} phase naturally calls {moon_sign} to {moon_action}.",
    "Today's {aspect} aspect suggests {aspect_meaning}. Trust this timing.",
    "The moon's current position creates {proximity} emotional climate for {moon_sign}.",
    "In {current_zodiac}, themes of {moon_theme} arise powerfully for your {moon_sign}.",
    "Your {moon_sign} responds to {phase_name} with {moon_action}. Trust the cycle.",
    "The {aspect} aspect reveals {aspect_meaning}. Your {moon_sign} understands.",
    "At {distance_km}km, the moon carries {proximity_intensity} influence over {moon_sign}.",
    "The {phase_name} is the natural time for your {moon_sign} to {moon_action}.",
    "With moon in {current_zodiac}, your {moon_sign} heart wants to {moon_action}.",
    "The {aspect} between today and your birth chart means {aspect_meaning}.",
    "Your {moon_sign} nature is {moon_state}. The {phase_name} confirms this truth.",
    "The moon at {distance_km}km affects your {moon_sign} deeply right now.",
    "In this {phase_name}, {moon_sign} natives thrive by {moon_action}.",
    "The {aspect} aspect suggests {aspect_meaning}. What emerges for your {moon_sign}?",
    "The {current_zodiac} transit speaks directly to your {moon_sign} about {moon_theme}.",
    "Your {moon_sign} is called to {moon_action} during this {phase_name}.",
    "The {aspect} aspect reveals emotional {aspect_meaning}. Honor what arises.",
    "At {distance_km}km, emotional clarity for {moon_sign} is {proximity_intensity}.",
    "The {phase_name} invites your {moon_sign} into a state of {moon_state}.",
    "With moon in {current_zodiac}, your {moon_sign} recognizes themes of {moon_theme}.",
    "The {aspect} between current and natal positions guides your {moon_sign}.",
    "Your {moon_sign} moon knows what to do: {moon_action}. The cosmos agrees.",
    "The {phase_name} phase always brings this for {moon_sign}: natural {moon_action}.",
]

MOON_ACTIONS = {
    "Aries": ["initiate boldly", "take action", "lead with courage", "assert yourself", "pioneer"],
    "Taurus": ["ground yourself", "build stability", "savor the moment", "tend to your body", "create security"],
    "Gemini": ["communicate clearly", "explore ideas", "connect with others", "learn something new", "share your voice"],
    "Cancer": ["nurture yourself", "honor your feelings", "protect what matters", "return home", "tend to family"],
    "Leo": ["express yourself", "shine authentically", "celebrate life", "create boldly", "lead with heart"],
    "Virgo": ["refine your plans", "attend to details", "organize", "serve others", "improve"],
    "Libra": ["seek balance", "strengthen relationships", "create beauty", "collaborate", "consider others"],
    "Scorpio": ["go deep", "transform", "uncover truth", "trust your instinct", "dive beneath the surface"],
    "Sagittarius": ["explore possibilities", "seek truth", "expand your vision", "take a risk", "inspire others"],
    "Capricorn": ["build toward goals", "take responsibility", "structure your time", "climb higher", "achieve"],
    "Aquarius": ["think differently", "honor your individuality", "connect with community", "innovate", "rebel gently"],
    "Pisces": ["surrender to flow", "open your heart", "create or dream", "dissolve boundaries", "feel deeply"],
}

MOON_THEMES = {
    "Aries": "courage and new beginnings",
    "Taurus": "security and sensuality",
    "Gemini": "communication and connection",
    "Cancer": "home and emotional safety",
    "Leo": "self-expression and creativity",
    "Virgo": "refinement and service",
    "Libra": "harmony and relationships",
    "Scorpio": "depth and transformation",
    "Sagittarius": "expansion and truth",
    "Capricorn": "achievement and mastery",
    "Aquarius": "innovation and community",
    "Pisces": "intuition and imagination",
}

MOON_STATES = {
    "Aries": "fierce and ready",
    "Taurus": "calm and sensual",
    "Gemini": "curious and social",
    "Cancer": "tender and introspective",
    "Leo": "radiant and expressive",
    "Virgo": "precise and helpful",
    "Libra": "balanced and diplomatic",
    "Scorpio": "intense and probing",
    "Sagittarius": "expansive and optimistic",
    "Capricorn": "focused and determined",
    "Aquarius": "visionary and detached",
    "Pisces": "dreamy and permeable",
}

ASPECT_MEANINGS = {
    "Trine": "harmony flows naturally",
    "Square": "tension sparks growth",
    "Opposition": "balance is needed",
    "Conjunction": "unity and intensity",
    "Sextile": "opportunity opens",
    "Quincunx": "adjustment is needed",
}

def generate_daily_insight(moon_sign, moon_lon, phase_frac, distance_km):
    """Generate unique daily insight for a user"""
    
    zodiac_signs = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
                    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
    current_zodiac_idx = int((moon_lon % 360) / 30)
    current_zodiac = zodiac_signs[current_zodiac_idx]
    
    if phase_frac < 0.07: phase_name = "New Moon"
    elif phase_frac < 0.25: phase_name = "Waxing Crescent"
    elif phase_frac < 0.43: phase_name = "First Quarter"
    elif phase_frac < 0.50: phase_name = "Waxing Gibbous"
    elif phase_frac < 0.57: phase_name = "Full Moon"
    elif phase_frac < 0.75: phase_name = "Waning Gibbous"
    elif phase_frac < 0.93: phase_name = "Last Quarter"
    else: phase_name = "Waning Crescent"
    
    if distance_km < 370000: proximity = "close"
    elif distance_km > 400000: proximity = "distant"
    else: proximity = "balanced"
    
    if distance_km < 370000: proximity_intensity = "heightened"
    elif distance_km > 400000: proximity_intensity = "subtle"
    else: proximity_intensity = "moderate"
    
    aspect = random.choice(list(ASPECT_MEANINGS.keys()))
    aspect_meaning = ASPECT_MEANINGS[aspect]
    moon_action = random.choice(MOON_ACTIONS[moon_sign])
    moon_theme = MOON_THEMES[moon_sign]
    moon_state = MOON_STATES[moon_sign]
    
    selected_templates = random.sample(INSIGHT_TEMPLATES, k=random.randint(2, 3))
    
    insights = []
    for template in selected_templates:
        insight = template.format(
            moon_sign=moon_sign,
            current_zodiac=current_zodiac,
            moon_action=moon_action,
            aspect=aspect,
            aspect_meaning=aspect_meaning,
            phase_name=phase_name,
            moon_theme=moon_theme,
            moon_state=moon_state,
            distance_km=int(distance_km),
            proximity=proximity,
            proximity_intensity=proximity_intensity
        )
        insights.append(insight)
    
    return "\n\n".join(insights)
