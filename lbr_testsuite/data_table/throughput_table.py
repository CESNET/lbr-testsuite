"""
Author(s): Pavel Krobot <Pavel.Krobot@cesnet.cz>

Copyright: (C) 2024 CESNET, z.s.p.o.

Tabular data storage for throughput measurements.
"""

import csv
import pathlib
from enum import StrEnum
from typing import Any, Union

import pandas as pd


class VALUE_COLUMN(StrEnum):
    MBPS = "Measured (Mbps)"
    EXP_MBPS = "Expected (Mbps)"
    MAX_MBPS = "Max (Mbps)"
    MPPS = "Measured (Mpps)"
    EXP_MPPS = "Expected (Mpps)"
    MAX_MPPS = "Max (Mpps)"


"""Commonly used "value columns" for throughput table."""
COMMON_VALUES_COLUMNS = [c.value for c in VALUE_COLUMN]


class ThroughputTable:
    """Simple class for storage of tabular data.

    The class stores data table rows in form of a list of dictionaries.
    Dictionary keys represents column names.

    ThroughputTable consists of two columns type - value columns and
    index columns. Default "packet length" index column is always
    present. Other index columns (i.e. parameters) are optional. Using
    these two kind of columns a pandas.DataFrame with MultiIndex can
    be easily created (see 'to_data_frame()' method).
    """

    PACKET_LENGTH_COLUMN = "Packet Length"

    def __init__(self, value_columns: list, index_columns: list = None):
        """Initialize empty throughput table.

        There has to be at least one value column. Index columns are
        optional as there is always one mandatory index
        column - PACKET_LENGTH_COLUMN.

        Parameters
        ----------
        value_columns: list(str)
            Names of value columns.
        index_columns: list(str), optional
            Names of index columns (i.e. parameters)
        """

        if index_columns is None:
            index_columns = []

        assert len(value_columns) >= 1
        assert len(value_columns + index_columns) == len(set(value_columns + index_columns))
        assert self.PACKET_LENGTH_COLUMN not in value_columns
        assert self.PACKET_LENGTH_COLUMN not in index_columns

        self._data = []
        self._value_cols = value_columns
        self._index_cols = [self.PACKET_LENGTH_COLUMN] + index_columns
        self._cols = self._index_cols + self._value_cols

        self._df_last = None

    @property
    def df(self) -> pd.DataFrame:
        """Get stored data as pandas.DataFrame

        Index columns are used to form a hierarchical MultiIndex.
        """

        if self._df_last is None or self._df_last.shape[0] != len(self._data):
            # DataFrame has not been created yet or row(s) has been
            # appended since last DataFrame creation ...
            df = pd.DataFrame(self._data)
            self._df_last = df.set_index(self._index_cols)

        return self._df_last

    def empty(self) -> bool:
        """Check whether a table contains some data.

        Returns
        -------
        bool
            False when data table contains some data, True otherwise.
        """

        return len(self._data) == 0

    def append_row(self, row: dict):
        """Append row to the throughput table.

        row: dict
            Dictionary with keys matching all index and value columns.
        """

        assert set(row.keys()) == set(self._index_cols + self._value_cols), "Missing some column(s)"
        self._data.append(row)

    def values_to_numeric(self):
        """Convert values in columns to int or float if possible.

        All values in a column are converted to same type (if possible)
        or kept as original type.
        """

        conv_table = dict()
        for col in self._cols:
            conv_type = int
            for row in self._data:
                try:
                    # first try int, as float cant be converted to int in this way
                    int(row[col])
                except ValueError:
                    # every value which can be converted to int can be converted to float also
                    conv_type = float
                    try:
                        float(row[col])
                    except ValueError:
                        # no conversion - keep value original type
                        conv_type = None
                        break

            if conv_type:
                conv_table[col] = conv_type

        for row in self._data:
            for col in row.keys():
                try:
                    row[col] = conv_table[col](row[col])
                except KeyError:
                    pass

    def load_rows(self, csv_file: Union[str, pathlib.Path], convert_numeric: bool = True):
        """Load data rows from CSV file.

        Columns of a CSV file has to match index and values columns of
        the throughput table.

        Parameters
        ----------
        csv_file: str or pathlib.Path
            Path to a source CSV file.
        convert_numeric: bool, optional
            Try to convert loaded values into numeric types. First try
            to convert to int, if that fails try float. All values in a
            column are converted to the same type or none of them is.
            Conversion is turned on by default.
        """

        with open(str(csv_file)) as csvfile:
            reader = csv.DictReader(csvfile)
            if set(reader.fieldnames) != set(self._cols):
                raise RuntimeError(
                    "Non-matching set of columns in data file and throughput table:\n"
                    f"file : {reader.fieldnames},\n"
                    f"table: {self._cols}"
                )

            for row in reader:
                self.append_row(row)

            if convert_numeric:
                self.values_to_numeric()

    def get(
        self,
        index_values: dict,
        value_cols: list = None,
        force_series: bool = False,
    ) -> Union[pd.Series, Any]:
        """Get a value from the throughput table using composed index.

        All index columns has to be set as keys of index_values.

        Parameters:
        -----------
        index_values: dict
            Dictionary with containing values for all index columns.
        value_cols: list, optional
            Selected value columns (by default all value columns are
            returned).
        force_series: bool, optional
            Always return pandas.Series object. This turns off
            an optimization for single-value data (single value column).
            By default, single-value data are returned directly instead
            in pandas.Series object.

        Returns:
        --------
        pandas.Series or Any
            Value(s) from the table on the requested index in a form
            of pandas.Series object or direct value (see `force_series`
            parameter description).
        """

        if not value_cols:
            value_cols = self._value_cols

        index = ()
        for c in self._index_cols:
            index = index + (index_values[c],)

        row = self.df.loc[index, value_cols]

        if len(value_cols) == 1 and not force_series:
            return row.iloc[0]
        else:
            return row

    def set(
        self,
        index_values: dict,
        values: dict,
    ):
        """Set a value in the throughput table using composed index.

        All index columns has to be set as keys of index_values.

        Parameters:
        -----------
        index_values: dict
            Dictionary with containing values for all index columns.
        values: dict
            Values for all value columns.
        """

        assert set(self._value_cols) == set(values.keys()), "Missing some column(s) value"

        index = ()
        for c in self._index_cols:
            index = index + (index_values[c],)

        # cast to the column(s) data type(s) explicitly
        curr_val = self.df.loc[index]
        for k, v in values.items():
            values[k] = curr_val[k].dtype.type(v)

        self.df.loc[index] = values

    def to_csv(self, csv_file: Union[str, pathlib.Path]):
        """Store data as a CSV file.

        Parameters
        ----------
        csv_file: str or pathlib.Path
            Path to the destination CSV file.
        """

        self.df.to_csv(str(csv_file))
