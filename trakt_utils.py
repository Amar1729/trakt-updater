#! /usr/bin/env python3

"""
Update your trakt movie or tv watchlist.
Searches for movies on trakt from ./movies.txt (one movie name per line)
or tv shows from ./show.txt (expects a line format like:
SXX - TV show name
)

(The SXX season specifier is helpful for you to choose the correct
season when there are multiple seasons on trakt)

Expects config.ini in the same directory of the folowing format:

---- config.ini
[user]
username = your-usename

[app]
id = client-id-from-trakt-app
sec = client-secret-from-trakt-app
token = optional
----

If you do not have a token yet, this script will generate one and update
config.ini the first time you run it.
"""

import configparser
import datetime
import functools
import os
import pickle

# watch out for rate limits!
# https://trakt.docs.apiary.io/#introduction/rate-limiting
import time
import sys

from pprint import pprint
from typing import Optional

# third-party
import trakt
import trakt.core
import trakt.movies
import trakt.tv
import tqdm


# use a manual offset, since trakt module incorrectly uses utc time instead of local time
OFFSET = time.timezone


def get_config():
    cfg = configparser.ConfigParser()
    cfg.read("config.ini")
    return cfg


def update_config(cfg, trakt):
    app = {
        "id": trakt.core.CLIENT_ID,
        "sec": trakt.core.CLIENT_SECRET,
        "token": trakt.core.OAUTH_TOKEN,
    }

    cfg.update({"app": app})

    with open("config.ini", "w") as cfgfile:
        cfg.write(cfgfile)


def auth_trakt():
    cfg = get_config()

    try:
        trakt.core.CLIENT_ID = cfg["app"]["id"]
        trakt.core.CLIENT_SECRET = cfg["app"]["sec"]
        trakt.core.OAUTH_TOKEN = cfg["app"]["token"]
    except KeyError:
        username = cfg["user"]["username"]

        trakt.core.AUTH_METHOD = trakt.core.OAUTH_AUTH
        trakt.init(username)

        update_config(cfg, trakt)


# ----
# helpers for interface.py


def bad_serializer(d):
    """
    use `pickle` to serialize episodes into a file for later updating trakt all at once
    this seems like bad style, just be careful with your pickle files!
    """
    pf = "serialized.pickle"
    od = []
    if os.path.exists(pf):
        with open(pf, "rb") as f:
            od = pickle.load(f)
    od.append(d)
    with open(pf, "wb") as f:
        pickle.dump(od, f)


def read_serialized():
    pf = "serialized.pickle"
    if not os.path.exists(pf):
        raise Exception("Serialized file does not exist yet. Run a deferred update first.")

    with open(pf, "rb") as f:
        for res in pickle.load(f):
            yield res


def display_seasons(seasons):
    for season in seasons:
        try:
            yield f"Season {season.number} ({season.first_aired.split('-')[0]})"
            yield f"  {season.title} - {season.episode_count} episodes"
        except:
            yield ""


@functools.lru_cache
def search_tv(query):
    auth_trakt()  # ?

    query = query.replace("'", "")
    results = trakt.movies.search(query, search_type="show")
    return [
        dict([
            ("year", r.year),
            ("title", r.title),
            ("seasons", r.seasons),
        ])
        for r in results
    ]


def search_tv_episodes(season):
    pass


def non_interactive_episode_add(episode, date_obj):
    assert isinstance(episode, trakt.tv.TVEpisode)
    # python trakt is doing non-timezone aware datetimes
    date_obj = date_obj + datetime.timedelta(seconds=OFFSET)
    trakt.sync.add_to_history(episode, watched_at=date_obj)

    # rate limit: 2 POST calls every 1 sec
    time.sleep(1)

# ----


def movie_releases(media: trakt.movies.Movie) -> str:
    return "\n".join([
        f"{c+1} ({m.release_type}): {m.release_date}"
        for c, m in enumerate(media.get_releases())
    ])


def date_chooser(media, media_type) -> Optional[datetime.datetime]:
    if media_type == "movie":
        print("Releases:")
        print(movie_releases(media))

    # print("Enter the date (DD/MM/YY) you watched it (default: today): ")
    print("Enter the date (<month abbreviation> DD YY) you watched it.")
    print("Or, 0 for today, or a whole number matching its release date, or -1 to skip.")
    date_str = input().strip()

    try:
        idx = int(date_str)

        if idx == 0:
            date_obj = datetime.datetime.now()
        elif idx == -1:
            return None
        else:
            date_obj = datetime.datetime.strptime(
                media.get_releases()[idx - 1].release_date, "%Y-%m-%d"
            )
    except ValueError:
        try:
            # date_obj = datetime.datetime.strptime(date_str.strip(), "%d/%m/%y")
            date_obj = datetime.datetime.strptime(date_str.strip(), "%b %d %y")
        except ValueError as e:
            print("Date does not match format: DD MM YY")
            print("Skipping this media")
            print(e)
            return None

    # python trakt is doing non-timezone aware datetimes
    date_obj = date_obj + datetime.timedelta(seconds=OFFSET)

    return date_obj


def add_media_interactive(title: str, media_type: str):
    """
    1) Search trakt.tv for a movie/tv with title.
    2) interactively ask user for selection
    3) update user's history with selection
    """
    if media_type == "show":
        # expects format 'S01 - tv show title'
        cleaned = " - ".join(title.split(" - ")[1:]).strip()
    else:
        cleaned = title
    # remove quotes from search query
    if cleaned.startswith("?"):
        return
    cleaned = cleaned.replace("'", "")
    results = trakt.movies.search(cleaned, search_type=media_type)

    print(f"Choose the matching result for '{title}' (or -1 to skip):")
    for idx, media in enumerate(results):
        print(f"{idx}: ({media.year})\t{media.title}")

    try:
        _choice = input()

        if _choice.strip() == "-1":
            return

        choice = int(_choice)
    except ValueError:
        if media_type == "show":
            print("Assuming manual input, searching...")
            cleaned = _choice.strip()
            results = trakt.movies.search(cleaned, search_type=media_type)
            print(f"Choose the matching result for '{title}':")
            for idx, media in enumerate(results):
                print(f"{idx}: ({media.year})\t{media.title}")

            try:
                choice = int(input())
            except ValueError:
                print("Skipping this media (input must be integer)")
                return
        else:
            print("Skipping this media (input must be integer)")
            return

    if media_type == "show":
        print("Choose the appropriate season:")
        for idx, season in enumerate(results[choice].seasons):
            print(f"{idx}: ({season.first_aired})\t{season.title}")

        try:
            season_choice = int(input())
        except ValueError:
            print("Skipping this media (input must be integer)")
            return

        media = results[choice].seasons[season_choice].episodes
    else:
        media = results[choice]

    date_obj = date_chooser(media, media_type)
    if not date_obj:
        return

    if media_type == "show" and isinstance(media, list):
        for episode in tqdm.tqdm(media):
            assert isinstance(episode, trakt.tv.TVEpisode)
            trakt.sync.add_to_history(episode, watched_at=date_obj)

            # rate limit: 2 POST calls every 1 sec
            time.sleep(1)

    elif isinstance(media, trakt.movies.Movie):
        trakt.sync.add_to_history(media, watched_at=date_obj)


def add_media_to_history(media_type):
    """ Add all media from {media_type}.txt to user's trakt.tv account """
    with open(f"{media_type}.txt") as f:
        medias = f.readlines()

    for media in medias:
        if media.strip().endswith(":"):
            continue
        add_media_interactive(media.strip(), media_type)


def main(media_type):
    auth_trakt()
    add_media_to_history(media_type)


if __name__ == "__main__":
    try:
        # media_type: 'show' or 'movie'
        media_type = sys.argv[1]
        assert media_type in ["show", "movie"]
    except IndexError:
        media_type = "movie"
        print("using default media_type: movie")
        print("if you would like to parse tv shows, use `python trakt_utils.py show`")
        print()
    except AssertionError:
        print("usage:")
        print("  python trakt_utils.py movie")
        print("  python trakt_utils.py show")
        sys.exit(1)

    main(media_type)
