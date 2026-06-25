import sciplotlib as spl
import os
import matplotlib as mpl
from collections import OrderedDict
import struct

def get_style(stylesheet_name='nature'):
    """
    Function to get stylesheet to be used to apply a style to matplotlib plots.

    Example:
    >> import matplotlib.pyplot as plt
    >> from sciplotlib import style as spstyle
    >> nature_style = spstyle.get_style('nature')
    >> with plt.style.context(nature_style):
    >>      plt.plot([1, 2, 3, 4, 5])

    Parameters
    ----------
    stylesheet_name : (str)
        name of stylesheet to get

    Returns
    -------
    stylesheet_path : (str)
        path of stylesheet
    """

    package_dir = spl.__path__[0]
    dirname = os.path.join(package_dir, 'stylesheets')
    stylesheet_path = os.path.join(dirname, stylesheet_name + '.mplstyle')

    return stylesheet_path


def use_sans_maths(return_type='permenant', fig=None, ax=None, verbose=False):
    """
    Uses LaTeX computer modern *SANS* mathematics font.
    Note that you can reset using: plt.rcdefaults()

    Parameters
    ----------
    return_type : (str)
    fig : (matplotlib fig object)
    ax : (matplotlib ax object)
    verbose : (bool)
    """

    if return_type is 'temp_dict' and (fig is None):
        # usage is with mpl.rc_context(use_sans_maths())
        # note that there is currenlty an issue with matplotli that prevents this from working without
        # calling plt.show() or fig.savefig()
        # see: https://github.com/matplotlib/matplotlib/issues/13431
        if verbose:
            print("""Note you must use plt.show() so that the plot will render properly. 
                    You can turn off this warning by setting verbose=False.""")
        rc_param_dict = {'text.usetex': True,
                         'text.latex.preamble': [r'\usepackage[cm]{sfmath}'],
                         'font.family': 'sans-serif',
                         'font.sans-serif': 'cm',
                         'text.latex.preamble': [
                             r'\usepackage{siunitx}',
                             r'\sisetup{detect-all}',
                             r'\usepackage{sansmath}',
                             r'\sansmath'
                         ]}

        return OrderedDict(rc_param_dict.items())

    elif return_type is 'permenant':
        mpl.rcParams['text.usetex'] = True
        mpl.rcParams['text.latex.preamble'] = [r'\usepackage[cm]{sfmath}']
        mpl.rcParams['font.family'] = 'sans-serif'
        mpl.rcParams['font.sans-serif'] = 'cm'
        mpl.rcParams['text.latex.preamble'] = [
            r'\usepackage{siunitx}',  # i need upright \micro symbols, but you need...
            r'\sisetup{detect-all}',  # ...this to force siunitx to actually use your fonts
            r'\usepackage{sansmath}',  # load up the sansmath so that math -> helvet
            r'\sansmath'  # <- tricky! -- gotta actually tell tex to use!
        ]

    if (fig is not None) and (ax is not None):
        # TODO: see if there is a way to redraw (fig.canvas.draw()?) to circumvent the context manager
        fig = fig
        ax = ax

        return fig, ax

def get_palette(name='nature-reviews', output_type='hex'):
    """
    Gets the list of colors for a particular color scheme.
    Some colorschemes are obtained from the ggsci project in R:
    https://cran.r-project.org/web/packages/ggsci/vignettes/

    Some good resources on color palettes:
    https://jiffyclub.github.io/palettable/
    https://blog.graphiq.com/finding-the-right-color-palettes-for-data-visualizations-fcd4e707a283

    TODO: add support for D3JS color palette
    https://github.com/d3/d3-scale-chromatic
    Actually I think this is the same as the matplotlib default.

    More related to art than data visualisation:
    https://artsexperiments.withgoogle.com/artpalette/colors/

    Parameters
    ----------
    name : (str)
        name of the color scheme you want to get
    output_type : (str)
        way in which the color is specified: hex or RGB

    Returns
    -------

    """

    supported_colorschemes = ['nature-reviews', 'nature', 'economist', 'aaas',
                              'mondrian', 'kanagawa']

    if (name == 'nature-reviews') or (name == 'nature'):
        colors = ['#E64B35', '#4DBBD5', '#00A087', '#3C5488',
                  '#F39B7F', '#8491B4', '#91D1C2FF', '#DC0000',
                  '#7E6148', '#B09C85']
    elif name == 'economist':
        colors = ['#6794a7', '#014d64', '#7ad2f6', '#01a2d9',
                  '#7bc0c1', '#00887d', '#91D1C2FF', '#DC0000',
                  '#7E6148', '#B09C85']
    elif name == 'aaas':
        colors = ['#3B4992FF', '#EE0000FF', '#008B45FF',
                  '#631879FF', '#008280FF', '#BB0021FF',
                  '#5F559BFF', '#A20056FF', '#808180FF',
                  '#1B1919FF']
    elif name == 'mondrian':
        # based on the wikipedia image of
        # Composition with Red Blue and Yello
        colors = ["#DD271C", '#015A9C', '#EBDC75', '#071C13', '#E5E3E4']
    elif name == 'kanagawa':
        # based on the Great Wave of Kanagawa
        # Source: http://sierrakellermeyer.com/blog/10-color-palettes-based-on-famous-paintings
        colors = ['#7E9CA7', '#C1B9A9', '#DED4C5', "#07244b",
                  "#45494D"]
    else:
        print('No valid color scheme specified, returning none')
        print('The supported color schemes are ' + supported_colorschemes)
        colors = None

    if output_type == 'rgb':
        # remove the '#', then convert to RGB
        colors = [struct.unpack('BBB', color[1:].decode('hex')) for color in colors]

    return colors


def style_axes(ax, style='nature-reviews', font_size=None,
               axis_label_font_size=None, tick_font_size=None,
               title_font_size=None, spine_linewidth=None,
               tick_linewidth=None, tick_length=None):
    """Apply a named sciplotlib stylesheet to an existing axes in-place.

    Useful for making exploratory plots paper-ready without rebuilding them
    from scratch.  Applies spine visibility, linewidths, tick parameters,
    font sizes, facecolor, and color cycle from the named stylesheet.
    Override any individual parameter to fine-tune after applying the base
    style.

    Parameters
    ----------
    ax : matplotlib.axes.Axes
        The axes to style.
    style : str
        Name of a sciplotlib stylesheet (e.g. 'nature-reviews', 'nature',
        'modern', 'economist', 'mp-paper').
    font_size : float, optional
        Base font size for tick labels and free text. Defaults to the
        stylesheet's ``font.size``.
    axis_label_font_size : float, optional
        Font size for x/y axis labels. Defaults to the stylesheet's
        ``axes.labelsize``.
    tick_font_size : float, optional
        Font size for tick labels. Defaults to ``font_size`` if given,
        otherwise the stylesheet's ``xtick.labelsize``.
    title_font_size : float, optional
        Font size for the axes title. Defaults to the stylesheet's
        ``axes.titlesize``.
    spine_linewidth : float, optional
        Linewidth for all four spines. Defaults to ``axes.linewidth``.
    tick_linewidth : float, optional
        Linewidth for tick marks. Defaults to ``spine_linewidth``.
    tick_length : float, optional
        Length of major tick marks in points. Defaults to
        ``xtick.major.size`` from the stylesheet.

    Returns
    -------
    ax : matplotlib.axes.Axes
        The same axes object, modified in-place.

    Examples
    --------
    Apply nature-reviews style to an axes you already have:

    >>> fig, ax = plt.subplots()
    >>> ax.scatter(x, y)
    >>> from sciplotlib import style as spstyle
    >>> spstyle.style_axes(ax, 'nature-reviews', font_size=9)
    """
    import matplotlib as mpl

    style_path = get_style(style)
    with mpl.rc_context():
        mpl.style.use(style_path)
        rc = dict(mpl.rcParams)

    # --- Spine visibility ---
    for name in ('top', 'right', 'left', 'bottom'):
        ax.spines[name].set_visible(rc.get(f'axes.spines.{name}', True))

    # --- Spine linewidth ---
    lw = spine_linewidth if spine_linewidth is not None else rc.get('axes.linewidth', 0.8)
    for spine in ax.spines.values():
        spine.set_linewidth(lw)

    # --- Background ---
    ax.set_facecolor(rc.get('axes.facecolor', 'white'))

    # --- Font sizes ---
    base_font = font_size if font_size is not None else rc.get('font.size', 10)
    label_sz = axis_label_font_size if axis_label_font_size is not None else rc.get('axes.labelsize', base_font)
    tick_sz = tick_font_size if tick_font_size is not None else rc.get('xtick.labelsize', base_font)
    title_sz = title_font_size if title_font_size is not None else rc.get('axes.titlesize', base_font)

    ax.xaxis.label.set_fontsize(label_sz)
    ax.yaxis.label.set_fontsize(label_sz)
    ax.title.set_fontsize(title_sz)

    # --- Tick parameters ---
    tick_lw = tick_linewidth if tick_linewidth is not None else lw
    tick_len = tick_length if tick_length is not None else rc.get('xtick.major.size', 3.5)
    tick_dir = rc.get('xtick.direction', 'out')

    ax.tick_params(
        axis='both', which='major',
        labelsize=tick_sz,
        width=tick_lw,
        length=tick_len,
        direction=tick_dir,
    )

    # --- Color cycle ---
    prop_cycle = rc.get('axes.prop_cycle')
    if prop_cycle is not None:
        ax.set_prop_cycle(prop_cycle)

    return ax