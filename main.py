#! /usr/bin/env python3

import configparser
import datetime

from pprint import pprint

# third-party
import trakt
import trakt.core
import trakt.movies


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


def add_movie_interactive(movie_title: str):
    """
    1) Search trakt.tv for a movie with movie_title.
    2) interactively ask user for selection
    3) update user's history with selection
    """
    results = trakt.movies.search(movie_title)

    print(f"Choose the matching result for '{movie_title}':")
    for idx, movie in enumerate(results):
        print(f"{idx}: ({movie.year})\t{movie.title}")

    try:
        choice = int(input())
    except ValueError:
        print("Skipping this movie (input must be integer)")
        return

    # print("Enter the date (DD/MM/YY) you watched it (default: today): ")
    print("Enter the date (<month abbreviation> DD YY) you watched it (default: today): ")
    date_str = input()

    if not date_str.strip():
        date_obj = datetime.datetime.now()
    else:
        try:
            # date_obj = datetime.datetime.strptime(date_str.strip(), "%d/%m/%y")
            date_obj = datetime.datetime.strptime(date_str.strip(), "%b %d %y")
        except ValueError as e:
            print("Date does not match format: DD/MM/YY")
            print("Skipping this movie")
            print(e)
            return

    date_obj = date_obj + datetime.timedelta(hours=5)

    movie = results[choice]
    trakt.sync.add_to_history(movie, watched_at=date_obj)


def add_tv_interactive(tv_title: str):
    """
    Similar to process for add_movies_to_history()
    """
    results = trakt.tv.search(tv_title)


def add_movies_to_history():
    """ Add all movies from movies.txt to user's trakt.tv account """
    with open("movies.txt") as f:
        movies = f.readlines()

    for movie in movies:
        add_movie_interactive(movie.strip())


def add_tvs_to_history():
    """ Add all tv shows from tv.txt to user's trakt.tv account """
    with open("tv.txt") as f:
        tvs = f.readlines()

    for tv in tvs:
        add_tv_interactive(tv.strip())


def main():
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

    # add_movies_to_history()
    add_tvs_to_history()


if __name__ == "__main__":
    main()
