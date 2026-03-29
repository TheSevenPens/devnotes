# Wintab vs Windows Ink Driver Conflict

## Wintab vs Windows Ink Driver Conflict

Many tablet drivers (including Wacom's) treat Wintab and Windows Ink as mutually exclusive input paths. When one is active, the other may be suppressed or produce degraded data.

**In practice:**

* When Wintab is active (a context is open), the driver may stop delivering WM\_POINTER pen events
* When Windows Ink is the active path, the driver may not load `wintab32.dll` or may deliver incomplete Wintab data
* Some driver versions have a "Use Windows Ink" checkbox in the driver settings that controls which path is primary

**This is the reason apps like Krita require a restart when switching input APIs** — the driver-level plumbing is set up at process startup, and switching cleanly at runtime is not reliably supported by all drivers.

**Implications for a unified session design:**

* The session factory must probe for actual driver support, not just OS capability
* Offering both Wintab and WM\_POINTER in a dropdown is only meaningful if the driver supports both
* Starting a Wintab session may disable WM\_POINTER for the rest of the process lifetime (driver-dependent)
* See [FUTURES\_UNIFIED\_SESSION.md](../../pen-input/apis/FUTURES_UNIFIED_SESSION.md) for the full abstraction design
