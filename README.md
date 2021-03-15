# trakt updater

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

To use the trakt API, you will need an API key and secret.

## movies

Movies are the simplest. I retrieved a list of movies from wikipedia+imdb and saved them (one title per line) into a text file `movies.txt`. Once that is done, simply run:

`python trakt_utils.py`

And the script will search for movies from your input file one-by-one via trakt.

## tv

<todo>
