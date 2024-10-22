"""
Author(s): Pavel Krobot <Pavel.Krobot@cesnet.cz>

Copyright: (C) 2024 CESNET, z.s.p.o.

Charts creation for profilers data.

This module takes measured data and charts specifications and creates
an interactive html charts page. To create charts using this module,
just:
1) define a list of specifications using SubPlotSpecs class,
2) call create_charts_html on your data and defined specifications.
"""

from dataclasses import dataclass
from enum import Enum

import pandas
from plotly import graph_objects, subplots


class ChartType(Enum):
    LINE = 1
    BAR = 2


class TracesTagMode(Enum):
    """Enumeration for tag traces mode.

    When other mode than "NO" is used, trace names are tagged based
    on selected mode (affects legend and traces hovering). This can be
    useful for faster orientation within a chart.
    """

    """Add no tag to traces names."""
    NO = 0
    """Tag traces with zero values ("TRACE_NAME (0)". Non-zero traces
    left are unchanged."""
    ZERO = 1
    """Tag all traces with <min, max> tags ("TRACE_NAME <min, max>") or
    with <min> if min and max are equal ("TRACE_NAME <min>")."""
    MINMAX = 2


@dataclass
class SubPlotSpec:
    """Specification of single sub-plot.

    Attributes
    ----------
    title : str
        Title of the sub-plot.
    y_label : str
        Label of y axis.
    columns : list[str]
        Name of counters (i.e. columns) to use in the sub-plot.
    col_names : list[str], optional
        Alternative column names which will be used in a legend.
        If not set, original column names will be used
    chart_type : ChartType, optional
        Type of the chart.
    x_col : str, optional
        Name of x axis column.
    x_label : str, optional
        Label of x axis.
    x_ticks : list, optional
        List of x axis ticks.
    y_ticks : list, optional
        List of y axis ticks.
    """

    title: str
    y_label: str
    columns: list[str]
    col_names: list[str] = None
    chart_type: ChartType = ChartType.LINE
    x_col: str = "timestamp"
    x_label: str = "time [s]"
    x_ticks: list[float] = None
    y_ticks: list[float] = None

    def __post_init__(self):
        _CHART_TYPES = {
            ChartType.LINE: {
                "class": graph_objects.Scatter,
                "common_args": {"mode": "markers+lines"},
            },
            ChartType.BAR: {
                "class": graph_objects.Bar,
                "common_args": {},
            },
        }

        if not self.col_names:
            self.col_names = self.columns

        self.chart_class = _CHART_TYPES[self.chart_type]["class"]
        self.common_args = _CHART_TYPES[self.chart_type]["common_args"]


def _format_number(n: int | float) -> str:
    if len(str(n)) >= 5:
        return f"{n:.0e}"
    return str(n)


def _tag_min_max(df: pandas.DataFrame, col: str, col_name: str) -> str:
    c_min = df[col].min()
    c_max = df[col].max()
    if c_min == c_max:
        return f"{col_name} <{_format_number(c_min)}>"
    else:
        return f"{col_name} <{_format_number(c_min)}, {_format_number(c_max)}>"


def _tag_zero(df: pandas.DataFrame, col: str, col_name: str) -> str:
    if (df[col] == 0).all():
        return f"{col_name} (0)"
    else:
        return col_name


def _tag_traces(df: pandas.DataFrame, spec: SubPlotSpec, mode: TracesTagMode):
    if mode == TracesTagMode.NO:
        return
    elif mode == TracesTagMode.ZERO:
        tagger = _tag_zero
    elif mode == TracesTagMode.MINMAX:
        tagger = _tag_min_max

    new_col_names = []
    for c, c_name in zip(spec.columns, spec.col_names):
        new_col_names.append(tagger(df, c, c_name))

    spec.col_names = new_col_names


def create_charts_html(
    data: pandas.DataFrame,
    subplot_specs: SubPlotSpec | list[SubPlotSpec],
    path: str,
    title: str = "",
    vertical_spacing: float = 0.07,
    height: int = 600,
    markers: list[float] = None,
    barmode: str = "group",
    tag_traces: TracesTagMode = TracesTagMode.ZERO,
) -> graph_objects.Figure:
    """Create an interactive html page with charts.

    Parameters
    ----------
    data : pandas.DataFrame
        DataFrame with source data.
    subplot_specs : SubPlotSpec | list[SubPlotSpec]
        Sub-plots specifications.
    path : str
        Path to where resulting html page file should be stored.
    title : str, optional
        Page title.
    vertical_spacing : float, optional
        Value of sub-plots vertical spacing. For more information see
        documentation of plotly.subplots.make_subplots. Value is between
        0 and 1.
    height : int, optional
        Total subplot height in pixels.
    markers : list[float], optional
        List of points on x-axis where vertical lines (i.e. markers)
        should be drawn.
    barmode : str, optional
        Bar chart mode option propagated to "update_layout" method.
        The most common values are "group" and "stacked".
    tag_traces : TracesTagMode, optional
        Traces tag mode. If set to TracesTagMode.NO, traces names are
        left unchanged. Otherwise, all traces names are tagged based on
        selected mode.

    Returns
    -------
    plotly.graph_objects.Figure
        Created figure object for optional further processing.
    """

    if isinstance(subplot_specs, SubPlotSpec):
        subplot_specs = [subplot_specs]

    rows = len(subplot_specs)

    subplot_height = (1 - (rows - 1) * vertical_spacing) / rows

    fig = subplots.make_subplots(
        rows=rows,
        vertical_spacing=vertical_spacing,
        subplot_titles=[s.title for s in subplot_specs],
    )

    for row, spec in enumerate(subplot_specs, start=1):
        _tag_traces(data, spec, tag_traces)
        traces = []
        for c, c_name in zip(spec.columns, spec.col_names):
            traces.append(
                spec.chart_class(
                    name=c_name,
                    x=data[spec.x_col],
                    y=data[c],
                    showlegend=True,
                    **spec.common_args,
                )
            )
        fig.add_traces(traces, rows=row, cols=1)

        legend_name = f"legend{row}"
        fig.update_traces(row=row, col=1, legend=legend_name)
        y = 1 - ((row - 1) * (subplot_height + vertical_spacing))
        fig.update_layout(
            {
                legend_name: dict(y=y, yanchor="top"),
                f"xaxis{row}_title": spec.x_label,
                f"yaxis{row}_title": subplot_specs[row - 1].y_label,
            }
        )
        if spec.x_ticks:
            fig.update_layout({f"xaxis{row}": {"tickmode": "array", "tickvals": spec.x_ticks}})
        if spec.y_ticks:
            fig.update_layout({f"yaxis{row}": {"tickmode": "array", "tickvals": spec.y_ticks}})

    if markers:
        for m in markers:
            fig.add_vline(
                x=m,
                line_dash="dash",
                line_color="black",
                opacity=0.3,
                annotation=dict(
                    text=f"{m}s",
                    font=dict(color="white"),
                    bgcolor="grey",
                    hovertext=f"mark: {m}s",
                ),
                annotation_position="top",
            )

    fig.update_layout(
        height=height * rows,
        title_text=title,
        barmode=barmode,
        hoverlabel_namelength=-1,
    )

    fig.write_html(path)

    return fig
