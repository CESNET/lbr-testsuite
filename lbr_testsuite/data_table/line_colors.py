"""
Author(s): Pavel Krobot <Pavel.Krobot@cesnet.cz>

Copyright: (C) 2023 CESNET, z.s.p.o.

Class for pairing related lines with same color of different shade (one
lighter, one darker). Class defines pool of 15 color pairs. One can bind
a color pair to some pair of lines using arbitrary arguments. From these
arguments a key is created which can be reused for same pair using same
arguments.
"""


class LineColors:
    def __init__(self):
        self._color_pairs = [
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
        ]

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
            try:
                self._bindings[key] = self._color_pairs.pop(0)
            except IndexError:
                # Pool of color pairs exhausted
                return None, None

        return self._bindings[key]
