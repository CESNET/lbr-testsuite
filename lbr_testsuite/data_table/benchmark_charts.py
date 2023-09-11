"""
Author(s): Pavel Krobot <Pavel.Krobot@cesnet.cz>

Copyright: (C) 2023 CESNET, z.s.p.o.

Common functions for benchmark tests charts.
"""

from . import charts


class BenchmarkCharts:
    """Utility class providing common methods and definitions for
    benchmark tests.
    """

    """ Common names of columns used by throughput tests."""
    BASE_COLUMNS_HEADER = [
        "Packet Length",
        "Measured (Mbps)",
        "Expected (Mbps)",
        "Max (Mbps)",
        "Measured (Mpps)",
        "Expected (Mpps)",
        "Max (Mpps)",
    ]

    @staticmethod
    def _max_line_spec(column):
        """Specification of line with maximal values.

        Dark grey dashed line with circles as markers.
        """

        return charts.PlotLineSpec(
            column=column,
            label_base="Max",
            line_kwargs=dict(
                color="dimgrey",
                linestyle="dashed",
                marker="o",
            ),
        )

    @staticmethod
    def chart_spec(kind, title, parametrized_by=None, filter_by=None, expected=True):
        """Create single chart specification.

        The chart contains one line with maximal values and pair
        of lines (expected and measured) for each unique values combination
        from columns specified by ``parametrized_by``.

        e.g. having some data:

        +==================================================================+
        | Mbps | exp b | max b | Mpps | exp p | max p | par1 | par2 | par3 |
        +------------------------------------------------------------------+
        | 100  | 200   | 999   | 2    | 2     | 10    | x    | 1    | aa   |
        | 200  | 500   | 999   | 2    | 4     | 10    | x    | 2    | aa   |
        | 110  | 200   | 999   | 2    | 2     | 10    | y    | 1    | aa   |
        | 220  | 600   | 999   | 2    | 4     | 10    | y    | 2    | aa   |
        | 600  | 600   | 999   | 2    | 6     | 10    | x    | 1    | ab   |
        | 700  | 700   | 999   | 2    | 7     | 10    | x    | 2    | ab   |
        | 610  | 800   | 999   | 2    | 8     | 10    | y    | 1    | ab   |
        | 720  | 999   | 999   | 2    | 10    | 10    | y    | 2    | ab   |
        +==================================================================+

        There is only single measured value for every combination of
        arguments. Thus, resulting line will be only single point. This
        is only for example simplicity. In real measurements there will be
        more points (e.g. per various packet length).

        We would like to plot measurements in Mbps for par3 = aa only.
        There should be two lines for each combination of par1 and par2.
        Thus, 8 lines:
        - measured and expected bits for: par1 = x, par2 1
        - measured and expected bits for: par1 = x, par2 2
        - measured and expected bits for: par1 = y, par2 1
        - measured and expected bits for: par1 = y, par2 2
        Moreover, one line for maximal values is added (max is expected to
        be same for all parameter combinations).

        So having this call:
        chart_spec(
            kind="Mbps",
            title="Example Mbps, aa only",
            parametrized_by=["par1", "par2"],
            filter_by=dict(par3="aa"),
        )

        We will have a specification for single chart with 9 lines as
        described above.


        Parameters
        ----------
        kind : str
            Selects which kind of chart should be created - bits: "Mbps" or
            packets: "Mpps".
        title : str
            Title of created chart.
        parametrized_by : str or list(str), optional
            List of column names. Pair of lines ("expected" and "measured")
            is created for each unique values combination from these
            columns.
        filter_by : dict, optional
            Key-value pairs where key is a column name, value is value to
            be filtered. Filters data to plot. ``parametrized_by`` is
            applied after this data filtering.
        expected : bool, optional
            Information whether "expected" values should be plotted.

        Returns
        -------
        PlotSpec
            Instance of PlotSpec class containing a single chart
            specification.
        """

        assert kind in ["Mbps", "Mpps"]

        ylabels = dict(
            Mbps="Bit rate (Mbps)",
            Mpps="Packet rate (Mpps)",
        )

        line_spec_list = [
            charts.PlotLineSpec(
                column=f"Measured ({kind})",
                label_base="Measured",
                color_shade=0,
                line_kwargs=dict(marker="x"),
            ),
        ]

        if expected:
            line_spec_list.append(
                charts.PlotLineSpec(
                    column=f"Expected ({kind})",
                    label_base="Expected",
                    color_shade=1,
                    line_kwargs=dict(
                        linestyle="dashdot",
                        marker="s",
                    ),
                ),
            )

        return charts.PlotSpec(
            line_spec_list,
            title=title,
            max_column=BenchmarkCharts._max_line_spec(f"Max ({kind})"),
            x_column="Packet Length",
            parametrized_by=parametrized_by,
            filter_by=filter_by,
            xlabel="Packet Length (B)",
            ylabel=ylabels[kind],
        )
