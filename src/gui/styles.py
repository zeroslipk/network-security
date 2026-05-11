"""Shared color and font constants for the GUI."""

# Background layers
BG        = "#1a1b2e"   # main window bg
BG2       = "#16213e"   # slightly darker panels
SURFACE   = "#0f3460"   # header / status bar
ENTRY_BG  = "#252641"   # input fields

# Text
FG        = "#e0e0e0"   # primary text
FG_MUTED  = "#7b8cde"   # timestamps / hints

# Accent colours
ACCENT    = "#7b8cde"   # your own messages / interactive blue
ACCENT2   = "#e94560"   # send button / highlights
SUCCESS   = "#4ecca3"   # connected dot
ERROR     = "#e94560"   # error / disconnected
MUTED     = "#555577"   # system messages / placeholders

# Fonts  (SF Pro falls back to Helvetica Neue on macOS)
FONT_FAMILY   = "SF Pro Display"
FONT          = (FONT_FAMILY, 12)
FONT_BOLD     = (FONT_FAMILY, 12, "bold")
FONT_TITLE    = (FONT_FAMILY, 15, "bold")
FONT_SMALL    = (FONT_FAMILY, 10)
FONT_INPUT    = (FONT_FAMILY, 13)
