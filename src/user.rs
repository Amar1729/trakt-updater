
/// store information about what the user has seen
/// eventually, issue updates to trakt.tv

use std::collections::HashMap;
use std::io;

use sqlite;

use std::time::{Duration, Instant};

use termion::{event::Key, input::MouseTerminal, raw::IntoRawMode, screen::AlternateScreen};
use tui::{
    // backend::CrosstermBackend,
    backend::TermionBackend,
    layout::{Alignment, Constraint, Direction, Layout},
    style::{Color, Modifier, Style},
    text::{Span, Spans},
    widgets::{
        Block, BorderType, Borders, Cell, List, ListItem, ListState, Paragraph, Row, Table, Tabs,
    },
    Terminal,
};

use crate::cache::Show;
use crate::util::{
    event::{Event, Events},
    StatefulList,
};

struct TvUser {
    id: u32,
    watched: bool,
    trakt_updated: bool,
}

struct UserContext {
    conn: sqlite::Connection,
}

impl UserContext {
    fn new(db: &str) -> UserContext {
        let conn = sqlite::open(db).unwrap();

        conn.execute(
            "CREATE TABLE if not exists user (
                id          INTEGER PRIMARY KEY,
                watched     INTEGER
                )"
        ).unwrap();

        UserContext {
            conn: conn,
        }
    }

    fn mark_seen(&self, show: &Show, watched: bool) {
        let mut stmt = self.conn
            .prepare("SELECT id FROM user WHERE id = ?")
            .unwrap();

        stmt.bind(1, show.id as i64).unwrap();

        if let sqlite::State::Row = stmt.next().unwrap() {
            return;
        }

        let mut stmt = self.conn
            .prepare("INSERT INTO user (id, watched) VALUES (?, ?)")
            .unwrap();

        stmt.bind(1, show.id as i64).unwrap();
        stmt.bind(2, watched as i64).unwrap();

        stmt.next().unwrap();
    }
}

struct App {
    items: StatefulList<Show>,
}

impl<'a> App {
    fn new(shows: Vec<Show>) -> App {
        App {
            items: StatefulList::with_items(shows),
        }
    }
}

/// tui for marking shows as seen
pub fn interface(db: &str, shows: Vec<Show>) -> Result<(), Box<dyn std::error::Error>> {
    let mut context = UserContext::new(db);

    let stdout = io::stdout().into_raw_mode()?;
    let stdout = MouseTerminal::from(stdout);
    let stdout = AlternateScreen::from(stdout);
    let backend = TermionBackend::new(stdout);
    let mut terminal = Terminal::new(backend)?;

    let tick_rate = Duration::from_millis(200);
    let events = Events::new(tick_rate);

    let mut app = App::new(shows);

    loop {
        terminal.draw(|rect| {
            let size = rect.size();
            let chunks = Layout::default()
                .direction(Direction::Vertical)
                .margin(2)
                .constraints(
                    [
                        Constraint::Min(2),
                    ]
                    .as_ref(),
                )
                .split(size);

            let items: Vec<ListItem> = app
                .items
                .items
                .iter()
                .map(|i| {
                    ListItem::new(
                        Spans::from(vec![
                            Span::raw(&i.original_name),
                            Span::raw(" - "),
                            Span::styled(
                                format!("{} seasons", i.seasons),
                                Style::default().add_modifier(Modifier::ITALIC),
                            ),
                            Span::raw(" - "),
                            Span::raw(format!("{}", i.first_air_date)),
                        ])
                    )
                        .style(Style::default().fg(Color::White))
                })
                .collect();

            let items = List::new(items)
                .block(Block::default().borders(Borders::ALL).title("TV Shows"))
                .highlight_style(
                    Style::default()
                        .bg(Color::LightGreen)
                        .add_modifier(Modifier::BOLD),
                )
                .highlight_symbol(">> ");

            rect.render_stateful_widget(items, chunks[0], &mut app.items.state);
            // rect.render_widget(render_shows(&shows), chunks[1])
        })?;

        match events.next()? {
            Event::Input(event) => match event {
                Key::Char('q') => {
                    // disable_raw_mode()?;
                    // terminal.show_cursor()?;
                    break;
                }
                Key::Down => {
                    app.items.next()
                }
                Key::Up => {
                    app.items.previous()
                }
                _ => {}
            }
            Event::Tick => {}
        }
    }

    Ok(())
}
