# Known Quirks and Gotchas

## Known Quirks and Gotchas

### Wintab

* **CXO\_SYSTEM required** for Wacom driver packet delivery — without it, context opens but no packets arrive
* **Multi-monitor:** custom `OutExt` is clipped by the driver's tablet-to-monitor mapping; use system context output range or tablet-native with ScaleAxis conversion
* **Y-axis:** tablet origin is bottom-left; must negate `OutExtY` or `SysExtY` for screen convention
* **DPI in WinUI 3:** `ClientToScreen` must be called from a Per-Monitor V2 thread context; default DPI-unaware context returns virtualized values that drift
* **Two contexts:** `WTI_DEFCONTEXT` (digitizer) may not deliver packets; `WTI_DEFSYSCTX` (system) is more reliable as a base

### WM\_POINTER

* **DPI awareness:** coordinates are in the process's DPI awareness context — may need conversion for Per-Monitor V2
* **Pointer ID tracking:** each contact point has a unique ID; pen and touch can coexist
* **WinUI 3 wraps this:** `PointerPoint` events in WinUI 3 are built on WM\_POINTER; using both simultaneously can cause conflicts

### Windows Ink (WinUI / WPF)

* **Pre-normalized pressure:** convenient but loses the raw range (some tablets report 8192 levels, others 2048 — both become 0.0–1.0)
* **Tilt as X/Y:** less precise than azimuth/altitude for certain brush algorithms (calligraphy, airbrush)
* **InkCanvas:** built-in ink rendering is easy but limited for custom brush engines

### RealTimeStylus

* **COM-based:** requires interop boilerplate in .NET
* **Deprecated in spirit:** Microsoft hasn't invested in it since Windows 7; WM\_POINTER is the successor
* **Plugin model:** sync plugins run on the pen thread (low latency), async plugins run on the UI thread
