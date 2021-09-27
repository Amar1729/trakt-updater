
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
    context: UserContext,
    items: StatefulList<(Show, bool)>,
}

impl<'a> App {
    fn new(context: UserContext, shows: Vec<Show>) -> App {
        let watched_shows: Vec<(Show, bool)> = shows
            .iter()
            // clone is a bit dirty but i dont fully understand rust borrowing + lifetimes yet :/
            .map(|s| { (s.clone(), context.get_seen(s.id)) })
            .collect();

        App {
            context: context,
            items: StatefulList::with_items(
                watched_shows
            ),
        }
    }

    fn toggle_watched(&mut self) {
        match self.items.state.selected() {
            Some(i) => {
                let new_status = !(&self.items.items[i].1);
                self.context.mark_seen(&self.items.items[i].0, new_status);
                self.items.items[i] = (self.items.items[i].0.clone(), new_status);
            }
            None => {},
        };
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

    let mut app = App::new(context, shows);

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
                            if i.1 { Span::raw("-> ") } else { Span::raw("") },
                            Span::raw(&i.0.name),
                            Span::raw(" - "),
                            Span::styled(
                                format!("{} seasons", i.0.seasons),
                                Style::default().add_modifier(Modifier::ITALIC),
                            ),
                            Span::raw(" - "),
                            Span::raw(format!("{}", i.0.first_air_date.date())),
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
                Key::Char(' ') => {
                    app.toggle_watched()
                }
                _ => {}
            }
            Event::Tick => {}
        }
    }

    Ok(())
}
