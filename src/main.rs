#[macro_use]
extern crate serde_derive;

mod cache;
mod user;

use std::env;

fn main() {
    // eventually, this could be loaded from a config file / interactively queried
    let api_key = env::var("TVDB_TOKEN").unwrap();

    let db_file = "db.sqlite";

    dbg!(&api_key);
    // cache::cache_feed(&api_key, &db_file);

    // next, ask users what shows they've seen ...
    // sort by release_date? or have a mode that allows input?

    let mut shows = cache::shows();
    shows.sort_by(|a, b| a.first_air_date.cmp(&b.first_air_date));

    for show in shows {
        // dbg!(show);
        user::ask_seen(db_file, &show);
    }
}
