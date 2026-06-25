"""Core figure composition functionality for sciplotlib.

Provides the shared rendering logic used by both the GUI/CLI in layout.py
and the programmatic Python API (FigureComposer).
"""

import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from matplotlib.gridspec import GridSpec
from matplotlib.lines import Line2D
from matplotlib.collections import PathCollection
from matplotlib.patches import Rectangle
from pathlib import Path
import pickle
import io
import json
import yaml
from copy import copy


PAPER_DIMENSIONS = {
    'a4': (21.0, 29.7),
    'a4_half_portrait': (10.5, 29.7),
    'a0_portrait': (84.1, 118.9),
    'a0_landscape': (118.9, 84.1),
    '16:9_monitor': (59.7, 33.6),
}


def cm_to_px(cm, dpi=96):
    return int(cm * dpi / 2.54)


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------

def copy_axes_content(src_ax, dest_ax, scale_factor=1.0):
    """Copy data artists and properties from a source axes to a destination axes.

    Creates new artist instances to avoid reuse errors when transferring
    content between figures (e.g. from a pickled figure into a composed layout).
    """
    import matplotlib.text as mtext
    from matplotlib.offsetbox import AnnotationBbox, OffsetImage

    for line in src_ax.lines:
        new_line = Line2D(
            xdata=line.get_xdata(), ydata=line.get_ydata(),
            color=line.get_color(), linestyle=line.get_linestyle(),
            linewidth=line.get_linewidth() * scale_factor, marker=line.get_marker(),
            markersize=line.get_markersize() * scale_factor, label=line.get_label(),
        )
        dest_ax.add_line(new_line)

    for collection in src_ax.collections:
        if isinstance(collection, PathCollection):
            offsets = collection.get_offsets()
            dest_ax.scatter(
                offsets[:, 0], offsets[:, 1],
                s=collection.get_sizes() * (scale_factor ** 2),
                c=collection.get_facecolors(),
                marker=collection.get_paths()[0] if collection.get_paths() else 'o',
                alpha=collection.get_alpha(),
                linewidths=collection.get_linewidths() * scale_factor,
                edgecolors=collection.get_edgecolors(),
                label=collection.get_label(),
            )
            if collection.get_array() is not None:
                new_coll = dest_ax.collections[-1]
                new_coll.set_array(collection.get_array())
                new_coll.set_cmap(collection.get_cmap())
                new_coll.set_norm(collection.get_norm())

    for patch in src_ax.patches:
        if isinstance(patch, Rectangle):
            new_patch = Rectangle(
                xy=patch.get_xy(), width=patch.get_width(),
                height=patch.get_height(), angle=patch.get_angle(),
                facecolor=patch.get_facecolor(), edgecolor=patch.get_edgecolor(),
                linewidth=patch.get_linewidth() * scale_factor, linestyle=patch.get_linestyle(),
                alpha=patch.get_alpha(), label=patch.get_label(),
            )
            dest_ax.add_patch(new_patch)
        else:
            new_patch = copy(patch)
            if hasattr(new_patch, 'set_linewidth'):
                new_patch.set_linewidth(patch.get_linewidth() * scale_factor)
            dest_ax.add_patch(new_patch)

    for image in src_ax.images:
        new_img = dest_ax.imshow(
            image.get_array(), extent=image.get_extent(),
            cmap=image.get_cmap(), norm=image.norm,
            origin=getattr(image, '_origin', 'upper'),
            interpolation=image.get_interpolation(),
        )
        new_img.set_clim(image.get_clim())

    for text in src_ax.texts:
        if isinstance(text, mtext.Annotation):
            xytext = text.xytext
            if text.textcoords == 'offset points':
                xytext = (xytext[0] * scale_factor, xytext[1] * scale_factor)
            arrowprops = copy(text.arrowprops) if text.arrowprops else None
            if arrowprops:
                for k in ['width', 'headwidth', 'headlength', 'shrink']:
                    if k in arrowprops:
                        arrowprops[k] = arrowprops[k] * scale_factor
            dest_ax.annotate(
                text.get_text(), xy=text.xy, xytext=xytext,
                textcoords=text.textcoords, xycoords=text.xycoords,
                arrowprops=arrowprops, ha=text.get_ha(), va=text.get_va(),
                fontsize=text.get_fontsize() * scale_factor, color=text.get_color(),
                fontweight=text.get_fontweight(), fontstyle=text.get_fontstyle(),
                fontfamily=text.get_fontfamily(), zorder=text.get_zorder(),
            )
        else:
            dest_ax.text(
                *text.get_position(), text.get_text(),
                transform=dest_ax.transData,
                ha=text.get_ha(), va=text.get_va(),
                fontsize=text.get_fontsize() * scale_factor, color=text.get_color(),
                fontweight=text.get_fontweight(), fontstyle=text.get_fontstyle(),
                fontfamily=text.get_fontfamily(), zorder=text.get_zorder(),
            )

    for artist in src_ax.artists:
        if isinstance(artist, AnnotationBbox):
            offsetbox = artist.offsetbox
            if isinstance(offsetbox, OffsetImage):
                new_zoom = offsetbox.get_zoom() * scale_factor
                new_oi = OffsetImage(offsetbox.get_data(), zoom=new_zoom)
                xybox = artist.xybox
                if artist.boxcoords == 'offset points':
                    xybox = (xybox[0] * scale_factor, xybox[1] * scale_factor)
                new_ab = AnnotationBbox(
                    new_oi, artist.xy, xybox=xybox,
                    boxcoords=artist.boxcoords,
                    frameon=artist.patch.get_visible(),
                    zorder=artist.get_zorder(),
                )
                dest_ax.add_artist(new_ab)

    dest_ax.set_xlim(src_ax.get_xlim())
    dest_ax.set_ylim(src_ax.get_ylim())
    dest_ax.set_xscale(src_ax.get_xscale())
    dest_ax.set_yscale(src_ax.get_yscale())
    dest_ax.set_aspect(src_ax.get_aspect(),
                       adjustable=src_ax.get_adjustable(),
                       anchor=src_ax.get_anchor())
    dest_ax.set_title(src_ax.get_title())
    dest_ax.set_xlabel(src_ax.get_xlabel())
    dest_ax.set_ylabel(src_ax.get_ylabel())
    dest_ax.set_xticks(src_ax.get_xticks())
    dest_ax.set_xticklabels([l.get_text() for l in src_ax.get_xticklabels()])
    dest_ax.set_yticks(src_ax.get_yticks())
    dest_ax.set_yticklabels([l.get_text() for l in src_ax.get_yticklabels()])
    if src_ax.get_xgridlines():
        dest_ax.grid(src_ax.get_xgridlines()[0].get_visible())


def render_svg(filepath, scale=4, output_width=None):
    """Render an SVG file to a numpy RGBA array.

    Parameters
    ----------
    filepath : str or Path
        Path to the SVG file.
    scale : float
        Resolution multiplier. Ignored when *output_width* is set.
    output_width : int, optional
        Render the SVG to exactly this many pixels wide (height scales
        to preserve aspect ratio).  Much more memory-efficient than a
        large *scale* when the display size is known.

    Returns
    -------
    img : numpy array (H, W, 4) with values in [0, 1].
    """
    import cairosvg
    filepath = Path(filepath)
    kwargs = {'url': str(filepath)}
    if output_width is not None:
        kwargs['output_width'] = output_width
    else:
        kwargs['scale'] = scale
    png_bytes = cairosvg.svg2png(**kwargs)
    buf = io.BytesIO(png_bytes)
    return mpimg.imread(buf, format='png')


def tint_image(img, color):
    """Recolor an RGBA image array by replacing RGB values on opaque pixels.

    Parameters
    ----------
    img : numpy array
        An RGBA image array (H, W, 4) with values in [0, 1] or [0, 255].
    color : str or tuple
        Matplotlib color description.

    Returns
    -------
    out : numpy array
        The recolored image.
    """
    from matplotlib.colors import to_rgba
    r, g, b, _ = to_rgba(color)
    out = img.copy()
    if out.dtype.kind in 'iu':
        r_val, g_val, b_val = int(r * 255), int(g * 255), int(b * 255)
        mask = out[:, :, 3] > 12
    else:
        r_val, g_val, b_val = r, g, b
        mask = out[:, :, 3] > 0.05
    out[mask, 0] = r_val
    out[mask, 1] = g_val
    out[mask, 2] = b_val
    return out


def place_image(ax, img, x, y, zoom, zorder=5, frameon=False, **kwargs):
    """Place an image onto a matplotlib Axes using OffsetImage and AnnotationBbox.

    Parameters
    ----------
    ax : matplotlib.axes.Axes
        Target axes to draw into.
    img : numpy array
        The image array to place.
    x, y : float
        Coordinates in axes data space to place the image center.
    zoom : float
        Zoom factor for the image.
    zorder : int, default 5
        Z-order for the artist.
    frameon : bool, default False
        Whether to draw a frame around the image.
    **kwargs
        Passed to matplotlib.offsetbox.AnnotationBbox.

    Returns
    -------
    ab : matplotlib.offsetbox.AnnotationBbox
        The created AnnotationBbox artist.
    """
    from matplotlib.offsetbox import OffsetImage, AnnotationBbox
    im = OffsetImage(img, zoom=zoom)
    ab = AnnotationBbox(im, (x, y), frameon=frameon, zorder=zorder, **kwargs)
    ax.add_artist(ab)
    return ab


def create_inset_grid(ax, nrows, ncols, sharex=False, sharey=False,
                      wspace=0.1, hspace=0.1, left=0.0, bottom=0.0,
                      width=1.0, height=1.0,
                      keep_aspect=False, source_figsize=None):
    """Create a grid of inset axes within a parent axes.

    Returns a numpy array of axes shaped (nrows, ncols), matching the
    output of ``plt.subplots()``.  Supports ``sharex`` and ``sharey``
    so that generic plotting functions that expect ``plt.subplots()``
    output work without modification.

    Parameters
    ----------
    ax : matplotlib.axes.Axes
        Parent axes (typically with ``ax.axis('off')``).
    nrows, ncols : int
        Grid dimensions.
    sharex, sharey : bool
        Share x/y axes across the grid.
    wspace, hspace : float
        Horizontal/vertical gap between subplots, as a fraction of
        the subplot width/height.
    left, bottom, width, height : float
        Bounding box of the grid within the parent axes, in
        axes-fraction coordinates.  Defaults to the full axes.
    keep_aspect : bool
        If True, preserve the aspect ratio of the original figure
        and center the grid within the panel, leaving whitespace.
        Requires *source_figsize* or falls back to a square aspect.
    source_figsize : tuple of (width, height), optional
        The (width, height) in inches of the original standalone
        figure.  Used with *keep_aspect* to compute the target
        aspect ratio.  E.g. ``source_figsize=(2, 2)`` for a square.

    Returns
    -------
    axes : numpy.ndarray of Axes, shape (nrows, ncols)

    Notes
    -----
    Because the parent axes typically has ``axis('off')``,
    ``fit_axes_to_cells`` will skip it — meaning axis labels on the
    inset axes (e.g. ylabel text like "Win" / "Loss") can overflow
    the panel boundary.  Use the *left* parameter to reserve space::

        create_inset_grid(ax, 2, 2, left=0.12, width=0.88, ...)

    This is needed whenever inset subplots have y-axis labels or
    tick labels on the left edge.  The same applies to *bottom* for
    x-axis labels on the bottom edge.
    """
    import numpy as np

    if keep_aspect:
        fig = ax.figure
        pos = ax.get_position()
        fig_w, fig_h = fig.get_size_inches()
        panel_w = pos.width * fig_w
        panel_h = pos.height * fig_h

        src_w, src_h = source_figsize if source_figsize else (1.0, 1.0)
        src_aspect = src_w / src_h

        panel_aspect = panel_w / panel_h
        if src_aspect > panel_aspect:
            used_w = width
            used_h = width * (panel_w / panel_h) / src_aspect * (height / width)
            left_off = left
            bottom_off = bottom + (height - used_h) / 2
        else:
            used_h = height
            used_w = height * (panel_h / panel_w) * src_aspect * (width / height)
            left_off = left + (width - used_w) / 2
            bottom_off = bottom

        left, bottom, width, height = left_off, bottom_off, used_w, used_h

    cell_w = (width - wspace * (ncols - 1)) / ncols
    cell_h = (height - hspace * (nrows - 1)) / nrows

    axes = np.empty((nrows, ncols), dtype=object)
    ref_x = None
    ref_y = None

    for r in range(nrows):
        for c in range(ncols):
            x0 = left + c * (cell_w + wspace)
            y0 = bottom + height - (r + 1) * cell_h - r * hspace
            sa = ax.inset_axes([x0, y0, cell_w, cell_h])
            if sharex and ref_x is not None:
                sa.sharex(ref_x)
            if sharey and ref_y is not None:
                sa.sharey(ref_y)
            if ref_x is None:
                ref_x = sa
            if ref_y is None:
                ref_y = sa
            axes[r, c] = sa

    return axes


def figure_to_image(fig, width=None, dpi=None, **kwargs):
    """Convert a matplotlib Figure to a marimo-compatible HTML image.

    Prevents aspect-ratio squishing in the marimo UI by rendering the figure
    to PNG bytes with its native physical aspect ratio.
    """
    import io
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight', dpi=dpi or fig.dpi)
    plt.close(fig)
    buf.seek(0)
    if width is None:
        # Default to 96 CSS pixels per inch
        width = int(fig.get_size_inches()[0] * 96)
    try:
        import marimo as mo
        return mo.image(src=buf, width=width, **kwargs)
    except ImportError:
        return buf.read()


def load_panel_content(ax, filepath, fig=None):
    """Load an image or pickled matplotlib figure into an axes.

    Parameters
    ----------
    ax : matplotlib.axes.Axes
        Target axes to draw into.
    filepath : str or Path
        Path to an image (.png/.jpg/.jpeg), SVG placeholder, or pickled
        figure (.pkl).
    fig : matplotlib.figure.Figure, optional
        Parent figure, needed when a .pkl contains multiple sub-axes so
        that sub-gridspecs can be created.
    """
    filepath = Path(filepath)
    suffix = filepath.suffix.lower()

    if suffix in ('.png', '.jpg', '.jpeg'):
        img = mpimg.imread(str(filepath))
        ax.imshow(img)
        ax.set_box_aspect(img.shape[0] / img.shape[1])
        ax.axis('off')
    elif suffix == '.svg':
        img = render_svg(filepath)
        ax.imshow(img)
        ax.set_box_aspect(img.shape[0] / img.shape[1])
        ax.axis('off')
    elif suffix == '.pkl':
        try:
            with open(filepath, 'rb') as f:
                original_fig = pickle.load(f)
            buf = io.BytesIO()
            pickle.dump(original_fig, buf)
            buf.seek(0)
            fig_copy = pickle.load(buf)
            source_axes = fig_copy.get_axes()

            src_fig_w, src_fig_h = fig_copy.get_size_inches()
            parent_fig = fig or ax.figure
            dest_fig_w, dest_fig_h = parent_fig.get_size_inches()

            if len(source_axes) == 1:
                src_ax = source_axes[0]
                src_pos = src_ax.get_position()
                src_w = src_pos.width * src_fig_w
                src_h = src_pos.height * src_fig_h
                
                dest_pos = ax.get_position()
                dest_w = dest_pos.width * dest_fig_w
                scale_factor = dest_w / src_w if src_w > 0 else 1.0

                ax.set_box_aspect(src_h / src_w)
                copy_axes_content(src_ax, ax, scale_factor=scale_factor)
            elif fig is not None:
                ax.axis('off')
                inner_gs = ax.get_subplotspec().subgridspec(
                    1, len(source_axes), wspace=0.3)
                for i, src_ax in enumerate(source_axes):
                    sub_ax = fig.add_subplot(inner_gs[0, i])
                    
                    src_pos = src_ax.get_position()
                    src_w = src_pos.width * src_fig_w
                    src_h = src_pos.height * src_fig_h
                    
                    sub_pos = sub_ax.get_position()
                    sub_w = sub_pos.width * dest_fig_w
                    sub_scale = sub_w / src_w if src_w > 0 else 1.0

                    sub_ax.set_box_aspect(src_h / src_w)
                    copy_axes_content(src_ax, sub_ax, scale_factor=sub_scale)
            plt.close(fig_copy)
        except Exception as e:
            ax.text(0.5, 0.5, f'Failed to load:\n{filepath.name}',
                    ha='center', va='center', transform=ax.transAxes)
    else:
        ax.text(0.5, 0.5, f'Unsupported: {suffix}',
                ha='center', va='center', transform=ax.transAxes)
        ax.set_facecolor('#f0f0f0')


def get_axes_scale_factor(ax, ref_width_inches=3.5):
    """Calculate a scale factor for scaling plot elements (fonts, line widths, offsets)
    based on the physical width of the axes relative to a reference width.
    """
    fig = ax.figure
    fig_w, _ = fig.get_size_inches()
    pos = ax.get_position()
    current_w = pos.width * fig_w
    return current_w / ref_width_inches


# ---------------------------------------------------------------------------
# Layout file parsing
# ---------------------------------------------------------------------------

def parse_layout_file(filepath):
    """Parse a YAML or JSON layout file into a normalized dict.

    Returns
    -------
    dict with keys:
        paper_w_cm, paper_h_cm : float
        grid_rows, grid_cols   : int
        style                  : dict (stylesheet, font, font_size, …)
        panels                 : list of dict (label, row, col, rowspan, colspan, file)
    """
    filepath = Path(filepath)
    suffix = filepath.suffix.lower()

    with open(filepath, 'r') as f:
        if suffix in ('.yaml', '.yml'):
            data = yaml.safe_load(f)
        else:
            data = json.load(f)

    # --- Legacy JSON format (from the GUI's _save_json) ---
    if 'grid_settings' in data:
        grid_rows = data['grid_settings']['rows']
        grid_cols = data['grid_settings']['cols']
        paper_size = data['paper_settings']['size_name']
        custom_w = data['paper_settings']['custom_width_cm']
        custom_h = data['paper_settings']['custom_height_cm']
        style_info = {}

        if paper_size == 'custom':
            pw, ph = custom_w, custom_h
        else:
            pw, ph = PAPER_DIMENSIONS.get(paper_size, (21.0, 29.7))
        true_w = cm_to_px(pw, 96)
        true_h = cm_to_px(ph, 96)
        canvas_w, canvas_h = 700, 1200
        scale = 1.0
        if true_w > canvas_w or true_h > canvas_h:
            scale = min(canvas_w / true_w, canvas_h / true_h)
        disp_w = true_w * scale
        disp_h = true_h * scale

        panels = []
        for p in data['panels']:
            x0, y0, x1, y1 = p['bbox']
            col0 = int(round((x0 - 50) / disp_w * grid_cols))
            row0 = int(round((y0 - 50) / disp_h * grid_rows))
            col1 = int(round((x1 - 50) / disp_w * grid_cols))
            row1 = int(round((y1 - 50) / disp_h * grid_rows))
            panels.append({
                'label': p.get('label', ''),
                'row': row0, 'col': col0,
                'rowspan': row1 - row0, 'colspan': col1 - col0,
                'file': p.get('filepath'),
            })

    # --- YAML format (from the GUI's _save_yaml) ---
    else:
        grid_rows = data.get('grid', {}).get('rows', 20)
        grid_cols = data.get('grid', {}).get('cols', 10)
        paper_size = data.get('paper', {}).get('size', 'a4')
        custom_w = data.get('paper', {}).get('width_cm', 21.0)
        custom_h = data.get('paper', {}).get('height_cm', 29.7)
        style_info = data.get('style', {})
        panels = []
        for p in data.get('panels', []):
            panels.append({
                'label': p.get('label', ''),
                'row': p.get('row', 0),
                'col': p.get('col', 0),
                'rowspan': p.get('rowspan', 2),
                'colspan': p.get('colspan', 2),
                'file': p.get('file'),
            })

    if paper_size == 'custom':
        paper_w_cm, paper_h_cm = custom_w, custom_h
    else:
        paper_w_cm, paper_h_cm = PAPER_DIMENSIONS.get(paper_size, (21.0, 29.7))

    return {
        'paper_w_cm': paper_w_cm,
        'paper_h_cm': paper_h_cm,
        'grid_rows': grid_rows,
        'grid_cols': grid_cols,
        'style': style_info,
        'panels': panels,
    }


# ---------------------------------------------------------------------------
# Mid-level rendering
# ---------------------------------------------------------------------------

def clip_all_axes(fig):
    """Clip non-text artists in every axes of *fig* to the axes bounding box.

    Prevents lines, markers, patches, and images from overflowing into
    neighbouring panels.  The following are **never** clipped:

    - **Text** objects — panel labels, axis labels, and annotations are
      placed intentionally and may legitimately sit outside the axes box.
    - **Spine** objects — spines sit exactly at the axes boundary.
      Applying a clip-path to a spine cuts off the outer half of its
      stroke, making it render at half the specified ``stroke-width``.
      For example, a 0.7 pt spine appears as 0.35 pt when clipped.
      This is a subtle SVG/PDF rendering issue: the ``stroke-width``
      attribute is correct, but the ``clip-path`` silently halves the
      visible line.  Inset axes (child_axes) are not returned by
      ``fig.get_axes()`` and therefore escape this clipping, which
      causes inconsistent spine widths across panels.
    """
    from matplotlib.text import Text
    from matplotlib.spines import Spine
    for ax in fig.get_axes():
        bbox = ax.get_clip_box() or ax.bbox
        for artist in ax.get_children():
            if isinstance(artist, (Text, Spine)):
                continue
            artist.set_clip_on(True)
            artist.set_clip_box(bbox)


def render_panels_to_figure(panels, grid_rows, grid_cols, fig,
                            label_font_size=14, label_weight='bold',
                            label_x=0.0, label_y=0.01, label_ha='left',
                            wspace=None, hspace=None, margins=None,
                            axes_pad=None):
    """Render a list of panel dicts onto a matplotlib figure.

    Parameters
    ----------
    panels : list of dict
        Each dict must have keys: label, row, col, rowspan, colspan.
        Optional key: file (path to image or .pkl).
    grid_rows, grid_cols : int
        Grid dimensions for the GridSpec.
    fig : matplotlib.figure.Figure
        Target figure.
    label_font_size : float
        Font size for panel labels.
    label_weight : str
        Font weight for panel labels.
    label_x, label_y : float
        Offset of the panel label from the gridspec cell's top-left corner,
        in figure-fraction coordinates.
    wspace, hspace : float or None
        Spacing passed to GridSpec.
    margins : dict, optional
        GridSpec margins with keys 'left', 'right', 'top', 'bottom'
        (figure-fraction). Use to reserve space for axis labels on
        edge panels.
    axes_pad : dict, optional
        Inset each axes from its gridspec cell to leave room for axis
        decorations (tick labels, axis labels). Keys 'left', 'right',
        'top', 'bottom' in figure-fraction units. The panel label is
        placed at the cell boundary, and the axes is shrunk inward.

    Returns
    -------
    axes : dict
        Mapping of panel label → matplotlib Axes.
    """
    gs_kwargs = {}
    if wspace is not None:
        gs_kwargs['wspace'] = wspace
    if hspace is not None:
        gs_kwargs['hspace'] = hspace
    if margins is not None:
        for key in ('left', 'right', 'top', 'bottom'):
            if key in margins:
                gs_kwargs[key] = margins[key]
    gs = GridSpec(grid_rows, grid_cols, figure=fig, **gs_kwargs)

    axes = {}
    for p in panels:
        r0, c0 = p['row'], p['col']
        r1, c1 = r0 + p['rowspan'], c0 + p['colspan']
        r0 = max(0, min(r0, grid_rows - 1))
        c0 = max(0, min(c0, grid_cols - 1))
        r1 = max(r0 + 1, min(r1, grid_rows))
        c1 = max(c0 + 1, min(c1, grid_cols))

        ax = fig.add_subplot(gs[r0:r1, c0:c1])

        pad = p.get('axes_pad', axes_pad)
        if pad is not None:
            cell = ax.get_position()
            pl = pad.get('left', 0)
            pb = pad.get('bottom', 0)
            pr = pad.get('right', 0)
            pt = pad.get('top', 0)
            ax.set_position([
                cell.x0 + pl, cell.y0 + pb,
                cell.width - pl - pr, cell.height - pb - pt,
            ])

        axes[p.get('label', '')] = ax

        label = p.get('label', '')
        if label:
            pos = gs[r0:r1, c0:c1].get_position(fig)
            fig.text(pos.x0 + label_x, pos.y1 + label_y, label,
                     fontsize=label_font_size, fontweight=label_weight,
                     va='bottom', ha=label_ha)

        ax.tick_params(bottom=False, left=False, labelbottom=False, labelleft=False)

        fp = p.get('file')
        if fp:
            load_panel_content(ax, fp, fig)

    return axes


# ---------------------------------------------------------------------------
# High-level Python API
# ---------------------------------------------------------------------------

class FigureComposer:
    """Compose multi-panel scientific figures using a grid layout.

    Example
    -------
    >>> composer = FigureComposer(width_cm=18, height_cm=21, grid_rows=24, grid_cols=20)
    >>> composer.add_panel('a', row=0, col=0, rowspan=3, colspan=10)
    >>> composer.add_panel('b', row=0, col=10, rowspan=3, colspan=10)
    >>> fig, axes = composer.compose()
    >>> axes['a'].plot([1, 2, 3], [1, 4, 9])
    >>> composer.save('my_figure')
    """

    def __init__(self, width_cm=18, height_cm=24, grid_rows=24, grid_cols=20,
                 label_font_size=14, label_weight='bold',
                 label_x=0.0, label_y=0.01, label_ha='left', dpi=300,
                 stylesheet=None, rc_params=None,
                 font_size=None, axis_label_font_size=None, title_font_size=None,
                 margins=None, axes_pad=None,
                 wspace=0.4, hspace=0.5,
                 spine_linewidth=None, tick_linewidth=None, tick_length=None,
                 tick_pad=None, axis_label_pad=None):
        self.width_cm = width_cm
        self.height_cm = height_cm
        self.grid_rows = grid_rows
        self.grid_cols = grid_cols
        self.label_font_size = label_font_size
        self.label_weight = label_weight
        self.label_x = label_x
        self.label_y = label_y
        self.label_ha = label_ha
        self.dpi = dpi
        self.stylesheet = stylesheet
        self.rc_params = rc_params or {}
        self.font_size = font_size
        self.axis_label_font_size = axis_label_font_size
        self.title_font_size = title_font_size
        self.margins = margins
        self.axes_pad = axes_pad
        self.wspace = wspace
        self.hspace = hspace
        self.spine_linewidth = spine_linewidth
        self.tick_linewidth = tick_linewidth
        self.tick_length = tick_length
        self.tick_pad = tick_pad
        self.axis_label_pad = axis_label_pad
        self.panels = []
        self._fig = None
        self._axes = None

    def apply_style(self):
        """Apply the composer's stylesheet and rc_params globally.

        Call once at the start of a notebook so all subsequent plotting
        uses the same fonts, tick sizes, etc.::

            composer = FigureComposer(..., stylesheet='mp-paper',
                                     rc_params={'axes.labelsize': 9})
            composer.apply_style()
        """
        if self.stylesheet:
            import sciplotlib.style as splstyle
            plt.style.use(splstyle.get_style(self.stylesheet))
        
        # Apply custom font sizes to rcParams
        if self.font_size is not None:
            plt.rcParams['font.size'] = self.font_size
            plt.rcParams['xtick.labelsize'] = self.font_size
            plt.rcParams['ytick.labelsize'] = self.font_size
            plt.rcParams['legend.fontsize'] = self.font_size

        # Apply axis label font size (default to general font_size)
        ax_label_sz = self.axis_label_font_size
        if ax_label_sz is None:
            ax_label_sz = self.font_size
        if ax_label_sz is not None:
            plt.rcParams['axes.labelsize'] = ax_label_sz

        # Apply title font size (default to general font_size)
        title_sz = self.title_font_size
        if title_sz is None:
            title_sz = self.font_size
        if title_sz is not None:
            plt.rcParams['axes.titlesize'] = title_sz

        if self.rc_params:
            plt.rcParams.update(self.rc_params)

    def add_panel(self, label, row, col, rowspan, colspan, file=None, no_axis=False, axes_pad=None):
        """Add a panel to the layout.

        Parameters
        ----------
        axes_pad : dict or None
            Per-panel override for axes inset padding. Set to ``{}``
            to disable the global axes_pad for this panel. ``None``
            (default) inherits the composer's global axes_pad.

        Returns self for method chaining.
        """
        self.panels.append({
            'label': label,
            'row': row,
            'col': col,
            'rowspan': rowspan,
            'colspan': colspan,
            'file': str(file) if file else None,
            'no_axis': no_axis,
            'axes_pad': axes_pad,
        })
        return self

    def panel_figsize(self, label, wspace=None, hspace=None):
        """Return (width_inches, height_inches) for a panel, matching
        the exact physical size it occupies in the composed figure.

        Uses matplotlib's own GridSpec positioning internally so the
        result is pixel-accurate.  Defaults to the composer's wspace/hspace.
        """
        for p in self.panels:
            if p['label'] == label:
                fig_w = self.width_cm / 2.54
                fig_h = self.height_cm / 2.54
                gs_kwargs = dict(
                    wspace=wspace if wspace is not None else self.wspace,
                    hspace=hspace if hspace is not None else self.hspace,
                )
                if self.margins is not None:
                    for key in ('left', 'right', 'top', 'bottom'):
                        if key in self.margins:
                            gs_kwargs[key] = self.margins[key]
                gs = GridSpec(self.grid_rows, self.grid_cols, **gs_kwargs)
                r0, c0 = p['row'], p['col']
                ss = gs[r0:r0 + p['rowspan'], c0:c0 + p['colspan']]
                tmp_fig = plt.figure(figsize=(fig_w, fig_h))
                pos = ss.get_position(tmp_fig)
                plt.close(tmp_fig)
                w_in = (pos.x1 - pos.x0) * fig_w
                h_in = (pos.y1 - pos.y0) * fig_h
                if self.axes_pad is not None:
                    w_in -= (self.axes_pad.get('left', 0) + self.axes_pad.get('right', 0)) * fig_w
                    h_in -= (self.axes_pad.get('bottom', 0) + self.axes_pad.get('top', 0)) * fig_h
                return (w_in, h_in)
        raise KeyError(f"No panel with label '{label}'")

    def preview(self, label, wspace=None, hspace=None, pad_inches=(2.0, 1.0)):
        """Create a preview figure+axes that matches the physical size, DPI,
        and style of a panel in the composed figure.

        Includes optional padding (width, height) in inches around the axes to prevent
        clipping of elements (like annotations or OffsetImages) that bleed outside
        the formal gridspec boundaries.  Defaults to the composer's wspace/hspace.
        """
        size = self.panel_figsize(label, wspace=wspace, hspace=hspace)
        if pad_inches:
            pad_w, pad_h = pad_inches
            fig = plt.figure(figsize=(size[0] + pad_w, size[1] + pad_h), dpi=self.dpi)
            ax = fig.add_axes([
                (pad_w / 2) / (size[0] + pad_w),
                (pad_h / 2) / (size[1] + pad_h),
                size[0] / (size[0] + pad_w),
                size[1] / (size[1] + pad_h)
            ])
        else:
            fig, ax = plt.subplots(figsize=size, dpi=self.dpi)
            fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
        return fig, ax

    def preview_image(self, label, wspace=None, hspace=None, plot_func=None, width=None, pad_inches=(2.0, 1.0), **kwargs):
        """Create a preview of a panel and return it as a marimo-compatible HTML image.

        This avoids aspect-ratio squishing in the marimo UI by rendering the panel
        to PNG bytes with its native physical aspect ratio.

        Parameters
        ----------
        label : str
            The panel label.
        wspace, hspace : float or None
            Grid spacing parameters.  Defaults to the composer's wspace/hspace.
        plot_func : callable, optional
            A function that takes an Axes object and plots the panel content.
            If provided, it will be executed on the preview axes before rendering.
        width : int or str, optional
            The display width of the image. Defaults to the calculated physical size
            in CSS pixels (96 pixels per inch).
        pad_inches : tuple of float, optional
            Width and height padding in inches to add around the axes to prevent clipping
            of overflowing content. Defaults to (2.0, 1.0).
        **kwargs
            Passed to marimo.image.
        """
        fig, ax = self.preview(label, wspace=wspace, hspace=hspace, pad_inches=pad_inches)
        if plot_func is not None:
            plot_func(ax)
        if width is None:
            size = self.panel_figsize(label, wspace=wspace, hspace=hspace)
            width = int(size[0] * 96)
        return figure_to_image(fig, width=width, dpi=self.dpi, **kwargs)

    def compose(self, wspace=None, hspace=None, clip_panels=True):
        """Create the composed figure with all panels on a grid.

        Parameters
        ----------
        wspace, hspace : float or None
            Spacing passed to GridSpec.  Defaults to the composer's wspace/hspace.
        clip_panels : bool
            If True (default), clip all panel contents to the axes
            bounding box so plots cannot overflow into neighbouring panels.

        Returns
        -------
        fig : matplotlib.figure.Figure
        axes : dict mapping panel label → Axes
        """
        wspace = wspace if wspace is not None else self.wspace
        hspace = hspace if hspace is not None else self.hspace

        fig_w = self.width_cm / 2.54
        fig_h = self.height_cm / 2.54

        fig = plt.figure(figsize=(fig_w, fig_h), dpi=self.dpi)
        axes = render_panels_to_figure(
            self.panels, self.grid_rows, self.grid_cols, fig,
            label_font_size=self.label_font_size,
            label_weight=self.label_weight,
            label_x=self.label_x,
            label_y=self.label_y,
            label_ha=self.label_ha,
            wspace=wspace, hspace=hspace,
            margins=self.margins,
            axes_pad=self.axes_pad,
        )

        # For panels with no_axis=True, turn off axes after render
        for p in self.panels:
            if p.get('no_axis') and p['label'] in axes:
                axes[p['label']].axis('off')

        if clip_panels:
            clip_all_axes(fig)

        self._fig = fig
        self._axes = axes
        self._wspace = wspace
        self._hspace = hspace
        self._panel_label_ids = {id(t) for t in fig.texts}
        return fig, axes

    def normalize_fonts(self):
        """Normalize all text sizes in the composed figure to the composer's settings.

        Called automatically by :meth:`to_image` and :meth:`save`.

        Mapping:
        - Tick labels → font_size
        - Axis labels (xlabel / ylabel) → axis_label_font_size
        - Axes titles → title_font_size
        - Free text above axes (transAxes y > 1) → title_font_size
        - Free text inside axes → font_size
        - Panel labels → label_font_size (unchanged)
        """
        if self._fig is None:
            return

        font_sz = self.font_size or plt.rcParams.get('font.size', 10)
        label_sz = self.axis_label_font_size or font_sz
        title_sz = self.title_font_size or font_sz

        label_pad = self.axis_label_pad

        def _apply_fonts(ax):
            ax.tick_params(labelsize=font_sz)
            ax.xaxis.label.set_fontsize(label_sz)
            ax.yaxis.label.set_fontsize(label_sz)
            if label_pad is not None:
                _default_pad = plt.rcParams.get('axes.labelpad', 4.0)
                if ax.xaxis.labelpad == _default_pad:
                    ax.xaxis.labelpad = label_pad
                if ax.yaxis.labelpad == _default_pad:
                    ax.yaxis.labelpad = label_pad
            if ax.get_title():
                ax.title.set_fontsize(title_sz)

            for text in ax.texts:
                if text.get_transform() is ax.transAxes:
                    _, y = text.get_position()
                    text.set_fontsize(title_sz if y > 1.0 else font_sz)
                else:
                    text.set_fontsize(font_sz)

            for child in getattr(ax, 'child_axes', []):
                _apply_fonts(child)

        for ax in self._fig.get_axes():
            _apply_fonts(ax)

        panel_ids = getattr(self, '_panel_label_ids', set())
        for text in self._fig.texts:
            if id(text) in panel_ids:
                continue
            text.set_fontsize(font_sz)

    def normalize_spines(self):
        """Normalize spine linewidths and tick sizes across all axes.

        Called automatically by :meth:`to_image` and :meth:`save`.
        Uses the composer's spine_linewidth, tick_linewidth, and tick_length
        settings. If not set, reads from current rcParams as defaults.

        Also sets rcParams so that any subsequent redraw (e.g. by savefig
        with bbox_inches='tight') preserves the normalized values.
        """
        if self._fig is None:
            return

        spine_lw = self.spine_linewidth
        tick_lw = self.tick_linewidth
        if spine_lw is not None and tick_lw is None:
            tick_lw = spine_lw
        elif tick_lw is not None and spine_lw is None:
            spine_lw = tick_lw
        elif spine_lw is None and tick_lw is None:
            spine_lw = plt.rcParams.get('axes.linewidth', 0.8)
            tick_lw = spine_lw
        tick_len = self.tick_length
        if tick_len is None:
            tick_len = plt.rcParams.get('xtick.major.size', 3.5)
        tick_pad = self.tick_pad

        plt.rcParams['axes.linewidth'] = spine_lw
        plt.rcParams['xtick.major.width'] = tick_lw
        plt.rcParams['ytick.major.width'] = tick_lw
        plt.rcParams['xtick.minor.width'] = tick_lw
        plt.rcParams['ytick.minor.width'] = tick_lw
        plt.rcParams['xtick.major.size'] = tick_len
        plt.rcParams['ytick.major.size'] = tick_len
        if tick_pad is not None:
            plt.rcParams['xtick.major.pad'] = tick_pad
            plt.rcParams['ytick.major.pad'] = tick_pad

        def _apply(ax):
            for spine in ax.spines.values():
                spine.set_linewidth(spine_lw)

            tp_kwargs = {'width': tick_lw}
            if tick_pad is not None:
                tp_kwargs['pad'] = tick_pad

            x_params = ax.xaxis.get_tick_params('major')
            y_params = ax.yaxis.get_tick_params('major')
            x_has_ticks = x_params.get('length', tick_len) > 0
            y_has_ticks = y_params.get('length', tick_len) > 0

            if x_has_ticks:
                ax.tick_params(axis='x', length=tick_len, **tp_kwargs)
            else:
                ax.tick_params(axis='x', length=0, **tp_kwargs)
            if y_has_ticks:
                ax.tick_params(axis='y', length=tick_len, **tp_kwargs)
            else:
                ax.tick_params(axis='y', length=0, **tp_kwargs)

            for child in getattr(ax, 'child_axes', []):
                _apply(child)

        for ax in self._fig.get_axes():
            _apply(ax)

    def fit_axes_to_cells(self, n_iterations=3, constrain_top=False):
        """Shrink each axes so its decorations fit within the gridspec cell.

        Uses matplotlib's tight bounding box to measure how much tick labels,
        axis labels, etc. overflow the cell boundary, then insets the axes
        accordingly. Called automatically by :meth:`to_image` and :meth:`save`.

        Panels whose main axes has ``axis('off')`` (i.e. ``axison == False``)
        are **skipped**, because they have no standard decorations to
        constrain.  This means that panels using ``ax.axis('off')`` with
        inset axes (via :func:`create_inset_grid`) need to manage their
        own margins — use the *left*, *bottom* parameters of
        :func:`create_inset_grid` to reserve space for axis labels on
        the inset subplots.

        Parameters
        ----------
        n_iterations : int
            Number of measure-and-adjust passes (2-3 is usually enough).
        constrain_top : bool
            If False (default), don't shrink axes to fit content above
            the cell (e.g. titles, algorithm labels placed above the axes).
        """
        if self._fig is None:
            return

        fig = self._fig
        gs_kwargs = dict(wspace=self._wspace, hspace=self._hspace)
        if self.margins is not None:
            for key in ('left', 'right', 'top', 'bottom'):
                if key in self.margins:
                    gs_kwargs[key] = self.margins[key]
        gs = GridSpec(self.grid_rows, self.grid_cols, **gs_kwargs)

        inv_fig = fig.transFigure.inverted()

        for _ in range(n_iterations):
            fig.canvas.draw()
            renderer = fig.canvas.get_renderer()

            for p in self.panels:
                label = p.get('label', '')
                if not label or label not in self._axes:
                    continue
                if p.get('axes_pad') is not None and p['axes_pad'] == {}:
                    continue

                ax = self._axes[label]
                if not ax.axison:
                    continue
                r0, c0 = p['row'], p['col']
                r1 = r0 + p['rowspan']
                c1 = c0 + p['colspan']
                cell = gs[r0:r1, c0:c1].get_position(fig)

                tight = ax.get_tightbbox(renderer)
                if tight is None:
                    continue
                tb = tight.transformed(inv_fig)

                pos = ax.get_position()
                dl = max(0, cell.x0 - tb.x0)
                db = max(0, cell.y0 - tb.y0)
                dr = max(0, tb.x1 - cell.x1)
                dt = max(0, tb.y1 - cell.y1) if constrain_top else 0

                if dl + db + dr + dt < 1e-6:
                    continue

                ax.set_position([
                    pos.x0 + dl, pos.y0 + db,
                    pos.width - dl - dr, pos.height - db - dt,
                ])

        # Align panels that share a grid row to the same y0 and height.
        # Uses the most-constrained panel (highest y0, lowest y1) as reference
        # so all siblings in the row match.
        from collections import defaultdict
        row_groups = defaultdict(list)
        for p in self.panels:
            label = p.get('label', '')
            if not label or label not in self._axes:
                continue
            row_groups[p['row']].append(label)

        for row_labels in row_groups.values():
            if len(row_labels) < 2:
                continue
            positions = [self._axes[l].get_position() for l in row_labels]
            max_y0 = max(p.y0 for p in positions)
            min_y1 = min(p.y0 + p.height for p in positions)
            for l in row_labels:
                pos = self._axes[l].get_position()
                self._axes[l].set_position([pos.x0, max_y0, pos.width, min_y1 - max_y0])

        # Align panels that share a grid column to the same x0.
        col_groups = defaultdict(list)
        for p in self.panels:
            label = p.get('label', '')
            if not label or label not in self._axes:
                continue
            ax = self._axes[label]
            if not ax.axison:
                continue
            col_groups[p['col']].append(label)

        for col_labels in col_groups.values():
            if len(col_labels) < 2:
                continue
            positions = [self._axes[l].get_position() for l in col_labels]
            max_x0 = max(p.x0 for p in positions)
            for l in col_labels:
                pos = self._axes[l].get_position()
                dx = max_x0 - pos.x0
                self._axes[l].set_position([max_x0, pos.y0, pos.width - dx, pos.height])

    def compose_image(self, wspace=None, hspace=None, clip_panels=True, width=None, **kwargs):
        """Compose the figure and return it as a marimo-compatible HTML image.

        Prevents aspect-ratio squishing in the marimo UI.
        """
        fig, axes = self.compose(wspace=wspace, hspace=hspace, clip_panels=clip_panels)
        return figure_to_image(fig, width=width, dpi=self.dpi, **kwargs)

    def to_image(self, width=None, **kwargs):
        """Return the current composed figure as a marimo-compatible HTML image.

        Useful when you want to compose and plot on the axes manually, and then
        render the final result as an image in marimo.
        """
        if self._fig is None:
            raise RuntimeError("Call compose() and plot on axes before calling to_image().")
        self.normalize_fonts()
        self.fit_axes_to_cells()
        self.normalize_spines()
        return figure_to_image(self._fig, width=width, dpi=self.dpi, **kwargs)

    def save(self, path, formats=('pdf', 'svg'), dpi=None, transparent=True):
        """Save the composed figure to one or more file formats."""
        if self._fig is None:
            raise RuntimeError("Call compose() before save().")
        self.normalize_fonts()
        self.fit_axes_to_cells()
        self.normalize_spines()

        dpi = dpi or self.dpi
        p = Path(path).with_suffix('')
        p.parent.mkdir(parents=True, exist_ok=True)

        for fmt in formats:
            save_path = p.with_suffix(f'.{fmt}')
            kwargs = {'dpi': dpi, 'bbox_inches': 'tight'}
            if fmt in ('svg', 'png'):
                kwargs['transparent'] = transparent
            self._fig.savefig(save_path, **kwargs)
            print(f"Saved: {save_path}")

    @classmethod
    def from_yaml(cls, filepath, **overrides):
        """Create a FigureComposer from a saved YAML/JSON layout file.

        Any keyword arguments override the values read from the file.
        """
        parsed = parse_layout_file(filepath)

        init_kwargs = {
            'width_cm': parsed['paper_w_cm'],
            'height_cm': parsed['paper_h_cm'],
            'grid_rows': parsed['grid_rows'],
            'grid_cols': parsed['grid_cols'],
        }
        init_kwargs.update(overrides)

        composer = cls(**init_kwargs)
        for p in parsed['panels']:
            composer.add_panel(
                label=p['label'],
                row=p['row'], col=p['col'],
                rowspan=p['rowspan'], colspan=p['colspan'],
                file=p.get('file'),
            )
        return composer

    @property
    def fig(self):
        return self._fig

    @property
    def axes(self):
        return self._axes
