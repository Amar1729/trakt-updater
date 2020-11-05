#! /usr/bin/env python3

import configparser
import datetime

from pprint import pprint

# third-party
import trakt
import trakt.core
import trakt.movies
import trakt.tv


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


def add_media_interactive(title: str, media_type: str):
    """
    1) Search trakt.tv for a movie/tv with title.
    2) interactively ask user for selection
    3) update user's history with selection
    """
    if media_type == "show":
        cleaned = " - ".join(title.split(" - ")[1:]).strip()
    else:
        cleaned = title
    results = trakt.movies.search(cleaned, search_type=media_type)

    print(f"Choose the matching result for '{title}':")
    for idx, media in enumerate(results):
        print(f"{idx}: ({media.year})\t{media.title}")

    try:
        _choice = input()
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
            print("Skipping this media")
            print(e)
            return

    # python trakt is doing non-timezone aware datetimes
    date_obj = date_obj + datetime.timedelta(hours=5)

    if media_type == "show" and isinstance(media, list):
        for episode in tqdm.tqdm(media):
            assert isinstance(episode, trakt.tv.TVEpisode)
            trakt.sync.add_to_history(episode, watched_at=date_obj)

    elif isinstance(media, trakt.movies.Movie):
        trakt.sync.add_to_history(media, watched_at=date_obj)


def add_media_to_history(media_type):
    """ Add all media from {media_type}.txt to user's trakt.tv account """
    with open(f"{media_type}.txt") as f:
        medias = f.readlines()

    for media in medias:
        add_media_interactive(media.strip(), media_type)


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

    media_type = "show"  # or "movie"
    add_media_to_history(media_type)


if __name__ == "__main__":
    main()
