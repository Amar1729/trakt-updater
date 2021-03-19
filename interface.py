#! /usr/bin/env python3

# import time
import sys
from itertools import zip_longest

from picotui.context import Context
from picotui.screen import Screen
from picotui.widgets import Dialog, WButton, WLabel, ACTION_OK, ACTION_CANCEL, WCheckbox
from picotui.widgets import WRadioButton, WMultiEntry
from picotui.defs import C_WHITE, C_BLUE

# local
import trakt_utils
import txt_tv_parser as ttp


def take_filled(iterable, n):
    args = [iter(iterable)] * n
    return zip_longest(*args)


def take(iterable, n):
    try:
        g = next(take_filled(iterable, n))
        yield list(filter(lambda e: e is not None, g))
    except StopIteration:
        return []


def redraw_screen():
    Screen.attr_color(C_WHITE, C_BLUE)
    Screen.cls()
    Screen.attr_reset()


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
                    b.on("click", lambda w: 1 / 0)

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


class SeasonSelector:
    def __init__(self, show):
        self.show = show
        self.show_choice = None

    def assign(self, show_choice):
        self.show_choice = show_choice
        raise ZeroDivisionError

    def _run(self):
        shows = trakt_utils.search_tv(self.show)

        with Context():
            redraw_screen()
            x, y = Screen.screen_size()

            d = Dialog(3, 1, x - 6, y - 2)

            w_label = WLabel(f"> Searching: {self.show}")
            d.add(1, 1, w_label)

            show_display = lambda s: f"({s['year']}) - {s['title']}"
            w_radio = WRadioButton([show_display(show) for show in shows])
            d.add(1, 3, w_radio)

            sd = list(trakt_utils.display_seasons(shows[0]["seasons"]))
            w_showinfo = WMultiEntry(x // 2 - 10, y - 10, sd)
            d.add(x // 2, 3, w_showinfo)

            def show_selector_changed(w):
                seasons = shows[w_radio.choice]["seasons"]
                sd = list(trakt_utils.display_seasons(seasons))
                w_showinfo.set(sd)
                w_showinfo.redraw()
            w_radio.on("changed", show_selector_changed)

            b = WButton(10, "Select")
            d.add(3, y - 5, b)

            b2 = WButton(10, "Skip")
            d.add(18, y - 5, b2)
            b2.finish_dialog = ACTION_CANCEL

            b.on("click", lambda w: self.assign(shows[w_radio.choice]))

            d.loop()

    def run(self):
        try:
            self._run()
        except ZeroDivisionError:
            return self.show_choice
        return None


class EpisodeSelector:
    def __init__(self, title, season):
        self.title = title
        self.season = season

    def run(self):
        with Context():
            redraw_screen()
            x, y = Screen.screen_size()

            d = Dialog(3, 1, x - 6, y - 2)

            w_label = WLabel(f"> Selecting episodes for {self.title}: {self.season.title}")
            d.add(1, 1, w_label)

            # todo - impl.
            w_checkbox = WCheckbox("State")
            d.add(1, 3, w_checkbox)

            d.loop()


def select_watched_shows():
    """
    Select the tv shows you've watched (from find_movies)
    This function will write out year - month - name of show
    to tv-show-selected.txt for later input
    """
    p = Paginate(ttp.find_movies())
    p.run()

    with open("tv-show-selected.txt") as f:
        current = set([line.strip() for line in f.readlines() if line.strip()])

    current.update(p.selected)

    with open("tv-show-selected.txt", "w") as f:
        for show in current:
            f.write(show)
            f.write("\n")


def update_trakt():
    tv_shows = list(ttp.get_selected())

    for show in tv_shows:
        s = SeasonSelector(tv_shows[0])
        sc = s.run()

        if sc:
            print(sc)
            for season in sc["seasons"]:
                e = EpisodeSelector(sc["title"], season)
                e.run()

        # only run on first show while testing
        break


if __name__ == "__main__":
    try:
        action = sys.argv[1]
    except IndexError:
        action = ""

    if action not in ["select", "trakt"]:
        print("Usage:")
        print("  python interface.py select")
        print("    -> select watched shows from list")
        print("  python interface.py trakt")
        print("    -> update trakt with watched tv shows")
        sys.exit(1)

    if action == "select":
        select_watched_shows()
    else:
        update_trakt()
