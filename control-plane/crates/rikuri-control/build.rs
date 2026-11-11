//! Embeds the setup pages' build (`ui/dist`, made by `scripts/quality/ui.sh
//! build`) in the binary as a fixed table of files (D23): no request can
//! reach the disk, and the pages and the API they call cannot be out of step.
//! The build fails if the pages are missing or a file is of a type the table
//! does not know, so every build embeds them, tests included.
//!
//! The UI's folder is `RIKURI_UI_DIR` when set (an absolute path: the copy
//! of control-plane/ that cargo-mutants builds is not beside ui/), else the
//! repository's `ui/`.
//! Record: docs/build-records/2026-11-11-5c3a-ui-pipeline.md

#![allow(clippy::print_stdout)] // cargo reads a build script's directives from its stdout

use std::env;
use std::fmt::Write as _;
use std::fs;
use std::path::{Path, PathBuf};

/// Every file the build must hold, as served.
const REQUIRED: [&str; 4] = ["/cert.html", "/favicon.svg", "/index.html", "/licenses.txt"];

fn content_type(path: &str) -> Option<&'static str> {
    let ext = path.rsplit_once('.').map(|(_, e)| e)?;
    Some(match ext {
        "html" => "text/html; charset=utf-8",
        "js" => "text/javascript; charset=utf-8",
        "css" => "text/css; charset=utf-8",
        "woff2" => "font/woff2",
        "svg" => "image/svg+xml",
        "txt" => "text/plain; charset=utf-8",
        _ => return None,
    })
}

fn walk(dir: &Path, base: &Path, out: &mut Vec<(String, PathBuf)>) {
    let entries =
        fs::read_dir(dir).unwrap_or_else(|e| panic!("cannot read {}: {e}", dir.display()));
    for entry in entries {
        let path = entry
            .unwrap_or_else(|e| panic!("cannot read {}: {e}", dir.display()))
            .path();
        let kind = fs::symlink_metadata(&path)
            .unwrap_or_else(|e| panic!("cannot read {}: {e}", path.display()))
            .file_type();
        if kind.is_symlink() {
            panic!(
                "{}: a link in the UI's build; only plain files are embedded",
                path.display()
            );
        } else if kind.is_dir() {
            walk(&path, base, out);
        } else {
            let rel = path
                .strip_prefix(base)
                .unwrap_or_else(|e| panic!("{}: {e}", path.display()));
            let served = rel
                .components()
                .map(|c| {
                    c.as_os_str()
                        .to_str()
                        .unwrap_or_else(|| panic!("{}: a name that is not UTF-8", path.display()))
                })
                .fold(String::new(), |acc, c| acc + "/" + c);
            out.push((served, path));
        }
    }
}

fn main() {
    println!("cargo:rerun-if-env-changed=RIKURI_UI_DIR");
    let manifest = PathBuf::from(
        env::var("CARGO_MANIFEST_DIR").unwrap_or_else(|e| panic!("CARGO_MANIFEST_DIR: {e}")),
    );
    let ui = match env::var_os("RIKURI_UI_DIR") {
        Some(dir) => PathBuf::from(dir),
        None => manifest.join("../../../ui"),
    };
    let ui = fs::canonicalize(&ui).unwrap_or_else(|e| {
        panic!(
            "the UI's folder {}: {e} (set RIKURI_UI_DIR, or build from the repository)",
            ui.display()
        )
    });
    let dist = ui.join("dist");
    println!("cargo:rerun-if-changed={}", dist.display());
    println!("cargo:rustc-env=RIKURI_UI_DIR={}", ui.display());

    let mut files = Vec::new();
    if dist.is_dir() {
        walk(&dist, &dist, &mut files);
    }
    files.sort();
    for needed in REQUIRED {
        assert!(
            files.iter().any(|(served, _)| served == needed),
            "{needed} is not in {}: build the UI first (scripts/quality/ui.sh build)",
            dist.display()
        );
    }

    let mut table = String::from("pub(crate) static FILES: &[UiFile] = &[\n");
    for (served, path) in &files {
        let ctype = content_type(served).unwrap_or_else(|| {
            panic!("{served}: a file type the setup pages' table does not know")
        });
        let path = path
            .to_str()
            .unwrap_or_else(|| panic!("{}: a path that is not UTF-8", path.display()));
        writeln!(
            table,
            "    UiFile {{ path: {served:?}, content_type: {ctype:?}, body: include_bytes!({path:?}) }},"
        )
        .unwrap_or_else(|e| panic!("{e}"));
    }
    table.push_str("];\n");
    let out = PathBuf::from(env::var("OUT_DIR").unwrap_or_else(|e| panic!("OUT_DIR: {e}")));
    fs::write(out.join("ui_files.rs"), table).unwrap_or_else(|e| panic!("ui_files.rs: {e}"));
}
