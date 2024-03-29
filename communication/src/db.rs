use crate::AddAnnouncement;
use crate::AskQuestion;
use actix_web::error::ErrorInternalServerError;
use actix_web::web;
use anyhow::Result;
use r2d2_sqlite::SqliteConnectionManager;
use rusqlite::params;
use rusqlite::Row;
use serde::Serialize;
use std::path::Path;

pub type Pool = r2d2::Pool<r2d2_sqlite::SqliteConnectionManager>;
pub type ResultQuery<T> = std::result::Result<T, actix_web::Error>;

/// The schema of the database, executed at start to setup the tables.
const SCHEMA: &str = include_str!("../schema.sql");

/// Connect to the sqlite database at the provided path and return a connection
/// pool to it.
pub fn connect<P: AsRef<Path>>(path: P) -> Result<Pool> {
    let manager =
        SqliteConnectionManager::file(path.as_ref()).with_init(|c| c.execute_batch(SCHEMA));
    Pool::new(manager).map_err(|e| e.into())
}

/// Information about an annoucement in the database, containing only the
/// public information (i.e. not the token of the admin that posted it)
#[derive(Debug, Serialize)]
pub struct Announcement {
    /// Identifier of the announcement.
    pub id: i64,
    /// Severity of the announcement (i.e. its color using the bootstrap class
    /// names, e.g. danger, warning, success, info, primary, ...)
    pub severity: String,
    /// Title of the announcement.
    pub title: String,
    /// Content of the announcement, in Markdown.
    pub content: String,
    /// Date of the announcement, in UTC using the "SQL" date format
    /// (YYYY-MM-DD hh:mm:ss).
    pub date: String,
}

/// Fetch the list with all the announcements in the database, sorted by date.
pub async fn list_announcements(pool: &Pool) -> ResultQuery<Vec<Announcement>> {
    let conn = pool.get();
    web::block(move || -> Result<_> {
        let conn = conn?;
        let mut stmt = conn.prepare(
            "
            SELECT id, severity, title, content, date
            FROM announcements
            ORDER BY date",
        )?;
        stmt.query_map([], |row| {
            Ok(Announcement {
                id: row.get(0)?,
                severity: row.get(1)?,
                title: row.get(2)?,
                content: row.get(3)?,
                date: row.get(4)?,
            })
        })
        .and_then(Iterator::collect)
        .map_err(|e| e.into())
    })
    .await?
    .map_err(ErrorInternalServerError)
}

/// Information about the answer to a question. Only public information is
/// listed here (i.e. not the admin token that answered the question).
#[derive(Debug, Serialize, Clone)]
pub struct Answer {
    /// Date of the answer, in SQL format in UTC.
    pub date: String,
    /// Content of the answer, in Markdown.
    pub content: String,
}

/// Information about a question from a contestant.
#[derive(Debug, Serialize, Clone)]
pub struct Question {
    /// The identifier of the question.
    pub id: i64,
    /// The username of the user asking the question.
    pub creator: String,
    /// Text written by the contestant, not in Markdown.
    pub content: String,
    /// Date of the question, in SQL format in UTC.
    pub date: String,
    /// The answer from an admin, if any.
    pub answer: Option<Answer>,
}

impl Question {
    /// Build a question from a properly executed query. The columns should be:
    /// id, content, date, answer, answerDate
    fn from_row(row: &Row) -> rusqlite::Result<Question> {
        Ok(Question {
            id: row.get(0)?,
            creator: row.get(1)?,
            content: row.get(2)?,
            date: row.get(3)?,
            answer: row.get::<_, Option<String>>(4)?.map(|_| Answer {
                content: row.get(4).unwrap(),
                date: row.get(5).unwrap(),
            }),
        })
    }
}

/// List all the questions from `token`. If `token` is an admin, all the
/// questions are returned.
pub async fn questions(pool: &Pool, token: String) -> ResultQuery<Vec<Question>> {
    let admin = is_admin(pool, token.clone()).await?;
    let conn = pool.get();
    web::block(move || -> Result<_> {
        let conn = conn?;
        let mut stmt = conn.prepare(
            "
            SELECT id, creator, content, date, answer, answerDate
            FROM questions
            WHERE creator = ?1 OR ?2
            ORDER BY date",
        )?;
        stmt.query_map(params![token, admin], Question::from_row)
            .and_then(Iterator::collect)
            .map_err(|e| e.into())
    })
    .await?
    .map_err(ErrorInternalServerError)
}

/// Add a new question in the database.
pub async fn add_question(
    pool: &Pool,
    token: String,
    question: AskQuestion,
) -> ResultQuery<Question> {
    let conn = pool.get();
    web::block(move || -> Result<_> {
        let conn = conn?;
        let mut stmt = conn.prepare(
            "
            INSERT INTO
                questions (content, creator)
            VALUES
                (?1, ?2)",
        )?;
        let id = stmt.insert(params![question.content, token])?;
        let mut stmt = conn.prepare(
            "
            SELECT id, creator, content, date, answer, answerDate
            FROM questions
            WHERE id = ?1
            ORDER BY date",
        )?;
        let mut q = stmt.query_map(params![id], Question::from_row)?;
        Ok(q.next().unwrap()?)
    })
    .await?
    .map_err(ErrorInternalServerError)
}

/// Add a new announcement to the database. It is not checked that the token of
/// the poster is not an admin.
pub async fn add_announcement(pool: &Pool, announcement: AddAnnouncement) -> ResultQuery<()> {
    let conn = pool.get();
    web::block(move || -> Result<_> {
        let conn = conn?;
        let mut stmt = conn.prepare(
            "
            INSERT INTO
                announcements (severity, title, content, creator)
            VALUES
                (?1, ?2, ?3, ?4)",
        )?;
        stmt.insert(params![
            announcement.severity,
            announcement.title,
            announcement.content,
            announcement.token
        ])?;
        Ok(())
    })
    .await?
    .map_err(ErrorInternalServerError)
}

/// Checks if the `token` is an admin. If the token does not exists `false` is
/// returned.
pub async fn is_admin(pool: &Pool, token: String) -> ResultQuery<bool> {
    let conn = pool.get();
    web::block(move || -> Result<_> {
        let conn = conn?;
        let mut stmt = conn.prepare(
            "
            SELECT isAdmin
            FROM users
            WHERE token = ?1",
        )?;
        let mut res = stmt.query_map(params![token], |row| Ok(row.get::<_, i32>(0)? == 1))?;
        let admin = match res.next() {
            Some(Ok(admin)) => admin,
            _ => false,
        };
        if res.next().is_some() {
            return Ok(false);
        }

        Ok(admin)
    })
    .await?
    .map_err(ErrorInternalServerError)
}

/// Post the answer of a question, overwriting the previous answer, if any.
pub async fn answer_question(
    pool: &Pool,
    token: String,
    id: i64,
    answer: String,
) -> ResultQuery<bool> {
    let conn = pool.get();
    web::block(move || -> Result<_> {
        let conn = conn?;
        let mut stmt = conn.prepare(
            "
            UPDATE
                questions
            SET
                answer = ?1,
                answerDate = CURRENT_TIMESTAMP,
                answerer = ?2
            WHERE
                id = ?3",
        )?;
        let res = stmt.execute(params![answer, token, id])?;
        Ok(res == 1)
    })
    .await?
    .map_err(ErrorInternalServerError)
}
