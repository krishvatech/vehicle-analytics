"""Gate logic for determining entry/exit events based on ROI crossings."""

from typing import Tuple, List


def point_inside_rect(x: float, y: float, rect: List[List[float]]) -> bool:
    """Return True if a point lies within the rectangle defined by two points.

    Args:
        x: X coordinate of the point (pixels).
        y: Y coordinate of the point (pixels).
        rect: List containing two points [[x1,y1],[x2,y2]] describing a rectangle.
    Returns:
        True if (x,y) lies within the rectangle.
    """
    (x1, y1), (x2, y2) = rect
    left, right = sorted([x1, x2])
    top, bottom = sorted([y1, y2])
    return left <= x <= right and top <= y <= bottom


def determine_entry_exit(prev_pos: Tuple[float, float], curr_pos: Tuple[float, float], rect: List[List[float]] | None = None) -> str:
    """Determine direction based on movement along the y-axis or ROI midline."""
    _, prev_y = prev_pos
    _, curr_y = curr_pos
    if rect:
        (x1, y1), (x2, y2) = rect
        mid_y = (y1 + y2) / 2.0
        # Crossing the midline downward => EXIT, upward => ENTRY
        if prev_y <= mid_y < curr_y:
            return "EXIT"
        if prev_y >= mid_y > curr_y:
            return "ENTRY"
    return "ENTRY" if curr_y < prev_y else "EXIT"
