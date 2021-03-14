#! /usr/bin/env python3

"""
This file is required for this script to run:
fname = "./tv-shows-by-date-full.txt"
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
"""

import re
import os


fname = "./tv-shows-by-date-full.txt"


def find_movies(limit=0):
    year = 0

    if not os.path.exists(fname):
        raise Exception("Read docstring for txt_tv_parser.py")

    counter = 0
    with open(fname) as f:
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
