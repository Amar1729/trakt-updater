#! /usr/bin/env python3

import datetime as dt
from itertools import zip_longest

# third-party
import tqdm
from picotui.context import Context
from picotui.screen import Screen
from picotui.widgets import Dialog, WButton, WLabel, WCheckbox, WRadioButton, WTextEntry, WMultiEntry, WDropDown
from picotui.widgets import ACTION_OK, ACTION_NEXT, ACTION_CANCEL
from picotui.defs import C_WHITE, C_BLUE

# local
import trakt_utils
import txt_tv_parser as ttp
from picotui_ext import WPager, WEpisodeWidget
from picotui_ext import EP_WATCHED


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
            while True:
                redraw_screen()
                x, y = Screen.screen_size()
                d = Dialog(0, 0, x, y)

                try:
                    # leave space for next/curr page labels
                    results = next(take(self.itr, y - 4))

                    for idx, show in enumerate(results):
                        w_checkbox = WCheckbox(show)
                        d.add(1, idx + 1, w_checkbox)

                        w_checkbox.on("changed", checkbox_changed)

                    b = WLabel(f"Page {self.page}")
                    d.add(1, y - 2, b)

                    b = WButton(8, "Next")
                    d.add(12, y - 2, b)
                    b.finish_dialog = ACTION_NEXT

                    b = WButton(8, "Done")
                    d.add(23, y - 2, b)
                    b.finish_dialog = ACTION_CANCEL

                    res = d.loop()

                    if res == ACTION_NEXT:
                        self.page += 1
                    elif res == ACTION_CANCEL:
                        Screen.cls()
                        return
                    else:
                        print(res)
                        raise Exception(res)

                except StopIteration:
                    Screen.cls()
                    return


class SeasonSelector:
    def __init__(self, show):
        self.show = show
        self.show_choice = None

    def run(self):
        shows = trakt_utils.search_tv(self.show)

        with Context():
            redraw_screen()
            x, y = Screen.screen_size()

            d = Dialog(0, 0, x, y)

            w_label = WLabel(f"> Searching: {self.show}")
            d.add(1, 1, w_label)

            show_display = lambda s: f"({s['year']}) - {s['title']}"
            w_radio = WRadioButton([show_display(show) for show in shows])
            w_radio.finish_dialog = ACTION_OK
            d.add(1, 3, w_radio)

            sd = list(trakt_utils.display_seasons(shows[0]["seasons"]))
            w_showinfo = WMultiEntry(x // 2 - 2, y - 6, sd)
            d.add(x // 2, 3, w_showinfo)

            def show_selector_changed(w):
                seasons = shows[w_radio.choice]["seasons"]
                sd = list(trakt_utils.display_seasons(seasons))
                w_showinfo.set(sd)
                w_showinfo.redraw()
            w_radio.on("changed", show_selector_changed)

            b2 = WButton(10, "Skip")
            d.add(2, y - 2, b2)
            b2.finish_dialog = ACTION_NEXT

            b_done = WButton(10, "Done")
            d.add(16, y - 2, b_done)
            b_done.finish_dialog = ACTION_CANCEL

            res = d.loop()

        if res == ACTION_OK:
            self.show_choice = shows[w_radio.choice]

        return res


def int_range_as_str(a, b):
    return list(map(str, range(a, b)))


class EpisodeSelector:
    def __init__(self, title, season):
        self.title = title
        self.season = season
        self.episodes = season.episodes

        # fill out in run()
        self.results = {}

    def run(self):
        episodes = list(map(WEpisodeWidget, self.episodes))

        if not episodes:
            return ACTION_CANCEL

        with Context():
            redraw_screen()
            x, y = Screen.screen_size()

            d = Dialog(0, 0, x, y)

            d.add(1, 1, f"> Selecting {len(self.episodes)} episodes for {self.title}: Season {self.season.number}")

            d.add(1 + x // 2, 3, "Mark multiple episodes on the same date (YYYY/MM/DD)")

            w_dates = [
                WDropDown(6, int_range_as_str(1980, dt.datetime.now().year + 1)[::-1], dropdown_h=12),
                WDropDown(4, int_range_as_str(1, 13), dropdown_h=14),
                WDropDown(4, int_range_as_str(1, 32), dropdown_h=12),
            ]

            d.add(1 + x // 2, 4, "(optional) Input Date:")
            i = 24 + x // 2
            d.add(i, 4, w_dates[0])
            d.add(i + 7, 4, w_dates[1])
            d.add(i + 12, 4, w_dates[2])

            w_input_date = WButton(12, "Input Date")
            d.add(1 + x // 2, 5, "Each non-skipped episode watched on input date")
            d.add(1 + x // 2, 6, w_input_date)
            w_input_date.finish_dialog = 1005

            w_release_label = WLabel("Each episode watched on release")
            w_release = WButton(12, "On Release")
            d.add(1 + x // 2, 8, w_release_label)
            d.add(1 + x // 2, 9, w_release)
            w_release.finish_dialog = 1004

            w_done_label = WLabel("Mark each episode (as selected on the left)")
            w_done = WButton(15, "Finish Season")
            d.add(1 + x // 2, 11, w_done_label)
            d.add(1 + x // 2, 12, w_done)
            w_done.finish_dialog = ACTION_OK

            w_skip = WButton(13, "Skip Season")
            d.add(1 + x // 2, 14, w_skip)
            w_skip.finish_dialog = ACTION_CANCEL

            w_skip_show = WButton(19, "Skip Rest of Show")
            d.add(1 + x // 2, 16, w_skip_show)
            w_skip_show.finish_dialog = ACTION_NEXT

            w_pager = WPager(y - 5, episodes, d, offset=1)
            d.add(1, 3, w_pager)

            res = d.loop()

        get_dd = lambda i: int(w_dates[i].items[w_dates[i].choice])

        if res in [ACTION_OK, 1004]:
            for w_ep in w_pager.items:
                if w_ep.choice == EP_WATCHED.AIRED:
                    # datetime.datetime object
                    self.results[w_ep.ep] = w_ep.ep.first_aired_date
                elif w_ep.choice == EP_WATCHED.DATE:
                    d = dt.datetime(year=get_dd(0), month=get_dd(1), day=get_dd(2))
                    self.results[w_ep.ep] = d
        elif res in [1005, 1006]:
            for w_ep in w_pager.items:
                if res == 1006 or w_ep.choice != EP_WATCHED.SKIP:
                    d = dt.datetime(year=get_dd(0), month=get_dd(1), day=get_dd(2))
                    self.results[w_ep.ep] = d

        return res


def select_watched_shows():
    """
    Select the tv shows you've watched (from find_movies)
    This function will serialize selected shows to a file
    for later ingestion in update_trakt
    """
    p = Paginate(ttp.find_movies())
    p.run()

    ttp.serialize(p.selected)


def episode_updates(results):
    # unholy combination of TUI + tqdm ???
    [trakt_utils.non_interactive_episode_add(*e) for e in tqdm.tqdm(results.items())]


def update_trakt(defer):
    tv_shows = list(ttp.get_selected())

    for show in tv_shows:
        s = SeasonSelector(show)
        ret = s.run()

        # skip this season on ACTION_NEXT

        if ret == ACTION_CANCEL:
            return

        elif ret == ACTION_OK:
            assert s.show_choice is not None
            for season in s.show_choice["seasons"]:
                ep = EpisodeSelector(s.show_choice["title"], season)
                res = ep.run()

                if res in [ACTION_OK, 1004, 1005, 1006]:
                    if defer:
                        trakt_utils.bad_serializer(ep.results)
                    else:
                        episode_updates(ep.results)
                elif res == ACTION_CANCEL:
                    # skipping this season
                    pass
                elif res == ACTION_NEXT:
                    # skip the rest of this show
                    break
                else:
                    raise Exception(res)


def deferred_updates():
    print("The serialized file is NOT removed between runs.")
    print("This will result in deuplicate plays of episodes if you re-run deferred updates.")
    print("Make sure to delete serialized.pickle after successful updates.")
    for d in trakt_utils.read_serialized():
        ep = list(d.items())[0][0]
        print(f"> {ep.show} - Season {ep.season}")
        episode_updates(d)


def main():
    trakt_utils.auth_trakt()

    with Context():
        redraw_screen()
        x, y = Screen.screen_size()

        get_x = lambda w: x // 2 - len(w.t) // 2

        d = Dialog(0, 0, x, y)

        w_select = WButton(14, "select shows")
        w_select.finish_dialog = 1

        w_trakt = WButton(14, "update trakt")
        w_trakt.finish_dialog = 2

        d.add(get_x(w_select), y // 4, w_select)
        d.add(get_x(w_trakt), 3 * y // 4, w_trakt)

        res = d.loop()

        if res == 2:
            d = Dialog(0, 0, x, y)

            w_settings = [
                WButton(47, "Defer updates until all episodes are selected"),
                WButton(52, "Run trakt API calls after each season is complete"),
                WButton(39, "Run trakt updates from a previous run")
            ]
            w_settings[0].finish_dialog = ACTION_OK
            w_settings[1].finish_dialog = ACTION_CANCEL
            w_settings[2].finish_dialog = 1004

            d.add(get_x(w_settings[0]), y // 2 - 2, w_settings[0])
            d.add(get_x(w_settings[1]), y // 2, w_settings[1])
            d.add(get_x(w_settings[2]), y // 2 + 2, w_settings[2])

            defer = d.loop()

    if res == 1:
        select_watched_shows()
    elif res == 2:
        if defer == 1004:
            deferred_updates()
        else:
            update_trakt(defer == ACTION_OK)


if __name__ == "__main__":
    # possible TODO: add arguments to specify txt files for input
    main()
