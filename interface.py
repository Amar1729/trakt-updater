#! /usr/bin/env python3

# import time
import sys
from itertools import zip_longest

from picotui.context import Context
from picotui.screen import Screen
from picotui.widgets import Dialog, WButton, WLabel, WCheckbox, WRadioButton, WTextEntry, WMultiEntry
from picotui.widgets import ACTION_OK, ACTION_CANCEL
from picotui.defs import C_WHITE, C_BLUE

# local
import trakt_utils
import txt_tv_parser as ttp
from picotui_ext import WPager, WEpisodeWidget


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
        self.episodes = season.episodes

        # fill out in run()
        self.results = {}

    def run(self):
        episodes = list(map(WEpisodeWidget, self.episodes))

        with Context():
            redraw_screen()
            x, y = Screen.screen_size()

            d = Dialog(0, 0, x, y)

            w_label = WLabel(f"> Selecting {len(self.episodes)} episodes for {self.title}: Season {self.season.number}")
            d.add(1, 1, w_label)

            w_input_date = WTextEntry(11, "YYYY/MM/DD")
            w_input_label = WLabel("(optional) Input Date:")
            d.add(1 + x // 2, 3, w_input_label)
            d.add(24 + x // 2, 3, w_input_date)

            w_input_explanation = WLabel("Input Date: mark multiple episodes on the same date")
            d.add(1 + x // 2, 4, w_input_explanation)

            w_release_label = WLabel("Each episode watched on release")
            w_release = WButton(12, "On Release")
            d.add(1 + x // 2, 6, w_release_label)
            d.add(1 + x // 2, 7, w_release)
            w_release.finish_dialog = 1004

            w_done_label = WLabel("Mark each episode as selected on the left")
            w_done = WButton(15, "Finish Season")
            d.add(1 + x // 2, 9, w_done_label)
            d.add(1 + x // 2, 10, w_done)
            w_done.finish_dialog = ACTION_OK

            w_skip = WButton(13, "Skip Season")
            d.add(1 + x // 2, 12, w_skip)
            w_skip.finish_dialog = ACTION_CANCEL

            w_pager = WPager(y - 8, episodes, d, offset=1)
            d.add(1, 3, w_pager)

            res = d.loop()

        if res in [ACTION_OK, 1004]:
            for w_ep in w_pager.items:
                if w_ep.choice == 0:
                    self.results[w_ep.ep] = w_ep.ep.first_aired_date
                elif w_ep.choice == 1:
                    # TODO - add date parsing to this input somehow?
                    self.results[w_ep.ep] = w_input_date.t

        return res


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
            for season in sc["seasons"]:
                e = EpisodeSelector(sc["title"], season)
                res = e.run()

                # TODO - implement actual trakt calls
                if res == ACTION_OK:
                    print("do stuff with trakt")
                    print()
                    for e, c in e.results.items():
                        print(e, c)
                elif res == 1004:
                    print("mark each ep watched on release")
                    for e, c in e.results.items():
                        print(e, c)
                elif res == ACTION_CANCEL:
                    # skipping this season
                    print('skip')
                else:
                    print(res)

                # while testing
                break

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
