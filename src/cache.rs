use std::fs;
use std::io::{BufRead, BufReader};
use std::{thread, time};

use chrono::{NaiveDate, NaiveDateTime};
use reqwest;
use serde_json::Value;
use sqlite;

// current daily feed formatted like: tv_series_ids_MM_DD_YYYY.json.gz
const TVDB_FEED: &str = "http://files.tmdb.org/p/exports/";
const TVDB_API: &str = "https://api.themoviedb.org/3/tv/";


#[derive(Clone, Debug, Deserialize)]
struct FeedItem {
    id: i32,
    original_name: String,
    popularity: f32,
}

#[derive(Debug)]
struct Tvdb {
    name: String,
    seasons: u64,
    // unix timestamp
    first_air_date: i64,
}

#[derive(Clone, Debug)]
pub struct Show {
    pub id: i64,
    pub name: String,
    pub original_name: String,
    pub seasons: u64,
    pub first_air_date: NaiveDateTime,
}

fn feed() -> Vec<FeedItem> {
    let filename = "./tv_series_ids_09_14_2021.json";
    let file = fs::File::open(filename).unwrap();
    let reader = BufReader::new(file);

    let mut items: Vec<FeedItem> = vec![];

    for line in reader.lines() {
        let line = line.unwrap();

        let item: FeedItem = serde_json::from_str(&line)
            .expect("bad format");

        items.push(item);
    }

    items
}

pub fn cache_feed(api_key: &str, db_file: &str) {
    // let conn = sqlite::open(":memory:").unwrap();
    let conn = sqlite::open(db_file).unwrap();

    let client = reqwest::blocking::Client::new();

    conn.execute(
        "CREATE TABLE IF NOT EXISTS feed (
            id              INTEGER PRIMARY KEY,
            original_name   TEXT NOT NULL,
            name            TEXT NOT NULL,
            seasons         INTEGER,
            first_air_date  INTEGER
            )",
    ).unwrap();

    let items = feed();

    for item in items {

        let mut stmt = conn
            .prepare("SELECT id FROM feed WHERE id = ?")
            .unwrap();

        stmt.bind(1, item.id as i64).unwrap();

        if let sqlite::State::Row = stmt.next().unwrap() {
            // println!("id = {} name = {}", stmt.read::<i64>(0).unwrap(), stmt.read::<String>(1).unwrap());
            println!("already inserted: id = {}", stmt.read::<i64>(0).unwrap());
        } else {
            // does api request
            if let Some(item_full) = tvdb_info(&client, item.id as u32, api_key) {
                let mut stmt = conn
                    .prepare("INSERT INTO feed (id, original_name, name, seasons, first_air_date) VALUES (?, ?, ?, ?, ?)")
                    .unwrap();

                stmt.bind(1, item.id as i64).unwrap();
                stmt.bind(2, item.original_name.as_str()).unwrap();
                stmt.bind(3, item_full.name.as_str()).unwrap();
                stmt.bind(4, item_full.seasons as i64).unwrap();
                stmt.bind(5, item_full.first_air_date).unwrap();

                stmt.next().unwrap();

                println!("inserted: id = {}", item.id);
            }

            // time sleep to prevent crashing api limit
            thread::sleep(time::Duration::from_secs(2));
        }
    }
}

fn parse_date(first_air_date: &str) -> NaiveDateTime {
    NaiveDate::parse_from_str(first_air_date, "%Y-%m-%d")
        .unwrap()
        .and_hms(0, 0, 0)
}

fn tvdb_info(client: &reqwest::blocking::Client, tv_id: u32, api_key: &str) -> Option<Tvdb> {
    let target = format!("{}{}?api_key={}", TVDB_API, tv_id, api_key);

    // let body = reqwest::blocking::get(target).unwrap();
    let body = client.get(target).send().unwrap();

    let res: Value = serde_json::from_str(&body.text().unwrap()).unwrap();

    let release_date;
    if let Some(first_air_date) = res["first_air_date"].as_str() {
        release_date = parse_date(first_air_date);
    } else {
        println!("No air date: {}", tv_id);
        return None;
    }

    let tvdb = Tvdb {
        name: res["name"].as_str().unwrap().to_owned(),
        seasons: res["number_of_seasons"].as_u64().unwrap(),
        first_air_date: release_date.timestamp(),
    };

    Some(tvdb)
}

pub fn shows() -> Vec<Show> {
    let conn = sqlite::open("db.sqlite").unwrap();

    let mut stmt = conn
        .prepare("SELECT * FROM feed")
        .unwrap();

    let mut shows: Vec<Show> = vec!();
    while let sqlite::State::Row = stmt.next().unwrap() {
        // println!("already inserted: id = {}", stmt.read::<i64>(0).unwrap());
        // .prepare("INSERT INTO feed (id, original_name, name, seasons, first_air_date) VALUES (?, ?, ?, ?, ?)")
        shows.push(Show {
            id: stmt.read::<i64>(0).unwrap(),
            original_name: stmt.read::<String>(1).unwrap(),
            name: stmt.read::<String>(2).unwrap(),
            seasons: stmt.read::<i64>(3).unwrap() as u64,
            first_air_date: NaiveDateTime::from_timestamp(stmt.read::<i64>(4).unwrap(), 0),
        });
    }

    shows
}
