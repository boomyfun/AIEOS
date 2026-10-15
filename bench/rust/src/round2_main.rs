//! The round-2 entry: `port2 <round-2 input document>` prints the whole document to standard output in one write and
//! exits 0; on any failure it prints nothing to standard output, names the reason on standard error and exits
//! non-zero (the error returned from main).

use std::io::Write;

fn read(path: &str) -> Result<Vec<u8>, String> {
    std::fs::read(path).map_err(|e| format!("cannot read {}: {}", path, e))
}

fn main() -> Result<(), String> {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let out = aieos_bench_port::round2::run(&args, &read)?;
    let mut stdout = std::io::stdout().lock();
    stdout
        .write_all(&out)
        .map_err(|e| format!("cannot write: {}", e))?;
    stdout.flush().map_err(|e| format!("cannot write: {}", e))
}
