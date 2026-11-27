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
    style: str = "glass"   # glass (glass.py) or aero (aero.py)
    glass: tuple = ()      # tints of the glass panes


LOOKS = {
    "day": Look("Day", False, 4, ("#dce6fb", "#f4ecf8"), ("#9db9dc", "#e6f0fb", "#ffffff"), (.74, .10), "#fff3d6",
                glass=("#a9c2f3", "#c3cff8", "#9fbcef", "#d2dcfb", "#b9b6ef")),
    "dawn": Look("Dawn", False, 9, ("#e4e2fa", "#fbe3dc"), ("#b9a3cf", "#f9cfcb", "#fff6ec"), (.22, .62), "#ffe0b0",
                 glass=("#f6cfc6", "#d9c8f3", "#f3dcc8", "#c6c9f5", "#efc3d6")),
    "mist": Look("Mist", False, 41, ("#e3e8ee", "#f3f4f7"), ("#b9c5d1", "#e4eaf0", "#ffffff"), (.50, .10), "#ffffff",
                 glass=("#c8d2de", "#d9dde8", "#bfc9d8", "#dcd6e4", "#cfd9e2")),
    "dusk": Look("Dusk", True, 17, ("#1d2152", "#5a3a6e"), ("#473a70", "#a2678f", "#ffc09a"), (.70, .66), "#ffb883",
                 glass=("#6a4f8e", "#a0628c", "#e08a7d", "#4f4a8e", "#c4799a")),
    "night": Look("Night", True, 23, ("#060a1a", "#17224a"), ("#17234a", "#2a3f70", "#7f95c8"), (.78, .14), "#b9cbff",
                  stars=True, glass=("#22346a", "#2e4682", "#1c2a5c", "#3a4f92", "#283a75")),
    "aero": Look("Aero", False, 31, ("#0f6fe0", "#aeeaff"), ("#8fb8e6", "#e8f4ff", "#ffffff"), (.80, .16), "#fffbe8",
                 style="aero"),
}
