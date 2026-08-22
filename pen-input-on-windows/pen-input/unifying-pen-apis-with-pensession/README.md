# WinPenKit

## WinPenKit

The [WinPenKit](https://github.com/TheSevenPens/WinPenKit) library provides a unified `IPenSession` interface across seven backends, with runtime switching via a dropdown — no restart required.

## Related projects

### Qt QTabletEvent

Qt abstracts tablet input across Wintab (Windows), XInput (Linux), and Apple Pencil (macOS/iOS) behind a single `QTabletEvent` class. Fully normalizes all values (pressure 0.0–1.0, tilt in degrees). Event-driven (not polling). Does not expose which underlying API is in use. Krita uses Qt's tablet abstraction and adds a startup-time switch between Wintab and WM\_POINTER backends (requires app restart).

* [QTabletEvent docs](https://doc.qt.io/qt-6/qtabletevent.html)
* [Qt Tablet example](https://doc.qt.io/qt-6/qtwidgets-widgets-tablet-example.html)
* [Krita Tablet Settings](https://docs.krita.org/en/reference_manual/preferences/tablet_settings.html)

### octotablet (Rust)

A Rust crate for cross-platform tablet/pen input. Provides a unified interface over platform-specific tablet APIs with support for pressure, tilt, and multiple tools. Designed for Rust applications that need pen input without going through a full UI framework.

* [octotablet on crates.io](https://crates.io/crates/octotablet)
* [octotablet on GitHub](https://github.com/Fuzzyzilla/octotablet)
* [octotablet docs](https://docs.rs/octotablet/0.1.0/octotablet/)
