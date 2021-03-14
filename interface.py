#! /usr/bin/env python3

# import time
from itertools import zip_longest

from picotui.context import Context
from picotui.screen import Screen
from picotui.widgets import Dialog, WButton, WLabel, ACTION_OK, WCheckbox
from picotui.defs import C_WHITE, C_BLUE

# local
from txt_tv_parser import find_movies


def take_filled(iterable, n):
    args = [iter(iterable)] * n
    return zip_longest(*args)


def take(iterable, n):
    try:
        g = next(take_filled(iterable, n))
        yield list(filter(lambda e: e is not None, g))
    except StopIteration:
        return []


# wrapper widget to paginate multiple items and allow multi-selection.
# only allows "next"/"done" (no "previous")
# access results with Paginate.selected after completion
# (assumes all items are unique, order is not retained)
class Paginate:
    def __init__(self, itr):
        self.selected = set()
        self.itr = itr
        self.page = 1

    def run(self):
        def checkbox_changed(w):
            if w.choice:
                self.selected.update([w.t])
            else:
                if w.t in self.selected:
                    self.selected.remove(w.t)

        def redraw_screen():
            Screen.attr_color(C_WHITE, C_BLUE)
            Screen.cls()
            Screen.attr_reset()

        with Context():
            redraw_screen()
            x, y = Screen.screen_size()

            while True:
                d = Dialog(3, 1, x - 6, y - 2)

                try:
                    # leave space for next/curr page labels
                    results = next(take(self.itr, y - 8))

                    for idx, show in enumerate(results):
                        w_checkbox = WCheckbox(show)
                        d.add(1, idx + 1, w_checkbox)

                        w_checkbox.on("changed", checkbox_changed)

                    b = WLabel(f"Page {self.page}")
                    d.add(1, y - 5, b)

                    b = WButton(8, "Next")
                    d.add(12, y - 5, b)
                    b.on("click", lambda w: 1/0)

                    b = WButton(8, "Done")
                    d.add(23, y - 5, b)
                    b.finish_dialog = ACTION_OK

                    d.loop()
                    break

                except ZeroDivisionError:
                    self.page += 1
                    redraw_screen()
                    d.redraw()

                except StopIteration:
                    # redraw_screen()
                    Screen.cls()

                    """
                    # this approach doesn't work ?
                    d = Dialog(3, 1, x - 6, y - 2)

                    b = WLabel("No more results, exiting")
                    d.add(1, y - 4, b)

                    time.sleep(2)
                    """

                    break

        print()


def main():
    p = Paginate(find_movies())
    p.run()

    with open("tv-show-selected.txt") as f:
        current = set([line.strip() for line in f.readlines() if line.strip()])

    current.update(p.selected)

    with open("tv-show-selected.txt", "w") as f:
        for show in current:
            f.write(show)
            f.write("\n")


if __name__ == "__main__":
    main()
