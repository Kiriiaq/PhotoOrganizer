# Security Policy

PhotoOrganizer manipulates user files (copy, move, delete) and performs one outbound HTTPS request (OpenStreetMap Nominatim, opt-in geocoding). Security is taken seriously, even though the threat model is limited (no auth, no server, no shared infrastructure).

---

## Supported versions

| Version | Status |
|---|---|
| 2.x (current) | ✅ Supported |
| 1.x | ❌ End-of-life since v2.0.0 (May 2026). Upgrade to 2.x. |

Security fixes are released as patch versions of the current minor (e.g. `2.0.1`).

---

## Reporting a vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Instead, contact the maintainer directly:

- **Email** : `manugrolleau48@gmail.com`
- **Subject line** : `[PhotoOrganizer SECURITY] <short description>`

Include:

1. Affected version (Settings → About, or commit SHA).
2. Steps to reproduce.
3. Expected impact (data loss, privilege escalation, code execution, denial of service, etc.).
4. Suggested fix if you have one.

Expected response time: **48 h acknowledgement**, **14 days** for an initial assessment and a planned fix window if confirmed.

Reporters acting in good faith will be credited in the release notes of the fix (unless they prefer to stay anonymous).

---

## Threat model and scope

### In scope

- **File system manipulation** : path traversal, symlink races, accidental data loss, unsafe deletion.
- **Bundled binaries** : `assets/tools/exiftool.exe` and its Perl runtime — vulnerabilities in this fallback subprocess.
- **Outbound network** : the single GET to `nominatim.openstreetmap.org` (geocoding). Improper URL construction, MITM resistance.
- **Configuration handling** : YAML loading (uses `yaml.safe_load`), JSON config files in `%LOCALAPPDATA%`.
- **Quarantine and rollback** : ensure deletion is reversible, that rollback cannot be hijacked to overwrite arbitrary files.
- **EXE supply chain** : the `release.yml` build pipeline.

### Out of scope

- **Antivirus heuristic false positives** on the PyInstaller `--onefile` EXE (unsigned binary). This is a known limitation of unsigned PyInstaller builds.
- **Privilege escalation against the local user** : the application runs with the current user's privileges by design. It does not request elevation.
- **Denial of service via crafted EXIF** in user-supplied files — these errors are caught and logged; the app remains responsive. Submit a report only if you can crash or hang the GUI.
- **Vulnerabilities in upstream dependencies** that are not exploitable through PhotoOrganizer's actual use of them.

---

## Hardening already in place

- **`yaml.safe_load`** for all YAML config loading (no arbitrary object construction).
- **MD5 hashing** explicitly marked `usedforsecurity=False` (Bandit B324).
- **`subprocess`** calls use absolute paths and a 30-second timeout, no shell=True.
- **HTTPS only** for the Nominatim request, with a 5-second timeout and a custom `User-Agent`.
- **Quarantine** with metadata for reversible deletion, instead of one-shot `send2trash`.
- **Recycle bin / `System Volume Information` exclusion** when scanning to avoid loops or destructive recursion.
- **No credentials, secrets, or API keys** in the source tree. No `.env` is required.
- **`ruff` + `bandit`** run on every CI pipeline. Bandit High issues are zero at time of writing.

---

## What we won't fix

- The EXE is unsigned. We do not currently have a code-signing certificate. The cost (~250 €/year) is outside the budget of an open-source project. This causes Defender SmartScreen warnings on first launch. We accept this and document it in the README.
- ExifTool fallback runs an embedded Perl runtime. Its surface is large but the call is only triggered when `exifread` and Pillow both fail to read a file. We do not audit ExifTool's Perl code. If you find an exploitable vulnerability *triggered by reading a metadata file*, please report it — we may simply remove the fallback (see [docs/exe-optimization.md](docs/exe-optimization.md) finding F-01).

---

## Disclosure policy

We follow a **coordinated disclosure** model:

1. Reporter contacts the maintainer privately.
2. The maintainer confirms the issue within 48 h.
3. A fix is developed, tested, and released as a patch version.
4. Once the fix is publicly available, the maintainer publishes a security advisory (GitHub Security Advisories tab) within 7 days of the release.
5. The reporter is credited (unless they decline).

If a fix takes more than 90 days, the reporter is free to publish their findings.

---

## Acknowledgements

Security reports are appreciated. Reporters acting in good faith have helped harden similar projects significantly. If this is your first time reporting, the [HackerOne disclosure guidance](https://www.hackerone.com/disclosure-guidelines) is a good baseline.
