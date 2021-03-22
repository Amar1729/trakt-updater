"""
Widget extensions to `picotui`
"""

from enum import Enum
from typing import List
from picotui.widgets import Widget, Dialog

from picotui.widgets import ItemSelWidget, FocusableWidget

from picotui.defs import C_B_BLUE, C_GREEN, C_B_GREEN
from picotui.defs import KEY_UP, KEY_DOWN, KEY_ENTER, DOWN_ARROW, KEY_TAB, KEY_SHIFT_TAB
from picotui.widgets import ACTION_OK

UP_ARROW = chr(8593)


class WPager(ItemSelWidget):
    """
    possible todo: "scrollbar" indicating position in multi-paged output
    """

    def __init__(self, h: int, widgets: List[Widget], parent_dialog: Dialog, offset=0):
        super().__init__(widgets)
        self.w = max(w.w for w in widgets) + 2
        self.h = h
        self.offset = offset

        self.focus = False
        self.focus_w = None
        self.parent = parent_dialog

        # override parent Dialog's handle_key with ours
        self.parent_handle_key = self.parent.handle_key
        self.parent.handle_key = self.handle_key

        self.displayed: List[Widget] = []
        self.reorder(start=0)

    def reorder(self, start=None, end=None):
        itr = None
        if start is not None and start < len(self.items):
            itr = range(self.choice, len(self.items))
        if end is not None and end < len(self.items):
            # itr = range(len(self.items) - 1, 0, -1)
            itr = range(end, 0, -1)
        assert itr is not None

        height = 0
        self.displayed = []
        for i in itr:
            if height + self.items[i].h <= self.h:
                if start is not None:
                    # counting up
                    self.displayed.append(i)
                else:
                    # counting down
                    self.displayed.insert(0, i)
                height += self.items[i].h + self.offset
            else:
                break

    def _remove_from_dialog(self, wi):
        if self.items[wi] in self.parent.childs:
            self.parent.childs.remove(self.items[wi])

    def _inside(self):
        if self.focus:
            return True
        if self.parent.focus_w in self.items:
            return True
        return False

    def redraw(self):
        # can be optimized by using a shifting window instead of re-calculating whole thing
        for wi in self.displayed:
            self._remove_from_dialog(wi)

        if self.choice < self.displayed[0]:
            self.reorder(start=self.choice)
        if self.choice > self.displayed[-1]:
            self.reorder(end=self.choice)

        if self.displayed[0] > 0:
            self.goto(self.x, self.y)
            self.wr(UP_ARROW)
        else:
            if self.focus:
                self.attr_color(C_B_BLUE, None)
            self.goto(self.x, self.y)
            self.wr("-")
            if self.focus:
                self.attr_reset()

        shade = C_B_GREEN if self._inside() else C_GREEN

        i = self.y
        for wi in self.displayed:
            for x in range(0, self.items[wi].h):
                self.goto(self.x + 1, i + x)
                self.attr_color(shade, None)
                if self.choice == wi:
                    self.wr(">")
                else:
                    self.wr("|")
                self.attr_reset()

            if wi != self.displayed[-1] or True:
                for x in range(0, self.offset):
                    self.goto(self.x + 1, i + x + self.items[wi].h)
                    self.attr_color(shade, None)
                    self.wr("|")
                    self.attr_reset()

            if wi == self.displayed[-1]:
                for y in range(i + x + self.items[wi].h, self.y + self.h):
                    self.goto(self.x + 1, y + 1)
                    self.attr_color(shade, None)
                    self.wr("|")
                    self.attr_reset()

            self.parent.add(self.x + 2, i, self.items[wi])
            i += self.items[wi].h + self.offset

        if self.displayed[-1] < len(self.items) - 1:
            self.goto(self.x, self.y + self.h)
            self.wr(DOWN_ARROW)
        else:
            if self.focus:
                self.attr_color(C_B_BLUE, None)
            # self.goto(self.x, self.h - self.y - 1)
            self.goto(self.x, self.y + self.h)
            self.wr("-")
            if self.focus:
                self.attr_reset()

    def handle_key(self, key):
        if key in [KEY_UP, KEY_DOWN]:
            if self.focus_w != self.choice:
                return
            else:
                if self.focus_w is not None:
                    if self.focus:
                        return
                    if self.focus_w != self.parent.focus_w:
                        return self.parent_handle_key(key)

        if key in [KEY_UP, KEY_DOWN] and self.focus_w != self.choice:
            pass
        elif key == KEY_ENTER:
            self.focus_w = self.choice
            self.parent.change_focus(self.items[self.choice])
            self.signal("changed")
        elif key == KEY_TAB:
            if self.focus_w is None:
                self.focus_w = self.choice
                self.parent.change_focus(self.items[self.choice])
                return

            if self.choice < len(self.items) - 1:
                self.move_sel(1)
                self.focus_w = self.choice
                self.parent.change_focus(self.items[self.choice])
                self.parent.redraw()
            else:
                return self.parent_handle_key(key)
        elif key == KEY_SHIFT_TAB:
            if self.focus_w is None:
                self.focus_w = self.choice
                self.parent.change_focus(self.items[self.choice])
                return

            if self.choice > 0:
                self.move_sel(-1)
                self.focus_w = self.choice
                self.parent.change_focus(self.items[self.choice])
                self.parent.redraw()
        else:
            return self.parent_handle_key(key)

    def find_focusable_by_xy(self, x, y):
        # override Dialog.find_focusable_by_xy()
        # do NOT return instances of WPager
        i = 0
        for w in self.parent.childs:
            if isinstance(w, FocusableWidget) and w.inside(x, y):
                # TODO - add a check here for changing WPager's focus to the clicked child
                if not isinstance(w, WPager):
                    return i, w
            i += 1
        return None, None

    def handle_mouse(self, x, y):
        # TODO - handle clicks on the up/down arrows?
        # Work in absolute coordinates
        if self.inside(x, y):
            self.focus_idx, w = self.find_focusable_by_xy(x, y)
            if w:
                self.parent.change_focus(w)
                return w.handle_mouse(x, y)


class EP_WATCHED(Enum):
    SKIP = 0
    AIRED = 1
    DATE = 2


class WEpisodeWidget(ItemSelWidget):
    """
    Custom widget to display choosing when an episode was watched.
    """

    def __init__(self, ep):
        self.ep = ep
        self.header = [
            f"Episode {self.ep.number} ({self.ep.first_aired_date})",
            f"Title: {self.ep.title}",
        ]
        items = [
            "Skipped",
            "Watched on Air Date",
            "Input Date",
        ]
        super().__init__(items)
        self.h = 5
        self.w = max(
            max(len(s) for s in self.header),
            6 + max(len(s) for s in items),
        )
        self.focus = False

    def redraw(self):
        i = 0
        if self.focus:
            self.attr_color(C_B_BLUE, None)
        self.goto(self.x, self.y)
        self.wr(f"Episode {self.ep.number} ({self.ep.first_aired_date})")
        self.goto(self.x, self.y + 1)
        self.wr(f"Title: {self.ep.title}")
        for t in self.items:
            self.goto(self.x, self.y + i + 2)
            self.wr("  (*) " if self.choice == i else "  ( ) ")
            self.wr(t)
            i += 1
        self.attr_reset()

    def handle_mouse(self, x, y):
        if self.y + 1 < y < self.y + self.h:
            self.choice = y - self.y - 2
            self.redraw()
            self.signal("changed")

    def handle_key(self, key):
        if key == KEY_UP:
            self.move_sel(-1)
        elif key == KEY_DOWN:
            self.move_sel(1)
        elif key == KEY_ENTER:
            # ?
            return ACTION_OK
