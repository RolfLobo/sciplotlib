# sciplotlib — LLM reference

sciplotlib is a Python library for composing publication-quality multi-panel figures with matplotlib. The core API is `FigureComposer` in `sciplotlib.compose`. Supporting utilities live in `sciplotlib.text`, `sciplotlib.style`, and `sciplotlib.polish`.

## Imports

```python
import sciplotlib.compose as splcompose   # FigureComposer
import sciplotlib.text   as spltext       # add_significance_bars, pval_to_stars
import sciplotlib.style  as splstyle      # get_style, get_palette, style_axes
import sciplotlib.polish as splpolish     # set_bounds, apply_gradient
```

## FigureComposer — full workflow

```python
composer = splcompose.FigureComposer(
    width_cm=18, height_cm=12,
    grid_rows=20, grid_cols=40,       # virtual grid; panels snap to cells
    dpi=600,
    stylesheet='mp-paper',            # mplstyle name (see Stylesheets)
    font_size=6.0,
    axis_label_font_size=6.0,
    title_font_size=6.0,
    label_font_size=14,               # panel letter size (a, b, c …)
    label_weight='bold',
    label_y=0.001,                    # vertical offset of panel letter
    spine_linewidth=0.7,
    tick_linewidth=0.7,
    tick_length=2.5,
    tick_pad=1.0,
    axis_label_pad=2.0,
    line_linewidth=1.0,               # normalises all Line2D widths
    wspace=0.4, hspace=1.5,
    margins={'left': 0.02, 'right': 0.98, 'bottom': 0.05, 'top': 0.96},
)
composer.apply_style()   # load stylesheet globally so panel cells inherit it
```

### add_panel

```python
composer.add_panel(
    label,          # str — single letter used as dict key and panel letter
    row, col,       # top-left grid cell (0-indexed)
    rowspan, colspan,
    file=None,      # optional path to .pkl / .png / .jpg / .svg
    no_axis=False,  # True → no axes created (image-only panel)
    axes_pad=None,  # dict with 'left','right','top','bottom' in fig fraction
    plot_func=None, # callable(ax) used by preview_image
)
```

Panels are positioned on a virtual grid. `rowspan`/`colspan` determine physical size proportionally.

### compose + plot

```python
fig, axes = composer.compose(wspace=None, hspace=None)
# axes is a dict keyed by label string

plot_panel_a(axes['a'])
plot_panel_b(axes['b'])
```

### Normalisation (call order matters)

```python
composer.normalize_fonts()       # sets all text to composer font sizes
composer.fit_axes_to_cells()     # shrinks axes so ticks/labels don't overlap adjacent panels
composer.normalize_spines()      # sets spine linewidths; NEVER clip spines — see Gotchas
composer.normalize_linewidths()  # sets Line2D widths to line_linewidth
```

`composer.to_image()` calls all four and returns a marimo-renderable PIL image.  
`composer.save(path)` calls the first three, then saves.

### Preview (per-panel, in marimo)

```python
# bottom of each panel cell:
_img = composer.preview_image('b', plot_func=plot_panel_b, normalize=True)
_img   # marimo displays it inline
```

`normalize=True` (default) applies all normalisation steps so the preview matches the final figure exactly.

### Save

```python
composer.save(
    'reports/figures/figure-4',
    formats=('pdf', 'svg', 'png'),   # any subset
    dpi=600,
    transparent=True,
)
```

### Stats report

```python
# in each panel cell — call after computing statistics:
composer.register_stats('e', [
    {
        'description': 'GLM-HMM 3-state vs LR log-likelihood',
        'test': 'Paired t-test (two-sided)',
        'statistic': -13.37, 'p_value': 9.67e-12, 'n': 22,
        'note': '3-state GLM-HMM outperforms LR',
    },
])
composer.register_stats('b', None)   # None = "no statistical tests apply"
# omitting register_stats → reported as "stats not yet registered"

# in the save cell:
composer.save_stats_report(
    'reports/figures/figure-4-stats',  # writes .md and .pdf
    title='Figure 4',
)
```

PDF backend priority: **weasyprint** (install `sciplotlib[stats-pdf]`) → **pandoc** → **matplotlib fallback** (always available).

Stat entry keys (all optional): `description`, `test`, `statistic`, `p_value`, `n`, `effect_size`, `ci`, `note`.

---

## Marimo integration

### Recommended cell structure

```
imports cell        →  mo, plt, np, splcompose, …
composer cell       →  FigureComposer() + add_panel calls + apply_style()
data loaders cell   →  @lru_cache functions — def _(): with NO inputs
panel a cell        →  define plot_panel_a, register_stats('a', …), preview_image
panel b cell        →  define plot_panel_b, register_stats('b', None), preview_image
…
compose cell        →  composer.compose() + all plot_panel_* calls + to_image()
save cell           →  composer.save(…) + composer.save_stats_report(…)
```

### Data loader pattern (prevents re-running on every upstream change)

```python
# data loaders cell — def _():   ← no inputs from other cells
import functools

@functools.lru_cache(maxsize=None)
def load_mouse_data():
    import matchingp.dataset as _mp   # all imports INSIDE the function
    return _mp.load_data(...)

return load_mouse_data   # export the function, not the data
```

### Inset axes inside a panel

Use `ax.inset_axes([x0, y0, w, h])` (all in parent-axes fraction) instead of `plt.subplots`. Inset axes are exempt from GridSpec layout, so they never interfere with `fit_axes_to_cells`. Never call `fig.subplots_adjust` inside a panel function — it corrupts the GridSpec.

### Axis-off panels (schematics)

```python
ax.axis('off')   # fit_axes_to_cells automatically skips this panel
```

To add inset axes with their own ticks inside an off panel, use `ax.inset_axes(...)` and only call `axis('off')` on the parent.

---

## add_significance_bars

```python
from sciplotlib.text import add_significance_bars

add_significance_bars(
    ax,
    pairs=[(3, 6), (3, 7)],   # x-positions in data coords
    pvalues=[p1, p2],          # converted to stars automatically
    # OR: labels=['***', 'n.s.'],  explicit text overrides pvalues
    pad=None,          # gap above data, default 6% of y-range
    tick_height=None,  # end-tick length, default 30% of pad
    linewidth=0.7,
    fontsize=5,
    show_ns=True,      # set False to skip non-significant pairs
    expand_ylim=True,  # auto-expand ylim to fit brackets
)
```

Brackets are stacked automatically (narrowest span placed lowest). Star thresholds: `*` p<0.05, `**` p<0.01, `***` p<0.001, `****` p<0.0001.

---

## Stylesheets

Available names for `FigureComposer(stylesheet=...)` and `splstyle.get_style(...)`:

| Name | Description |
|------|-------------|
| `nature-reviews` | Nature Publishing Group style |
| `nature` | Minimal Nature style |
| `mp-paper` | matching pennies paper style |
| `modern` | Clean sans-serif |
| `economist` | Economist magazine style |
| `dark` | Dark background |
| `default` | sciplotlib default |

```python
# Apply to a single axes post-hoc:
splstyle.style_axes(ax, style='nature-reviews', font_size=8)

# Apply via context manager:
with plt.style.context(splstyle.get_style('nature-reviews')):
    fig, ax = plt.subplots()
    ...
```

---

## Other utilities

```python
# Clip axes to data range (ticks define axis extent):
splpolish.set_bounds(fig, ax)

# Color palettes:
colors = splstyle.get_palette('nature-reviews', output_type='hex')  # list of hex strings

# Convert p-value to stars:
from sciplotlib.text import pval_to_stars
pval_to_stars(0.003)   # → '**'

# Save figure (legacy, prefer composer.save):
import sciplotlib.util as splutil
splutil.savefig(fig, 'path/to/figure', dpi=300, fig_exts=['.png', '.svg'])
```

---

## Gotchas

**Never clip Spine objects.** Spines sit exactly on the axes boundary, so clipping halves their visible stroke width. Remove any `spine.set_clip_on(True)` calls.

**`fit_axes_to_cells` grouping.** Panels are aligned by `(row_start, row_end)` pairs, not just `row_start`. Panels that share a start row but have different rowspans are in different alignment groups — this is intentional.

**`subplots_adjust` corrupts GridSpec.** Never call `fig.subplots_adjust` or `plt.tight_layout` inside a panel function. These affect the top-level GridSpec and misalign all other panels.

**Inset axes bounds are in axes-fraction coordinates.** They don't move when you change `xlim`/`ylim`. Recompute bounds analytically if you change the data limits after placing insets: `y0_frac = (y_data - ylim_min) / (ylim_max - ylim_min)`.

**marimo `_`-prefix variables are cell-private.** Functions or variables named `_foo` cannot be returned from a marimo cell and are not visible to other cells. Don't prefix exported names with `_`.

**`axes_pad={}` sentinel.** Pass `axes_pad={}` (empty dict, not `None`) to `add_panel` to explicitly opt out of `fit_axes_to_cells` for one panel while keeping the default for others.
