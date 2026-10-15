//! The stack benchmark's Rust port (TASK-045; the port brief, revision 2): the bootstrap governor's acceptance
//! decision (`governor.evaluate`), the Resume Check (`resume_check.check`), the record forms they use from
//! records.py and the canonical text of `conformance.canonical_text`, computed over the fixture document.
//!
//! It reads only the bytes it is given, writes nothing, and reads no clock, random value, environment or network.

mod document;
mod governor;
mod json;
mod records;
mod resume_check;
mod sha256;

pub mod eventlog;
pub mod pyval;
pub mod records2;
pub mod recovery;
pub mod round2;

pub use document::{
    case_records, document, placeholder, read_fixture_document, GOVERNOR_FOLDER, RC_FOLDER,
};
pub use governor::evaluate;
pub use json::{canon, canonical_text, parse, py_eq, Int, Json};
pub use records::check_record;
pub use resume_check::{check, check_with, meet, PLACEHOLDER};

pub const USAGE: &str = "usage: port <fixture document>";

/// The one argument, or the usage text when there is not exactly one.
pub fn the_argument(args: &[String]) -> Result<&str, String> {
    match args {
        [one] => Ok(one.as_str()),
        _ => Err(USAGE.to_string()),
    }
}

/// The whole run but the read of the file and the write: the arguments (without the program name), the reader of
/// the one path, and the document's bytes, or why there is none.
pub fn run(
    args: &[String],
    read: &dyn Fn(&str) -> Result<Vec<u8>, String>,
) -> Result<Vec<u8>, String> {
    let path = the_argument(args)?;
    let data = read(path)?;
    document(&data)
}
