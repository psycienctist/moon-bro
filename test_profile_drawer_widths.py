from pathlib import Path

source = Path("profile_drawer.py").read_text(encoding="utf-8")
assert "width: min(50vw, 30rem) !important;" in source
assert "@media (max-width: 600px)" in source
assert "width: min(82vw, 30rem) !important;" in source
assert "max-width: calc(100vw - 1rem) !important;" in source

# CSS sizing model used by the drawer. The mobile rule applies at <=600px.
def drawer_width(viewport_width: int) -> float:
    if viewport_width <= 600:
        return min(viewport_width * 0.82, 480.0, viewport_width - 16.0)
    return min(viewport_width * 0.50, 480.0)

expected = {
    320: 262.4,
    360: 295.2,
    390: 319.8,
    430: 352.6,
    600: 480.0,
    768: 384.0,
    1024: 480.0,
    1280: 480.0,
}
for width, target in expected.items():
    actual = drawer_width(width)
    assert abs(actual - target) < 0.01, (width, actual, target)
    assert actual <= width - 16 if width <= 600 else actual <= width / 2 + 0.01

print("Profile drawer width matrix passed:", ", ".join(f"{w}px={drawer_width(w):.1f}px" for w in expected))
