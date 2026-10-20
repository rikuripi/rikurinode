//! The control plane's state folder: a 0700 folder of 0600 files, each written
//! whole by temporary file and rename (SEC-03), so a reader sees the old file
//! or the new one and never a half. Secrets live only here, referenced by
//! path (SEC-02): the node's keys, the hashes of the claim code and the
//! password, the sessions.

use std::fmt;
use std::fs::{self, OpenOptions};
use std::io::{self, Write};
use std::os::unix::fs::{OpenOptionsExt, PermissionsExt};
use std::path::{Path, PathBuf};

use serde::Serialize;
use serde::de::DeserializeOwned;

/// The environment variable that names the folder.
pub const ENV: &str = "RIKURI_STATE_DIR";
/// Where the daemon keeps its state when [`ENV`] is unset: under `/var`, which
/// an image update never touches (plan §4.1).
pub const DEFAULT: &str = "/var/lib/rikuri/control-plane";

const DIR_MODE: u32 = 0o700;
const FILE_MODE: u32 = 0o600;

#[derive(Debug, Clone)]
pub struct StateDir {
    root: PathBuf,
}

#[derive(Debug)]
pub enum StateError {
    Io {
        path: PathBuf,
        source: io::Error,
    },
    Json {
        path: PathBuf,
        source: serde_json::Error,
    },
}

impl fmt::Display for StateError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            StateError::Io { path, source } => write!(f, "{}: {source}", path.display()),
            StateError::Json { path, source } => {
                write!(f, "{}: not the expected JSON: {source}", path.display())
            }
        }
    }
}

impl std::error::Error for StateError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match self {
            StateError::Io { source, .. } => Some(source),
            StateError::Json { source, .. } => Some(source),
        }
    }
}

fn io_error(path: &Path, source: io::Error) -> StateError {
    StateError::Io {
        path: path.to_path_buf(),
        source,
    }
}

impl StateDir {
    /// Opens `root`, creating it if missing, and sets it to 0700 either way:
    /// a folder other users could read holds nothing this one keeps.
    pub fn open(root: impl Into<PathBuf>) -> Result<Self, StateError> {
        let root = root.into();
        fs::create_dir_all(&root).map_err(|e| io_error(&root, e))?;
        fs::set_permissions(&root, fs::Permissions::from_mode(DIR_MODE))
            .map_err(|e| io_error(&root, e))?;
        Ok(Self { root })
    }

    pub fn root(&self) -> &Path {
        &self.root
    }

    /// The path of `name`, a plain file name inside the folder.
    pub fn path(&self, name: &str) -> PathBuf {
        debug_assert!(!name.contains('/'), "a state file is a plain name");
        self.root.join(name)
    }

    pub fn exists(&self, name: &str) -> bool {
        self.path(name).is_file()
    }

    /// The whole file, or `None` when it does not exist.
    pub fn read(&self, name: &str) -> Result<Option<Vec<u8>>, StateError> {
        let path = self.path(name);
        match fs::read(&path) {
            Ok(bytes) => Ok(Some(bytes)),
            Err(e) if e.kind() == io::ErrorKind::NotFound => Ok(None),
            Err(e) => Err(io_error(&path, e)),
        }
    }

    /// Writes the whole file as 0600: into a temporary file beside it, synced,
    /// then renamed over the old one, so no reader ever sees a partial file.
    pub fn write(&self, name: &str, data: &[u8]) -> Result<(), StateError> {
        let path = self.path(name);
        let tmp = self.path(&format!("{name}.tmp"));
        let mut file = OpenOptions::new()
            .write(true)
            .create(true)
            .truncate(true)
            .mode(FILE_MODE)
            .open(&tmp)
            .map_err(|e| io_error(&tmp, e))?;
        // `mode` applies only to a file being created: a leftover temporary
        // file keeps its old mode, so set it explicitly.
        file.set_permissions(fs::Permissions::from_mode(FILE_MODE))
            .map_err(|e| io_error(&tmp, e))?;
        file.write_all(data).map_err(|e| io_error(&tmp, e))?;
        file.sync_all().map_err(|e| io_error(&tmp, e))?;
        drop(file);
        fs::rename(&tmp, &path).map_err(|e| io_error(&path, e))
    }

    /// Removes `name`; `Ok(false)` when it did not exist.
    pub fn remove(&self, name: &str) -> Result<bool, StateError> {
        let path = self.path(name);
        match fs::remove_file(&path) {
            Ok(()) => Ok(true),
            Err(e) if e.kind() == io::ErrorKind::NotFound => Ok(false),
            Err(e) => Err(io_error(&path, e)),
        }
    }

    /// The file parsed as JSON, or `None` when it does not exist. A file that
    /// exists but does not parse is an error, never an empty value: the caller
    /// decides what failing closed means for it.
    pub fn read_json<T: DeserializeOwned>(&self, name: &str) -> Result<Option<T>, StateError> {
        let Some(bytes) = self.read(name)? else {
            return Ok(None);
        };
        serde_json::from_slice(&bytes)
            .map(Some)
            .map_err(|source| StateError::Json {
                path: self.path(name),
                source,
            })
    }

    pub fn write_json<T: Serialize>(&self, name: &str, value: &T) -> Result<(), StateError> {
        let mut bytes = serde_json::to_vec_pretty(value).map_err(|source| StateError::Json {
            path: self.path(name),
            source,
        })?;
        bytes.push(b'\n');
        self.write(name, &bytes)
    }
}

#[cfg(test)]
pub(crate) mod testing {
    //! A fresh folder per test under the temporary directory, removed on drop.

    use std::path::PathBuf;
    use std::sync::atomic::{AtomicU32, Ordering};

    static COUNTER: AtomicU32 = AtomicU32::new(0);

    pub struct Scratch(pub PathBuf);

    impl Scratch {
        pub fn new() -> Self {
            let n = COUNTER.fetch_add(1, Ordering::Relaxed);
            let path = std::env::temp_dir()
                .join(format!("rikuri-control-test-{}-{n}", std::process::id()));
            let _ = std::fs::remove_dir_all(&path);
            Scratch(path)
        }
    }

    impl Drop for Scratch {
        fn drop(&mut self) {
            let _ = std::fs::remove_dir_all(&self.0);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::testing::Scratch;
    use super::*;

    fn mode(path: &Path) -> u32 {
        fs::metadata(path).unwrap().permissions().mode() & 0o777
    }

    #[test]
    fn opening_creates_a_private_folder() {
        let scratch = Scratch::new();
        let dir = StateDir::open(scratch.0.join("nested").join("state")).unwrap();
        assert!(dir.root().is_dir());
        assert_eq!(mode(dir.root()), 0o700);
    }

    #[test]
    fn an_existing_folder_is_tightened_to_0700() {
        let scratch = Scratch::new();
        fs::create_dir_all(&scratch.0).unwrap();
        fs::set_permissions(&scratch.0, fs::Permissions::from_mode(0o755)).unwrap();
        let dir = StateDir::open(&scratch.0).unwrap();
        assert_eq!(mode(dir.root()), 0o700);
    }

    #[test]
    fn files_are_written_0600_atomically_and_read_back() {
        let scratch = Scratch::new();
        let dir = StateDir::open(&scratch.0).unwrap();
        assert_eq!(dir.read("a").unwrap(), None);
        assert!(!dir.exists("a"));
        dir.write("a", b"one").unwrap();
        assert_eq!(dir.read("a").unwrap().as_deref(), Some(&b"one"[..]));
        assert_eq!(mode(&dir.path("a")), 0o600);
        assert!(!dir.path("a.tmp").exists(), "no temporary file is left");
        dir.write("a", b"two").unwrap();
        assert_eq!(dir.read("a").unwrap().as_deref(), Some(&b"two"[..]));
        let names: Vec<_> = fs::read_dir(dir.root())
            .unwrap()
            .map(|e| e.unwrap().file_name().into_string().unwrap())
            .collect();
        assert_eq!(names, vec!["a".to_owned()]);
    }

    #[test]
    fn a_leftover_temporary_file_with_a_loose_mode_is_tightened() {
        let scratch = Scratch::new();
        let dir = StateDir::open(&scratch.0).unwrap();
        fs::write(dir.path("a.tmp"), b"stale").unwrap();
        fs::set_permissions(dir.path("a.tmp"), fs::Permissions::from_mode(0o644)).unwrap();
        dir.write("a", b"fresh").unwrap();
        assert_eq!(mode(&dir.path("a")), 0o600);
        assert_eq!(dir.read("a").unwrap().as_deref(), Some(&b"fresh"[..]));
    }

    #[test]
    fn remove_reports_whether_the_file_existed() {
        let scratch = Scratch::new();
        let dir = StateDir::open(&scratch.0).unwrap();
        assert!(!dir.remove("a").unwrap());
        dir.write("a", b"x").unwrap();
        assert!(dir.remove("a").unwrap());
        assert_eq!(dir.read("a").unwrap(), None);
    }

    #[test]
    fn json_round_trips_and_a_broken_file_is_an_error_not_an_empty_value() {
        #[derive(Debug, PartialEq, Serialize, serde::Deserialize)]
        struct Thing {
            n: u32,
            s: String,
        }
        let scratch = Scratch::new();
        let dir = StateDir::open(&scratch.0).unwrap();
        assert_eq!(dir.read_json::<Thing>("t.json").unwrap(), None);
        let thing = Thing {
            n: 7,
            s: "seven".into(),
        };
        dir.write_json("t.json", &thing).unwrap();
        assert_eq!(dir.read_json::<Thing>("t.json").unwrap(), Some(thing));
        assert!(dir.read("t.json").unwrap().unwrap().ends_with(b"\n"));
        dir.write("t.json", b"{ not json").unwrap();
        let err = dir.read_json::<Thing>("t.json").unwrap_err();
        assert!(matches!(err, StateError::Json { .. }), "{err}");
        assert!(err.to_string().contains("t.json"), "{err}");
    }

    #[test]
    fn a_name_that_cannot_be_read_is_an_error_never_an_absent_file() {
        // Only "not found" means absent. Here the name is a folder: reading
        // it fails with EISDIR, and so does removing it as a file. Any other
        // answer would let a read fault re-issue the CA or report a claim
        // finished with its file still there.
        let scratch = Scratch::new();
        let dir = StateDir::open(&scratch.0).unwrap();
        fs::create_dir(dir.path("sub")).unwrap();
        let read = dir.read("sub").unwrap_err();
        assert!(matches!(read, StateError::Io { .. }), "{read}");
        assert!(read.to_string().contains("sub"), "{read}");
        let removed = dir.remove("sub").unwrap_err();
        assert!(matches!(removed, StateError::Io { .. }), "{removed}");
        assert!(dir.path("sub").is_dir(), "nothing was deleted");
        assert!(matches!(
            dir.read_json::<u32>("sub"),
            Err(StateError::Io { .. })
        ));
    }

    #[test]
    fn an_unreadable_folder_is_an_io_error_that_names_the_path() {
        let scratch = Scratch::new();
        fs::create_dir_all(&scratch.0).unwrap();
        fs::write(scratch.0.join("file"), b"").unwrap();
        let err = StateDir::open(scratch.0.join("file").join("under-a-file")).unwrap_err();
        assert!(matches!(err, StateError::Io { .. }), "{err}");
        assert!(err.to_string().contains("under-a-file"), "{err}");
    }
}
