
/// store information about what the user has seen
/// eventually, issue updates to trakt.tv

use std::collections::HashMap;
use std::io;

use sqlite;

use crate::cache::Show;

struct TvUser {
    id: u32,
    watched: bool,
    trakt_updated: bool,
}

/// mark a tv_id as seen in our local database
/// skip operation if show's already marked in db
pub fn ask_seen(db: &str, show: &Show) {
    let conn = sqlite::open(db).unwrap();

    let mut stmt = conn
        .prepare("SELECT id FROM user WHERE id = ?")
        .unwrap();

    stmt.bind(1, show.id as i64).unwrap();

    if let sqlite::State::Row = stmt.next().unwrap() {
        return;
    }

    println!("Watched ? ({} / {}) [Y/n] ", show.name, show.first_air_date);

    let inp = &mut String::new();
    inp.clear();
    let _ = io::stdin().read_line(inp);

    let watched;
    match inp.trim() {
        "" => watched = true,
        "y" => watched = true,
        _ => watched = false,
    }

    conn.execute(
        "CREATE TABLE if not exists user (
            id          INTEGER PRIMARY KEY,
            watched     INTEGER
            )"
    ).unwrap();

    let mut stmt = conn
        .prepare("INSERT INTO user (id, watched) VALUES (?, ?)")
        .unwrap();

    stmt.bind(1, show.id as i64).unwrap();
    stmt.bind(2, watched as i64).unwrap();

    stmt.next().unwrap();
}
