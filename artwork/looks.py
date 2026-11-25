"""Wallpaper looks. Add an entry here and to the installer's packagechooser_look.conf."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Look:
    name: str
    dark: bool
    seed: int
    sky: tuple      # top, horizon
    cloud: tuple    # shadow, middle, light
    sun: tuple      # position, 0..1
    sun_color: str
    stars: bool = False


LOOKS = {
    "day": Look("Day", False, 4, ("#3f86d8", "#bfe0fa"), ("#9db9dc", "#e6f0fb", "#ffffff"), (.74, .10), "#fff3d6"),
    "dawn": Look("Dawn", False, 9, ("#8ea6e6", "#ffd8c6"), ("#b9a3cf", "#f9cfcb", "#fff6ec"), (.22, .62), "#ffe0b0"),
    "mist": Look("Mist", False, 41, ("#b4c2d0", "#eef2f6"), ("#b9c5d1", "#e4eaf0", "#ffffff"), (.50, .10), "#ffffff"),
    "dusk": Look("Dusk", True, 17, ("#262a5e", "#e88a78"), ("#473a70", "#a2678f", "#ffc09a"), (.70, .66), "#ffb883"),
    "night": Look("Night", True, 23, ("#060a1a", "#1f3059"), ("#17234a", "#2a3f70", "#7f95c8"), (.78, .14), "#b9cbff", stars=True),
}
