# trakt updater

Note: current branch is undergoing a rewrite in Rust.

Python files are still in this directory, but rust codebase can be tested with:

```bash
$ TVDB_TOKEN="<api token here>" cargo run
```

Currently requires a token from http://themovie.db.org to start up.

----

See [`requirements.txt`](./requirements.txt) before running.

Update trakt.tv with batches of watched movies/tv shows. Typically useful when syncing all your past history into Trakt after first making an account.

In general, these scripts will:
- read from a local text file containing the name of one movie or tv show per line
- search for that media on trakt
- asks you to confirm the media after finding it on trakt
- asks you the date you watched it
- updates trakt with date watched

If necessary, you can mark media as being watched multiple times by adding them multiple times in your input text file, by removing lines as you run the script from the input text file and re-running it later, or by updating the web interface manually.

## trakt

To use the trakt API, you will need an API id and secret.

## movies

Movies are the simplest. I retrieved a list of movies from wikipedia+imdb and saved them (one title per line) into a text file `movies.txt`. Once that is done, simply run:

`python trakt_utils.py`

And the script will search for movies from your input file one-by-one via trakt.

## tv

TV shows are slightly more complicated. To update trakt with tv shows you have watched:

1. Populate a text file called `shows.txt` with one name of a tv show per line. This can be done by manually typing out tv shows you have watched after referencing tv aggregators like IMDB or TVDB. I filled this file out by copying the list of TV shows by release date [from wikipedia](https://en.wikipedia.org/wiki/List_of_American_television_programs_by_debut_date).
    1. Select watched TV shows - if you fill out a file named `wikipedia-tv-shows.txt` (with the expected format, see docstring for [`txt_tv_parser.py`](txt_tv_parser.py) for more info), then you can call `python interface.py` to bring up an interface to select the TV shows you have seen. This will output your selected shows to a `shows.txt` file for later ingestion.
3. Once you have `shows.txt`, you can call `python interface.py` and select `update trakt`. The interface will guide you through selections of tv shows, seasons, and their episodes for each line in `shows.txt`.

Optional:
If you have been keeping track of tv shows you have watched before creating a trakt account, there is additional functionality for ingesting that information as well. In general, you can fill out a file `shows-structured.txt` with lines like this:
```
name of tv show ::: season-number ::: YYYY/MM/DD
```

Then call `python interface.py` > `update trakt` > `Run trakt updates from shows-structured.txt`. This functionality is meant for quicker updates for a batches of tv shows.
