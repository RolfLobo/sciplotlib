# /// script
# requires-python = ">=3.9"
# dependencies = [
#     "marimo>=0.9",
#     "matplotlib",
#     "numpy",
#     "pyyaml",
#     "scipy",
# ]
# ///
# sciplotlib itself is loaded via the sys.path hack in the imports cell below.
# Run standalone:  marimo edit --sandbox notebooks/preview_test.py
# Run in project:  uv run marimo edit notebooks/preview_test.py

import marimo

__generated_with = "0.23.11"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _():
    import marimo as mo
    mo.md("""
    # sciplotlib preview reliability test

    Each section below tests a different panel type.  For each one:

    1. A **standalone preview** is shown — this is `composer.preview(label)` at the
       exact physical size the panel will occupy in the final figure.
    2. After all panels are defined, the **full composed figure** is shown.

    Check that:
    - The preview and composed panel look the same (same proportions, fonts, clipping)
    - Colorbars, tick labels, and axis labels are not cut off
    - Inset subplots inside a panel render at correct sizes
    - The aspect ratio of `to_image()` is not squished
    """)
    return (mo,)


@app.cell
def _():
    import sys, os
    # Make sciplotlib importable whether running from notebooks/ or project root
    for _p in ['..', '.']:
        if os.path.isdir(os.path.join(_p, 'sciplotlib')) or os.path.isdir(os.path.join(_p, 'module')):
            sys.path.insert(0, _p)
            break

    import numpy as np
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    import matplotlib.colors as mcolors

    import sciplotlib.style as spstyle
    import sciplotlib.polish as sppolish
    import sciplotlib.text as sptext
    from sciplotlib.compose import FigureComposer, create_inset_grid, figure_to_image

    return (
        FigureComposer,
        create_inset_grid,
        mpatches,
        np,
        os,
        plt,
        sppolish,
        spstyle,
        sptext,
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## Composer layout
    """)
    return


@app.cell
def _(FigureComposer):
    # 2-column layout, 6 panels.
    # Panels A-D are in equal-sized quadrants; E is a wider subplot grid; F is shapes.
    composer = FigureComposer(
        width_cm=18,
        height_cm=22,
        grid_rows=28,
        grid_cols=20,
        stylesheet='nature-reviews',
        font_size=8,
        axis_label_font_size=9,
        title_font_size=9,
        spine_linewidth=0.6,
        tick_linewidth=0.6,
        tick_length=3,
        wspace=0.5,
        hspace=0.6,
        dpi=150,
    )
    return (composer,)


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## Panel functions
    """)
    return


@app.cell
def _(np, sppolish, spstyle):
    """A — line plot with fill_between (tests lines and area fills)."""
    def draw_A(ax):
        rng = np.random.default_rng(0)
        x = np.linspace(0, 4 * np.pi, 300)
        y1 = np.sin(x)
        y2 = np.sin(x + 0.5) + 0.3
        noise = rng.normal(0, 0.15, x.shape)
        colors = spstyle.get_palette('nature-reviews')
        ax.plot(x, y1, color=colors[0], label='sin(x)')
        ax.plot(x, y2 + noise, color=colors[1], linewidth=0.8, alpha=0.7, label='noisy')
        ax.fill_between(x, y1 - 0.2, y1 + 0.2, color=colors[0], alpha=0.2)
        ax.set_xlabel('x (rad)')
        ax.set_ylabel('Amplitude')
        ax.legend(frameon=False, fontsize=7)
        sppolish.set_bounds(ax.get_figure(), ax)

    return (draw_A,)


@app.cell
def _(np, plt):
    """B — scatter plot with colormap and colorbar."""
    def draw_B(ax):
        rng = np.random.default_rng(1)
        n = 120
        x = rng.standard_normal(n)
        y = 0.6 * x + rng.standard_normal(n) * 0.8
        c = x ** 2 + y ** 2
        sc = ax.scatter(x, y, c=c, cmap='viridis', s=15, linewidths=0)
        cb = plt.colorbar(sc, ax=ax, pad=0.02, shrink=0.85)
        cb.set_label('r²', fontsize=7)
        cb.ax.tick_params(labelsize=6)
        ax.set_xlabel('x')
        ax.set_ylabel('y')
        ax.set_title('Scatter + colorbar')

    return (draw_B,)


@app.cell
def _(np, spstyle, sptext):
    """C — bar chart with error bars and significance bracket."""
    def draw_C(ax):
        rng = np.random.default_rng(2)
        labels = ['Control', 'Drug A', 'Drug B', 'Drug C']
        means = [1.0, 1.45, 0.75, 1.80]
        sems  = [0.08, 0.13, 0.10, 0.15]
        x = np.arange(len(labels))
        colors = spstyle.get_palette('nature-reviews')
        ax.bar(x, means, yerr=sems, color=colors[:4], capsize=3,
               error_kw={'linewidth': 0.8})
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=30, ha='right', fontsize=7)
        ax.set_ylabel('Response (a.u.)')
        ax.set_ylim(0, 2.5)
        sptext.add_significance_bars(
            ax, pairs=[(0, 3), (1, 3)],
            pvalues=[0.001, 0.04],
            fontsize=7,
        )

    return (draw_C,)


@app.cell
def _(np, plt):
    """D — imshow heatmap (imagesc-style)."""
    def draw_D(ax):
        rng = np.random.default_rng(3)
        # Smooth 2-D field
        raw = rng.standard_normal((30, 30))
        from scipy.ndimage import gaussian_filter
        try:
            data = gaussian_filter(raw, sigma=2)
        except ImportError:
            data = raw  # fallback if scipy absent
        im = ax.imshow(data, cmap='RdBu_r', aspect='auto',
                       interpolation='nearest')
        cb = plt.colorbar(im, ax=ax, pad=0.02, shrink=0.85)
        cb.set_label('Value', fontsize=7)
        cb.ax.tick_params(labelsize=6)
        ax.set_xlabel('Column')
        ax.set_ylabel('Row')
        ax.set_title('Heatmap (imshow)')
        ax.set_xticks([0, 10, 20, 29])
        ax.set_yticks([0, 10, 20, 29])

    return (draw_D,)


@app.cell
def _(create_inset_grid, np, spstyle):
    """E — 2×2 inset subplot grid (tests create_inset_grid)."""
    def draw_E(ax):
        ax.axis('off')
        # Reserve left margin so y-axis labels don't bleed outside the panel
        axs = create_inset_grid(ax, 2, 2, wspace=0.45, hspace=0.55,
                                left=0.12, bottom=0.12,
                                width=0.88, height=0.88)
        rng = np.random.default_rng(4)
        colors = spstyle.get_palette('nature-reviews')
        subtitles = ['Histogram', 'Line', 'Scatter', 'Bar']
        for idx, (r, c) in enumerate([(0, 0), (0, 1), (1, 0), (1, 1)]):
            sub = axs[r, c]
            col = colors[idx]
            if idx == 0:
                sub.hist(rng.exponential(size=80), bins=12, color=col, alpha=0.8)
                sub.set_xlabel('Value', fontsize=6)
                sub.set_ylabel('Count', fontsize=6)
            elif idx == 1:
                t = np.linspace(0, 2 * np.pi, 100)
                sub.plot(t, np.sin(t), color=col)
                sub.set_xlabel('t', fontsize=6)
            elif idx == 2:
                sub.scatter(rng.standard_normal(40), rng.standard_normal(40),
                            s=8, color=col, linewidths=0)
                sub.set_xlabel('x', fontsize=6)
                sub.set_ylabel('y', fontsize=6)
            else:
                # ax.inset_axes() is incompatible with matplotlib's categorical
                # unit system, so use numeric positions + manual xticklabels.
                cats = ['A', 'B', 'C']
                x_pos = np.arange(len(cats))
                sub.bar(x_pos, rng.uniform(0.3, 1.0, 3), color=colors[idx:idx+3])
                sub.set_xticks(x_pos)
                sub.set_xticklabels(cats, fontsize=5)
                sub.set_xlabel('Group', fontsize=6)
            sub.set_title(subtitles[idx], fontsize=7)
            sub.tick_params(labelsize=5)

    return (draw_E,)


@app.cell
def _(mpatches, np, spstyle):
    """F — matplotlib patches/shapes (Rectangle, Circle, Ellipse, Arrow)."""
    def draw_F(ax):
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 10)
        ax.set_aspect('equal')
        colors = spstyle.get_palette('nature-reviews')

        ax.add_patch(mpatches.Rectangle(
            (0.5, 6.5), 3.0, 3.0, facecolor=colors[0], alpha=0.75, linewidth=0))
        ax.add_patch(mpatches.Circle(
            (7.5, 8.0), 1.6, facecolor=colors[1], alpha=0.75, linewidth=0))
        ax.add_patch(mpatches.Ellipse(
            (5.0, 3.5), 4.5, 2.5, angle=20,
            facecolor=colors[2], alpha=0.75, linewidth=0))
        ax.add_patch(mpatches.FancyArrowPatch(
            (1.0, 1.0), (9.0, 5.5),
            arrowstyle='->', mutation_scale=18,
            color=colors[3], linewidth=1.5))

        # Annotate shapes
        ax.text(2.0, 9.5, 'Rectangle', ha='center', fontsize=7)
        ax.text(7.5, 9.9, 'Circle', ha='center', fontsize=7)
        ax.text(5.0, 3.5, 'Ellipse', ha='center', fontsize=7, color='white')

        ax.set_xlabel('x')
        ax.set_ylabel('y')
        ax.set_title('Shapes & patches')

        # Add a second y-axis to test twin-axis rendering
        ax2 = ax.twinx()
        x = np.linspace(0, 10, 100)
        ax2.plot(x, np.sin(x) * 0.5 + 5, color=colors[4],
                 linestyle='--', linewidth=1, alpha=0.6)
        ax2.set_ylabel('sin overlay', fontsize=7)
        ax2.tick_params(labelsize=6)

    return (draw_F,)


@app.cell
def _(os, plt):
    """SVG insert — requires cairosvg; shows a placeholder if missing."""
    import io
    import tempfile

    def draw_G(ax):
        # Generate a simple SVG using matplotlib's SVG backend
        svg_fig, svg_ax = plt.subplots(figsize=(2, 2))
        svg_ax.plot([0, 1, 2], [0, 1, 0], 'o-', color='steelblue', linewidth=2)
        svg_ax.set_title('Embedded SVG', fontsize=9)
        svg_ax.spines[['top', 'right']].set_visible(False)

        buf = io.BytesIO()
        svg_fig.savefig(buf, format='svg', bbox_inches='tight')
        plt.close(svg_fig)
        buf.seek(0)
        svg_bytes = buf.read()

        # Write SVG to a temp file and try to load it via render_svg
        tmp = tempfile.NamedTemporaryFile(suffix='.svg', delete=False)
        tmp.write(svg_bytes)
        tmp.close()

        try:
            from sciplotlib.compose import render_svg
            img = render_svg(tmp.name, scale=3)
            ax.imshow(img)
            ax.set_title('SVG → raster (via cairosvg)')
        except ImportError:
            # cairosvg not installed: show SVG as raw text note
            ax.text(0.5, 0.5,
                    'cairosvg not installed\n(SVG insert not available)',
                    ha='center', va='center', transform=ax.transAxes,
                    fontsize=8, color='gray')
            ax.set_facecolor('#f8f8f8')
            ax.set_title('SVG insert (skipped)')
        finally:
            os.unlink(tmp.name)

        ax.set_xticks([])
        ax.set_yticks([])

    return (draw_G,)


@app.cell
def _(composer, draw_A, draw_B, draw_C, draw_D, draw_E, draw_F, draw_G):
    # Bottom row: E takes the left 13 cols, F takes the middle 4, G takes the right 3.
    # Row 18–27 (rowspan=10), total cols=20.
    (composer
        .add_panel('A', row=0,  col=0,  rowspan=8,  colspan=10, plot_func=draw_A)
        .add_panel('B', row=0,  col=10, rowspan=8,  colspan=10, plot_func=draw_B)
        .add_panel('C', row=9,  col=0,  rowspan=8,  colspan=10, plot_func=draw_C)
        .add_panel('D', row=9,  col=10, rowspan=8,  colspan=10, plot_func=draw_D)
        .add_panel('E', row=18, col=0,  rowspan=10, colspan=10, plot_func=draw_E)
        .add_panel('F', row=18, col=10, rowspan=5,  colspan=10, plot_func=draw_F)
        .add_panel('G', row=23, col=10, rowspan=5,  colspan=10, plot_func=draw_G)
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ---
    ## Individual panel previews

    Each cell below calls `composer.preview(label)` which creates a figure at the
    **exact physical size** the panel occupies in the final composed figure.
    The plot function is then called on that axes.

    **What to check:** Does the preview look like what you'd expect?  Are
    proportions correct?  Do labels/colorbars clip at the edges?
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ### Panel A — line + fill_between
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    _fig_A, _ax_A = composer.preview('A')
    draw_A(_ax_A)
    mo.md(f"**Preview size:** {_fig_A.get_size_inches()[0]:.2f} × {_fig_A.get_size_inches()[1]:.2f} in")
    """)
    return


@app.cell
def _(composer, draw_A):
    _fig_A_preview, _ax_A_preview = composer.preview('A')
    draw_A(_ax_A_preview)
    _fig_A_preview
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ### Panel B — scatter + colorbar
    """)
    return


@app.cell
def _(composer, draw_B, mo):
    _fig_B, _ax_B = composer.preview('B')
    draw_B(_ax_B)
    mo.md(f"**Preview size:** {_fig_B.get_size_inches()[0]:.2f} × {_fig_B.get_size_inches()[1]:.2f} in")
    return


@app.cell
def _(composer, draw_B):
    _fig_B_preview, _ax_B_preview = composer.preview('B')
    draw_B(_ax_B_preview)
    _fig_B_preview
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ### Panel C — bar chart + error bars + significance
    """)
    return


@app.cell
def _(composer, draw_C, mo):
    _fig_C, _ax_C = composer.preview('C')
    draw_C(_ax_C)
    mo.md(f"**Preview size:** {_fig_C.get_size_inches()[0]:.2f} × {_fig_C.get_size_inches()[1]:.2f} in")
    return


@app.cell
def _(composer, draw_C):
    _fig_C_preview, _ax_C_preview = composer.preview('C')
    draw_C(_ax_C_preview)
    _fig_C_preview
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ### Panel D — imshow heatmap
    """)
    return


@app.cell
def _(composer, draw_D, mo):
    _fig_D, _ax_D = composer.preview('D')
    draw_D(_ax_D)
    mo.md(f"**Preview size:** {_fig_D.get_size_inches()[0]:.2f} × {_fig_D.get_size_inches()[1]:.2f} in")
    return


@app.cell
def _(composer, draw_D):
    _fig_D_preview, _ax_D_preview = composer.preview('D')
    draw_D(_ax_D_preview)
    _fig_D_preview
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ### Panel E — 2×2 inset subplot grid
    """)
    return


@app.cell
def _(composer, draw_E, mo):
    _fig_E, _ax_E = composer.preview('E')
    draw_E(_ax_E)
    mo.md(f"**Preview size:** {_fig_E.get_size_inches()[0]:.2f} × {_fig_E.get_size_inches()[1]:.2f} in")
    return


@app.cell
def _(composer, draw_E):
    _fig_E_preview, _ax_E_preview = composer.preview('E')
    draw_E(_ax_E_preview)
    _fig_E_preview
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ### Panel F — shapes and patches (+ twin y-axis)
    """)
    return


@app.cell
def _(composer, draw_F, mo):
    _fig_F, _ax_F = composer.preview('F')
    draw_F(_ax_F)
    mo.md(f"**Preview size:** {_fig_F.get_size_inches()[0]:.2f} × {_fig_F.get_size_inches()[1]:.2f} in")
    return


@app.cell
def _(composer, draw_F):
    _fig_F_preview, _ax_F_preview = composer.preview('F')
    draw_F(_ax_F_preview)
    _fig_F_preview
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ### Panel G — SVG insert (cairosvg required)
    """)
    return


@app.cell
def _(composer, draw_G, mo):
    _fig_G, _ax_G = composer.preview('G')
    draw_G(_ax_G)
    mo.md(f"**Preview size:** {_fig_G.get_size_inches()[0]:.2f} × {_fig_G.get_size_inches()[1]:.2f} in")
    return


@app.cell
def _(composer, draw_G):
    _fig_G_preview, _ax_G_preview = composer.preview('G')
    draw_G(_ax_G_preview)
    _fig_G_preview
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ---
    ## `preview_image()` — marimo HTML output

    Two variants are shown side-by-side for each panel:

    - **plain** (`normalize=False`, default) — standalone figure at the correct
      physical size, no layout fitting applied.
    - **normalised** (`normalize=True`) — composes the full figure, runs
      `normalize_fonts` + `fit_axes_to_cells` + `normalize_spines`, then crops
      to the panel's GridSpec cell.  Should match the PDF exactly.
    """)
    return


@app.cell
def _(mo):
    mo.md("""
    **Panel A** — plain vs normalised `preview_image`
    """)
    return


@app.cell
def _(composer, draw_A, mo):
    mo.hstack([
        composer.preview_image('A', plot_func=draw_A, normalize=False),
        composer.preview_image('A', normalize=True),
    ])
    return


@app.cell
def _(mo):
    mo.md("""
    **Panel B** (scatter + colorbar) — plain vs normalised `preview_image`
    """)
    return


@app.cell
def _(composer, draw_B, mo):
    mo.hstack([
        composer.preview_image('B', plot_func=draw_B, normalize=False),
        composer.preview_image('B', normalize=True),
    ])
    return


@app.cell
def _(composer):
    composer.preview_image('B', normalize=True)
    return


@app.cell
def _(composer):
    composer.preview_image('D', normalize=True)
    return


@app.cell
def _(mo):
    mo.md("""
    **Panel E** (inset grid) — plain vs normalised `preview_image`
    """)
    return


@app.cell
def _(composer, draw_E, mo):
    mo.hstack([
        composer.preview_image('E', plot_func=draw_E, normalize=False),
        composer.preview_image('E', normalize=True),
    ])
    return


@app.cell
def _(composer):
    composer.preview_image('E', normalize=True)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ---
    ## Full composed figure

    `composer.compose()` assembles all panels into a single figure.
    `composer.to_image()` then normalises fonts and spine widths, fits axes
    to their gridspec cells, and returns a `mo.image(...)`.

    **What to check:**
    - Panels are in the right positions
    - Fonts and spine widths are uniform across panels
    - No panel content spills into a neighbour
    - The overall aspect ratio matches the declared `width_cm × height_cm`
    """)
    return


@app.cell
def _(composer):
    _fig_full, _axes_full = composer.compose()
    _fig_full
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ### `to_image()` output (normalised fonts + spines)
    """)
    return


@app.cell
def _(composer):
    # Re-compose so to_image() has a fresh figure to work with
    composer.compose()
    composer.to_image()
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ### Save to PDF

    `composer.save()` applies the same normalisation as `to_image()`, so the
    PDF should match the image above.
    """)
    return


@app.cell
def _(composer, os):
    # to_image() above closed the figure, so we need a fresh compose().
    _out_path = os.path.join('..', 'outputs', 'preview_test')
    os.makedirs(os.path.join('..', 'outputs'), exist_ok=True)
    composer.compose()
    composer.save(_out_path, formats=('pdf',))
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ---
    ## Panel physical sizes

    `panel_figsize(label)` returns the exact (width, height) in inches that
    each panel occupies in the composed figure.  Use this to sanity-check
    that panels are sized as expected.
    """)
    return


@app.cell
def _(composer, mo):
    _rows = []
    for _label in ['A', 'B', 'C', 'D', 'E', 'F', 'G']:
        _w, _h = composer.panel_figsize(_label)
        _rows.append({'Panel': _label,
                      'Width (in)': f'{_w:.3f}',
                      'Height (in)': f'{_h:.3f}',
                      'Aspect (w/h)': f'{_w/_h:.2f}'})
    mo.ui.table(_rows)
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
