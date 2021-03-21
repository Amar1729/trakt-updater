#! /usr/bin/env python3

"""
1. select watched tv shows from list (e.g. copied from list of all tv shows aired in a time period)

This file is required for this script to run:
FNAME = "wikipedia-tv-shows.txt"
# content copied from:
# (can just ctrl-a and copy all of it, then delete first few/last few lines)
# https://en.wikipedia.org/wiki/List_of_American_television_programs_by_debut_date

# format of the file should look something like:

```
2010
January

    January 3 – Frank the Entertainer in a Basement Affair
    January 3 – Worst Cooks in America

February

    Feb n - ...

2011
January

    January n - ...
```

# this script parses the output and yields each line one at a time, prefixed by its release year
# e.g.
# 2001 - January 12 - some tv show name

2. return list of watched tv shows
requires:
SELECTED = "shows.txt"
"""

import re
import os


FNAME = "wikipedia-tv-shows.txt"
SELECTED = "shows.txt"


def get_selected():
    with open(SELECTED) as f:
        for line in f.readlines():
            if line.strip():
                if chr(8211) in line:
                    # wikipedia has unicode characters similar to hyphens: '–'
                    show = line.strip().split(chr(8211))[1].strip()
                    yield show
                else:
                    yield line.strip()


def find_movies(limit=0):
    year = 0

    if not os.path.exists(FNAME):
        raise Exception("Read docstring for txt_tv_parser.py")

    counter = 0
    with open(FNAME) as f:
        for line in f.readlines():
            if not line.strip():
                pass
            elif re.match(r"[0-9]*$", line.strip()):
                year = int(line.strip())
            elif re.match(r"[A-Za-z]*$", line.strip()):
                pass
            else:
                counter += 1
                yield f"{year} - {line.strip()}"
                if limit > 0 and counter >= limit:
                    return


if __name__ == "__main__":
    for mov in find_movies(limit=1):
        print(mov)
