# -*- coding: utf-8 -*-
"""Small Qt helpers shared across Multi Script Editor widgets."""
from __future__ import absolute_import

import re

from vendor.Qt.QtCore import QPoint, Qt
from vendor.Qt.QtGui import QFont


_FONT_ZOOM_RE = re.compile(
    r"/\*FONT_SIZE_ZOOM_START\*/.*?/\*FONT_SIZE_ZOOM_END\*/",
    re.S,
)


def event_pos(event):
    """Return QPoint for mouse/tablet events (Qt5 .pos / Qt6 .position)."""
    if hasattr(event, "position"):
        try:
            return event.position().toPoint()
        except Exception:
            pass
    if hasattr(event, "pos"):
        return event.pos()
    return QPoint()


def wheel_delta_y(event):
    """Vertical wheel delta; 0 when unavailable."""
    delta_y = 0
    if hasattr(event, "angleDelta"):
        delta_y = event.angleDelta().y()
    elif hasattr(event, "delta"):
        delta_y = event.delta()
    if delta_y == 0 and hasattr(event, "pixelDelta"):
        delta_y = event.pixelDelta().y()
    return delta_y


def qt_object_is_alive(obj):
    """True if a wrapped Qt object still has a valid C++ instance."""
    if obj is None:
        return False
    try:
        obj.objectName()
        return True
    except RuntimeError:
        return False


def apply_plain_text_font_size(widget, size, theme_style=None, minimum=8, maximum=30):
    """
    Resize QPlainTextEdit text via font + stylesheet override.

    Theme stylesheets often keep setFont() from showing; output log uses the
    same approach. Preserves *theme_style* (or the current stylesheet) and
    injects a FONT_SIZE_ZOOM block.
    """
    try:
        size = int(size)
    except (TypeError, ValueError):
        return None
    size = max(minimum, min(maximum, size))

    font = widget.font()
    font.setPointSize(size)
    widget.setFont(font)
    if hasattr(widget, "fs"):
        widget.fs = size

    base = theme_style
    if not base:
        base = widget.styleSheet() or ""
    base = _FONT_ZOOM_RE.sub("", base)
    zoom_css = (
        "/*FONT_SIZE_ZOOM_START*/\n"
        "QPlainTextEdit { font-size: %spt; }\n"
        "/*FONT_SIZE_ZOOM_END*/\n" % size
    )
    widget.setStyleSheet(base + zoom_css)

    try:
        widget.document().setDefaultFont(font)
    except Exception:
        pass
    return size
