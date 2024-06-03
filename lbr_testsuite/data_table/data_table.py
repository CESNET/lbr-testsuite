"""
Author(s): Pavel Krobot <Pavel.Krobot@cesnet.cz>

Copyright: (C) 2023 CESNET, z.s.p.o.

Common module for manipulating tabular data.

This module is deprecated - use rather ThroughputTable for storage of
throughput data or pandas.DataTable directly.
"""

from __future__ import annotations  # postponed evaluation of annotations

import pathlib
from typing import Optional, Union

import pandas


class DataTable:
    """Class responsible for storing tabular data based on
    pandas.DataFrame.
    """

    def __init__(self, init_data: Union[tuple, pandas.DataFrame]):
        """Initialize a data table instance.

        Parameters
        ----------
        init_data : Union[tuple, padans.DataFrame]
            Column names or DataFrame with initialization data.
        """

        if isinstance(init_data, pandas.DataFrame):
            self._df = init_data.copy()
        else:
            self._df = pandas.DataFrame(columns=init_data)

    def get_data(self) -> pandas.DataFrame:
        """Return stored data.

        Returns
        -------
        pandas.DataFrame
            Data stored within the DataTable.
        """

        return self._df

    def empty(self) -> bool:
        """Check whether a table contains some data

        Returns
        -------
        bool
            False when data table contains some data, True otherwise.
        """

        return self._df.empty

    def get_column_unique_values(self, column: str) -> list:
        """Get all unique values from single column.

        Parameters
        ----------
        column : str
            Name of selected column.

        Returns
        -------
        list
            Unique values returned from selected column.
        """

        return list(self._df[column].unique())

    def _column_is_numeric(self, key: str) -> bool:
        return self._df[key].dtype.kind in "iufc"

    def _quote_non_numeric(self, key, val):
        if self._column_is_numeric(key):
            return val
        else:
            return f'"{val}"'

    def _filter_to_query(self, filter_dict: dict) -> str:
        sub_q = []
        for key, val in filter_dict.items():
            val = self._quote_non_numeric(key, val)
            sub_q.append(f"{key}=={val}")

        return " & ".join(sub_q)

    def _filter_data_frame(self, filter_by: dict) -> pandas.DataFrame:
        filter_query = self._filter_to_query(filter_by)
        return self._df.query(filter_query)

    def filter_data(self, filter_by: dict) -> DataTable:
        """Get data filtered by values of selected columns.

        Parameters:
        -----------
        filter_by : dict
            Dictionary where keys are column names and values are values
            to filter. Currently only we can filter only by a single
            value of a column.

        Returns:
        --------
        DataTable
            DataTable containing only rows matching to the filter.
        """

        return DataTable(self._filter_data_frame(filter_by))

    def append_row(self, row: tuple):
        """Append one row to the table.

        Note: Values of all columns has to be set.

        Parameters
        ----------
        row : tuple
            Tuple of values to write..
        """

        current_row = len(self._df.index)
        self._df.loc[current_row] = row

    def store_csv(self, csv_file: Union[str, pathlib.Path], filter_by: Optional[dict] = None):
        """Store data from data table to CSV file.

        Parameters
        ----------
        csv_file : str or Path
            Path to an output CSV file.
        filter_by : dict, optional
            Dictionary where keys are column names and values are values
            to filter. Used to filter rows which should be
            stored. None by default (i.e. save all data).
        """

        data = self._df
        if filter_by:
            data = self._filter_data_frame(filter_by)

        data.to_csv(csv_file, index=False)
