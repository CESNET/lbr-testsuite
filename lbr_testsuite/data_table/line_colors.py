"""
Author(s): Pavel Krobot <Pavel.Krobot@cesnet.cz>

Copyright: (C) 2023 CESNET, z.s.p.o.

Class for pairing related lines with same color of different shade (one
lighter, one darker). Class defines pool of 15 color pairs. One can bind
a color pair to some pair of lines using arbitrary arguments. From these
arguments a key is created which can be reused for same pair using same
arguments.
"""

import itertools


class LineColors:
    def __init__(self):
        _color_pairs_list = [
            ("#b22222", "#fa8072"),  # red
            ("#2e7d32", "#bbfa73"),  # green
            ("#283593", "#42a5f5"),  # light-blue
            ("#5d4037", "#a1887f"),  # brown
            ("#ffd700", "#fff59d"),  # yellow
            ("#ff1493", "#ffc0cb"),  # pink as a piggy
            ("#689f38", "#9ccc65"),  # army green
            ("#20b2aa", "#00ffff"),  # turquoise
            ("#8b4513", "#d2691e"),  # brown
            ("#6a1b9a", "#ee82ee"),  # violet
            ("#9e9d24", "#d4e157"),  # beige
            ("#00695c", "#26a69a"),  # dark-turquoise
            ("#f57c00", "#ffe082"),  # orange
            ("#ad1457", "#e91e63"),  # pink-red
            ("#455a64", "#90a4ae"),  # grayish
            ("#c1ae4f", "#fce367"),  # yellow-grey
            ("#244475", "#2c2475"),  # navy blue
            ("#80ad0f", "#a6e014"),  # apple green
            ("#96247f", "#fc44d7"),  # hot pink
            ("#477777", "#7a9b9b"),  # shallow blue
        ]

        self._color_pairs = itertools.cycle(_color_pairs_list)
        self._bindings = dict()

    def bind_color(self, **args):
        """Bind a color pair to a key created from arguments. Count and
        type of arguments is optional and fully in control of a caller.

        Calling this method for same arguments and its values provides
        always same color pair.

        Returns
        -------
        tuple(str, str)
            Pair of color definitions in RGB hex format. When all pairs
            are exhausted a tuple (None, None) is returned.
        """

        k_pairs = []
        for k, v in args.items():
            k_pairs.append(f"{k}={v}")
        k_pairs.sort()

        key = ""
        for k in k_pairs:
            key = f"{key}+{k}"
        key = key[1:]

        if key not in self._bindings:
            # _color_pairs is circular, can never raise StopIteration.
            self._bindings[key] = next(self._color_pairs)

        return self._bindings[key]
