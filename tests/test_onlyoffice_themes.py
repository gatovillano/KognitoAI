import pytest
from skills.onlyoffice_skill.design.themes import (
    THEMES,
    DEFAULT_THEME,
    get_theme,
    hex_to_rgb,
    rgb_to_hex,
    lighten_color,
    darken_color,
)

def test_themes_presence():
    expected_themes = [
        "corporate_blue",
        "emerald_green",
        "dark_slate",
        "sunset_amber",
        "violet_gold",
        "minimalist_gray",
    ]
    for name in expected_themes:
        assert name in THEMES, f"Theme '{name}' missing from THEMES"
        theme = THEMES[name]
        assert "primary" in theme
        assert "secondary" in theme
        assert "accent" in theme
        assert "bg_light" in theme
        assert "bg_tint" in theme
        assert "border" in theme
        assert "text_primary" in theme
        assert "text_muted" in theme
        assert "font_heading" in theme
        assert "font_body" in theme

def test_get_theme_fallback():
    theme = get_theme("non_existent_theme")
    assert theme["primary"] == THEMES[DEFAULT_THEME]["primary"]

def test_get_theme_with_overrides():
    custom = get_theme(
        "corporate_blue",
        overrides={"primary": "FF0000", "font_heading": "Georgia"}
    )
    assert custom["primary"] == "FF0000"
    assert custom["font_heading"] == "Georgia"
    # non-overridden fields stay the same
    assert custom["secondary"] == THEMES["corporate_blue"]["secondary"]

def test_hex_to_rgb():
    assert hex_to_rgb("FFFFFF") == (255, 255, 255)
    assert hex_to_rgb("#000000") == (0, 0, 0)
    assert hex_to_rgb("1E3A8A") == (30, 58, 138)

def test_lighten_darken_color():
    dark = "1E3A8A"
    lighter = lighten_color(dark, 0.5)
    darker = darken_color(dark, 0.2)
    assert len(lighter) == 6
    assert len(darker) == 6
    assert lighter != dark
    assert darker != dark
