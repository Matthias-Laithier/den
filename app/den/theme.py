from pathlib import Path

__all__ = ["STYLESHEET", "THEME"]

STYLESHEET = Path(__file__).parents[1] / "assets" / "styles" / "den.tcss"
THEME = "tokyo-night"
