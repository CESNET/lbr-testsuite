"""
Pavel Krobot <Pavel.Krobot@cesnet.cz>

Copyright: (C) 2023 CESNET, z.s.p.o.

Common module for plotting of data stored within a DataTable.
"""

import itertools
from dataclasses import dataclass, field
from typing import List, Union

import matplotlib
import matplotlib.pyplot as plt

from .line_colors import LineColors


@dataclass
class PlotLineSpec:
    """Data class representing specification of single line to plot.

    Parameters
    ----------
    column : str
        Name of a pandas.DataFrame column.
    label_base : str
        Base name of line label. Label-base is used instead of "direct"
        label as this base is extended by line identification when
        combining same kind of lines with different parameters. (e.g.
        measured value for 8 and 16 workers would have same
        base - "measured").
    color_shade : int
        Color shade for lines with same color of different shade.
        Currently only 2 values of shade are available: 0 - darker,
        1 - lighter. If it is not set, no automatic color derivation
        is done and color is set automatically or via line_kwargs.
    line_kwargs : dict
        Additional arguments for pandas.Series.plot method. "label"
        argument is not allowed as it is created automatically from
        label_base.
    """

    column: str
    label_base: str = None
    color_shade: int = None
    line_kwargs: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.label_base:
            self.label_base = self.column

        # fmt: off
        # ...as black really does not work well with asserts
        assert "label" not in self.line_kwargs, "Do not use 'label' directly in line kwargs"
        assert self.color_shade in [None, 0, 1], (
            "Invalid value of color shade. Only 0 and 1 is allowed."
        )
        # fmt: on


@dataclass
class PlotSpec:
    """Data class representing specification of single chart to plot.

    Parameters
    ----------
    lines : list[PlotLineSpec]
        Specification of lines to plot.
    title : str, optional
        Chart title.
    x_column : str, optional
        Name of pandas.DataFrame column which should be used for x axis.
    max_column : PlotLineSpec, optional
        If used, special "max" line is drawn. "Max" column may exists
        more than once in plotted data. However, this max column in most
        cases have same values for all used parametrizations. Using
        this argument "max" line is drawn only once.
    parametrized_by : Union[str, List[str]]
        Name(s) of columns holding values of parameters of group of
        lines with same meaning.
    filter_by : dict
        Dictionary where keys are column names and values are column
        values to filter. Requested chart is plotted on these filtered
        data only.
    xscale : dict, optional
        Scale for x axis. Log2 by default.
    xlabel : str, optional
        Label of x axis.
    ylabel : str, optional
        Label of y axis.
    """

    lines: List[PlotLineSpec]
    title: str = ""
    x_column: str = None
    max_column: PlotLineSpec = None
    parametrized_by: Union[str, List[str]] = None
    filter_by: dict = None
    xscale = dict(value="log", base=2)
    xlabel: str = None
    ylabel: str = None

    def __post_init__(self):
        if isinstance(self.parametrized_by, str):
            self.parametrized_by = [self.parametrized_by]


class DataTableCharts:
    """Class responsible for plotting of tabular data stored within
    a DataTable

    Attributes
    ----------
    _charts : list[list[PlotSpec]]
        List of lists (i.e. 2D-array) of plot specifications. Defines
        charts layout of resulting picture. Every plot specification
        defines one chart which will be placed in resulting figure in
        same location as within this list.
        E.g. [[spec1, spec2], [spec3, spec4]] will result in a figure:
        +----------------------------------+
        |                                  |
        |  +===========+    +===========+  |
        |  |           |    |           |  |
        |  |  CHART 1  |    |  CHART 2  |  |
        |  |           |    |           |  |
        |  +===========+    +===========+  |
        |                                  |
        |  +===========+    +===========+  |
        |  |           |    |           |  |
        |  |  CHART 3  |    |  CHART 4  |  |
        |  |           |    |           |  |
        |  +===========+    +===========+  |
        |                                  |
        +----------------------------------+
        Note: Count of charts in all rows has to be same.

    _data : data_table.DataTable
        Source data for plotting.
    """

    def __init__(self, charts=None):
        self._charts = charts if charts is not None else []
        self._data = None

        self._n_rows = None
        self._n_cols = None

        self._colors = LineColors()

    def set_data(self, data):
        """Set source data"""

        self._data = data

    def append_charts_row(self, charts):
        """Append single charts row to the list of all charts to plot.

        Parameters
        ----------
        charts : list
            List of charts specification (use list even if single chart
            in a row is used).
        """

        self._charts.append(charts)

    def _set_dimensions(self):
        self._n_rows = len(self._charts)
        self._n_cols = len(self._charts[0])

    def _assert_layout_grid(self):
        """Check whether charts layout has same number of columns in all
        rows.
        """

        all_n_cols = [len(x) for x in self._charts]
        c = all_n_cols.count(self._n_cols)

        assert c == self._n_rows, "Layout with various count of charts in rows is not supported."

    def _prepare_layout(self):
        """Prepare figure and axes using matplotlib."""

        self._set_dimensions()

        self._assert_layout_grid()

        fig_width = self._n_cols * 600 / 100
        fig_height = self._n_rows * 500 / 100
        fig, axes = plt.subplots(
            nrows=self._n_rows,
            ncols=self._n_cols,
            figsize=(fig_width, fig_height),
            dpi=300,
        )

        fig.tight_layout(pad=6)

        return (fig, axes)

    @staticmethod
    def _format_ax(ax, spec, data):
        """Common formatting"""

        ax.set_title(spec.title)
        ax.legend(fontsize=6)
        ax.set_xscale(**spec.xscale)
        ax.set_xticks(data[spec.x_column])
        ax.get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
        if spec.xlabel:
            ax.set_xlabel(spec.xlabel)
        if spec.ylabel:
            ax.set_ylabel(spec.ylabel)
        ax.grid(linestyle=":", color="silver")

    def _subframes_by_params(self, data, params):
        """Filter sub-frames per unique values of selected parameters.
        From these sub-frames requested columns will be plotted.
        """

        filters = []
        for par in params:
            flt = []
            for val in data.get_column_unique_values(par):
                flt.append((par, val))
            filters.append(flt)

        sub_frames = []
        for composed_flt in itertools.product(*filters):
            sub_frames.append(data.filter_data(dict(composed_flt)))

        return sub_frames

    @staticmethod
    def _label_suffix(parametrized_by, data):
        """Create line label suffix.

        Suffix is composed from names of all parametrized_by and their current
        values.

        Note: Only first letter of group name is used to keep labels
        short.
        """
        if not parametrized_by:
            return ""

        par_sep = ";"
        suffix = " "
        for par in parametrized_by:
            val = data[par].iloc[0]
            par_name = par[0]
            suffix = f"{suffix}{par_name}={val}{par_sep}"
        return suffix[: -len(par_sep)]  # remove trailing separator

    @staticmethod
    def _plot_line(ax, data, line_spec, index_column, parametrized_by=None):
        label_suffix = DataTableCharts._label_suffix(parametrized_by, data)

        col = data[line_spec.column]
        col.index = data[index_column]

        col.plot(
            kind="line",
            ax=ax,
            label=f"{line_spec.label_base}{label_suffix}",
            **line_spec.line_kwargs,
        )

    def _chart_spec_and_ax(self, axes, row, column):
        if axes.ndim == 1:
            ax = axes[column]
        else:
            ax = axes[row, column]

        return self._charts[row][column], ax

    def _lines_subframes(self, ch_spec):
        if ch_spec.filter_by:
            data = self._data.filter_data(ch_spec.filter_by)
        else:
            data = self._data

        if ch_spec.parametrized_by:
            return self._subframes_by_params(data, ch_spec.parametrized_by)
        else:
            return [data]

    @staticmethod
    def _cast_value_to_column_type(data, column, value):
        return data.dtypes[column].type(value)

    def _get_colors_by_params(self, ch_spec, data):
        """Lines in current plot are defined by:
        1) filtering - selects data to plot
        2) parametrization - unique combination of parameters defines
        particular lines in chart.
        Thus, a color pair is bound to a key created from filter_by and
        parametrized_by values from chart specification.
        """

        color_key = dict()
        if ch_spec.filter_by:
            for k, v in ch_spec.filter_by.items():
                """Filtering values - key (column) + value - comes from
                a user. However, user does not know about data type used
                in underlying data table. This can lead to situations
                where an inconsistent data types are used. E.g. integer
                is passed as a value but in the data table a related
                column has a float data type. Using such mixed data
                types might than lead to non-matching keys.

                With normalization, values are always converted to data
                table data type.
                """
                color_key[k] = self._cast_value_to_column_type(data, k, v)
        if ch_spec.parametrized_by:
            for p in ch_spec.parametrized_by:
                color_key[p] = data[p].iloc[0]
        return self._colors.bind_color(**color_key)

    def _plot_data_lines(self, sub_frames, ch_spec, ax):
        for data in sub_frames:
            for line_spec in ch_spec.lines:
                if line_spec.color_shade is not None:
                    colors = self._get_colors_by_params(ch_spec, data.get_data())
                    line_spec.line_kwargs["color"] = colors[line_spec.color_shade]
                self._plot_line(
                    ax,
                    data.get_data(),
                    line_spec,
                    ch_spec.x_column,
                    ch_spec.parametrized_by,
                )

    def store_charts(self, chart_file, title=None):
        """Plot requested data into a file.

        Parameters:
        -----------
        chart_file : str or Path
            Path to a resulting file.
        title : str, optional
            Title of the figure.
        """

        fig, axes = self._prepare_layout()

        for i in range(self._n_rows):
            for j in range(self._n_cols):
                ch_spec, ax = self._chart_spec_and_ax(axes, i, j)

                sub_frames = self._lines_subframes(ch_spec)

                # All subframes are expected to have same max and index
                any_subframe = sub_frames[0]

                if ch_spec.max_column:
                    # Draw "max" line only once
                    self._plot_line(
                        ax,
                        any_subframe.get_data(),
                        ch_spec.max_column,
                        ch_spec.x_column,
                    )

                self._plot_data_lines(sub_frames, ch_spec, ax)

                self._format_ax(ax, ch_spec, any_subframe.get_data())

        if title:
            fig.suptitle(title, fontsize=18)
        fig.savefig(chart_file)
