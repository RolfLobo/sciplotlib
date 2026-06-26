"""
Interactive drag-and-drop position editor for matplotlib artists.

Supported artist types
----------------------
- Text / Annotation (respects transAxes, transData, transFigure)
- AnnotationBbox  (SVG/image overlays created with place_image())
- Rectangle and other Patch subclasses

Typical workflow
----------------
1. In your marimo cell, save the composed figure as a pickle::

       import pickle
       with open('/tmp/fig_panel_j.pkl', 'wb') as f:
           pickle.dump(fig, f)

2. From the marimo prompt (or a terminal)::

       ! uv run python -m sciplotlib.drag_editor /tmp/fig_panel_j.pkl

3. Drag artists to new positions.
   - Press **p** at any time to print current coordinates.
   - Press **u** to undo the last move.
   - **Close the window** to print the final summary.

4. Paste the printed `set_position` / `.xy` / `set_xy` calls into your notebook.

Importing as a library
----------------------
    from sciplotlib.drag_editor import PositionEditor
    editor = PositionEditor(fig)
    editor.run()
"""

from __future__ import annotations

import sys
import pickle
import traceback
import numpy as np

import matplotlib
from matplotlib.text import Text, Annotation
from matplotlib.offsetbox import AnnotationBbox
from matplotlib.patches import Patch, Rectangle
import matplotlib.pyplot as plt


# ── coordinate helpers ────────────────────────────────────────────────────────

def _text_transform(text: Text, ax):
    """Return the coordinate transform that *text* uses for its position."""
    return text.get_transform()


def _annotation_bbox_transform(ab: AnnotationBbox, ax):
    """Return the coordinate transform for an AnnotationBbox's *xy* anchor."""
    coords = getattr(ab, 'xycoords', 'data')
    if coords == 'data':
        return ax.transData
    if coords == 'axes fraction':
        return ax.transAxes
    if coords == 'figure fraction':
        return ax.figure.transFigure
    # xycoords can also be a Transform object
    if callable(getattr(coords, 'transform', None)):
        return coords
    return ax.transData


def _patch_transform(patch: Patch, ax):
    return ax.transData  # patch coordinates are always in data space


def _get_transform(artist, ax):
    if isinstance(artist, Text):
        return _text_transform(artist, ax)
    if isinstance(artist, AnnotationBbox):
        return _annotation_bbox_transform(artist, ax)
    if isinstance(artist, Patch):
        return _patch_transform(artist, ax)
    raise TypeError(f"Unsupported artist: {type(artist)}")


def _transform_name(artist, ax):
    t = _get_transform(artist, ax)
    if t is ax.transAxes:
        return 'transAxes'
    if t is ax.transData:
        return 'transData'
    if t is ax.figure.transFigure:
        return 'transFigure'
    return 'custom'


# ── native position get/set ───────────────────────────────────────────────────

def _get_pos(artist) -> np.ndarray:
    if isinstance(artist, Text):
        return np.array(artist.get_position(), dtype=float)
    if isinstance(artist, AnnotationBbox):
        return np.array(artist.xy, dtype=float)
    if isinstance(artist, Patch):
        return np.array(artist.get_xy(), dtype=float)
    raise TypeError(f"Unsupported artist: {type(artist)}")


def _set_pos(artist, pos):
    if isinstance(artist, Text):
        artist.set_position(tuple(pos))
    elif isinstance(artist, AnnotationBbox):
        artist.xy = tuple(pos)
    elif isinstance(artist, Patch):
        artist.set_xy(tuple(pos))


# ── hit detection ─────────────────────────────────────────────────────────────

def _get_window_extent(artist, renderer):
    try:
        return artist.get_window_extent(renderer)
    except Exception:
        return None


def _hits(artist, event, renderer, pad: float = 6.0) -> bool:
    """Return True if the mouse event is within the artist's bounding box."""
    bbox = _get_window_extent(artist, renderer)
    if bbox is None:
        return False
    x0, y0, x1, y1 = bbox.x0, bbox.y0, bbox.x1, bbox.y1
    # Ensure x0 < x1 and y0 < y1 (AnnotationBbox bbox may be inverted)
    if x0 > x1:
        x0, x1 = x1, x0
    if y0 > y1:
        y0, y1 = y1, y0
    ex, ey = event.x, event.y
    return (x0 - pad) <= ex <= (x1 + pad) and (y0 - pad) <= ey <= (y1 + pad)


# ── artist description ────────────────────────────────────────────────────────

def _artist_label(artist) -> str:
    if isinstance(artist, Text):
        txt = artist.get_text().replace('\n', '\\n')
        return f'Text("{txt}")'
    if isinstance(artist, AnnotationBbox):
        return 'AnnotationBbox'
    if isinstance(artist, Rectangle):
        return f'Rectangle'
    if isinstance(artist, Patch):
        return type(artist).__name__
    return type(artist).__name__


# ── draggable wrapper ─────────────────────────────────────────────────────────

class _Item:
    def __init__(self, artist, ax):
        self.artist = artist
        self.ax = ax
        self.label = _artist_label(artist)

        self._initial_pos = _get_pos(artist).copy()
        self._history: list[np.ndarray] = []  # positions before each move
        self._press_display: np.ndarray | None = None
        self._press_native: np.ndarray | None = None
        self._press_display_of_native: np.ndarray | None = None

    @property
    def moved(self) -> bool:
        return len(self._history) > 0

    def start(self, ex: float, ey: float):
        native = _get_pos(self.artist)
        t = _get_transform(self.artist, self.ax)
        self._press_display = np.array([ex, ey], dtype=float)
        self._press_native = native.copy()
        self._press_display_of_native = t.transform(native)
        self._history.append(native.copy())

    def drag(self, ex: float, ey: float):
        if self._press_display is None:
            return
        delta = np.array([ex, ey]) - self._press_display
        new_display = self._press_display_of_native + delta
        t = _get_transform(self.artist, self.ax)
        new_native = t.inverted().transform(new_display)
        _set_pos(self.artist, new_native)

    def end(self):
        self._press_display = None
        self._press_native = None
        self._press_display_of_native = None

    def undo(self):
        if self._history:
            _set_pos(self.artist, self._history.pop())

    def pos(self) -> np.ndarray:
        return _get_pos(self.artist)

    def coord_system(self) -> str:
        return _transform_name(self.artist, self.ax)

    def code_snippet(self) -> str:
        x, y = self.pos()
        a = self.artist
        cs = self.coord_system()
        if isinstance(a, Text):
            return (
                f'# {self.label}  [{cs}]\n'
                f'.set_position(({x:.4f}, {y:.4f}))'
            )
        if isinstance(a, AnnotationBbox):
            return (
                f'# {self.label}  [{cs}]\n'
                f'.xy = ({x:.4f}, {y:.4f})'
            )
        if isinstance(a, Patch):
            return (
                f'# {self.label}  [{cs}]\n'
                f'.set_xy(({x:.4f}, {y:.4f}))'
            )
        return f'# {self.label}: ({x:.4f}, {y:.4f})'


# ── editor ────────────────────────────────────────────────────────────────────

class PositionEditor:
    """Interactive drag-and-drop position editor for a matplotlib figure.

    Parameters
    ----------
    fig : matplotlib.figure.Figure
    patch_types : tuple of type, optional
        Patch subclasses to make draggable.  Defaults to ``(Rectangle,)``.
        Pass ``None`` to disable patch dragging entirely, or a tuple of
        types (e.g. ``(Rectangle, FancyArrow)``) to extend coverage.
    """

    def __init__(self, fig, patch_types=(Rectangle,)):
        self.fig = fig
        self._patch_types = patch_types or ()
        self._items: list[_Item] = []
        self._active: _Item | None = None
        self._renderer = None
        self._collect()
        self._connect()
        self._set_title('Click an artist to drag it  |  p = print  |  u = undo')

    # ── collection ────────────────────────────────────────────────────────────

    def _collect(self):
        # Inset axes (create_inset_grid, ax.inset_axes) may live in
        # ax.child_axes without appearing in fig.get_axes(), so recurse.
        seen: set[int] = set()

        def _collect_ax(ax):
            if id(ax) in seen:
                return
            seen.add(id(ax))
            for t in ax.texts:
                self._items.append(_Item(t, ax))
            for a in ax.artists:
                if isinstance(a, AnnotationBbox):
                    self._items.append(_Item(a, ax))
            if self._patch_types:
                for p in ax.patches:
                    if isinstance(p, self._patch_types):
                        self._items.append(_Item(p, ax))
            for child in getattr(ax, 'child_axes', []):
                _collect_ax(child)

        for ax in self.fig.get_axes():
            _collect_ax(ax)

    # ── event plumbing ────────────────────────────────────────────────────────

    def _connect(self):
        c = self.fig.canvas
        self._cids = [
            c.mpl_connect('button_press_event',   self._on_press),
            c.mpl_connect('button_release_event', self._on_release),
            c.mpl_connect('motion_notify_event',  self._on_motion),
            c.mpl_connect('key_press_event',       self._on_key),
            c.mpl_connect('close_event',           self._on_close),
        ]

    def _disconnect(self):
        for cid in self._cids:
            self.fig.canvas.mpl_disconnect(cid)

    # ── renderer cache ────────────────────────────────────────────────────────

    def _get_renderer(self):
        if self._renderer is None:
            self.fig.canvas.draw()
            try:
                self._renderer = self.fig.canvas.get_renderer()
            except AttributeError:
                self._renderer = self.fig._get_renderer()
        return self._renderer

    def _invalidate_renderer(self):
        self._renderer = None

    # ── event handlers ────────────────────────────────────────────────────────

    def _on_press(self, event):
        if event.button != 1 or event.x is None:
            return
        renderer = self._get_renderer()
        for item in reversed(self._items):  # reversed → topmost first
            if _hits(item.artist, event, renderer):
                self._active = item
                item.start(event.x, event.y)
                self._set_title(f'Dragging {item.label}  [{item.coord_system()}]  |  u = undo')
                return

    def _on_motion(self, event):
        if self._active is None or event.x is None:
            return
        self._active.drag(event.x, event.y)
        self._invalidate_renderer()
        self.fig.canvas.draw_idle()

    def _on_release(self, event):
        if self._active is None:
            return
        x, y = self._active.pos()
        self._active.end()
        self._set_title(
            f'Released {self._active.label} → ({x:.4f}, {y:.4f})  '
            f'[{self._active.coord_system()}]  |  p = print  |  u = undo'
        )
        self._active = None
        self._invalidate_renderer()

    def _on_key(self, event):
        if event.key in ('p', 'P'):
            self.print_positions()
        elif event.key in ('u', 'U'):
            self._undo_last()

    def _on_close(self, event):
        self.print_positions()

    # ── undo ──────────────────────────────────────────────────────────────────

    def _undo_last(self):
        # Find the most recently moved item (last entry in history)
        candidates = [it for it in self._items if it.moved]
        if not candidates:
            self._set_title('Nothing to undo.')
            return
        # Undo the one with the most recent history entry
        target = max(candidates, key=lambda it: len(it._history))
        target.undo()
        self._invalidate_renderer()
        self.fig.canvas.draw_idle()
        self._set_title(f'Undid last move of {target.label}  |  p = print')

    # ── output ────────────────────────────────────────────────────────────────

    def print_positions(self):
        moved = [it for it in self._items if it.moved]
        if not moved:
            print('(No artists were moved.)')
            return
        print('\n# ── Updated positions (' + '─' * 50)
        for it in moved:
            print(it.code_snippet())
        print('# ' + '─' * 60)

    # ── window title ──────────────────────────────────────────────────────────

    def _set_title(self, msg: str):
        try:
            self.fig.canvas.manager.set_window_title(f'DragEditor — {msg}')
        except Exception:
            pass

    # ── run ───────────────────────────────────────────────────────────────────

    def run(self):
        """Open the interactive window (blocks until closed)."""
        plt.show(block=True)


# ── Convenience launcher (no manual pickle) ───────────────────────────────────

def launch_editor(fig, patch_types=(Rectangle,)):
    """Launch the drag editor for *fig* without any manual pickle step.

    Serialises *fig* to a temporary file, opens the interactive window in a
    subprocess (so the GUI backend is always available regardless of the
    calling environment), and cleans up on exit.  Blocks until the window is
    closed, then prints updated coordinates to the terminal where marimo/your
    script was started.

    Parameters
    ----------
    fig : matplotlib.figure.Figure
    patch_types : tuple of type, optional
        Patch subclasses to make draggable. Defaults to ``(Rectangle,)``.

    Usage (from a marimo cell)::

        from sciplotlib.drag_editor import launch_editor
        launch_editor(fig)
    """
    import os
    import subprocess
    import tempfile

    with tempfile.NamedTemporaryFile(suffix='.pkl', delete=False) as f:
        pkl_path = f.name
        pickle.dump(fig, f)

    try:
        subprocess.run(
            [sys.executable, '-m', 'sciplotlib.drag_editor', pkl_path],
            check=False,
        )
    finally:
        try:
            os.unlink(pkl_path)
        except OSError:
            pass


# ── CLI entry point ───────────────────────────────────────────────────────────

def _cli():
    import argparse
    parser = argparse.ArgumentParser(
        prog='python -m sciplotlib.drag_editor',
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('pkl', help='Path to a pickled matplotlib Figure (.pkl)')
    args = parser.parse_args()

    try:
        with open(args.pkl, 'rb') as f:
            fig = pickle.load(f)
    except Exception as e:
        print(f'Error loading {args.pkl}: {e}', file=sys.stderr)
        sys.exit(1)

    editor = PositionEditor(fig)
    editor.run()


if __name__ == '__main__':
    _cli()
