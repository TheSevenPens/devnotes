# Build a Scribble app: Native / C++

> **Status: outline.** Headings and intent only. Tracked in [#8](https://github.com/TheSevenPens/devnotes/issues/8).

Canonical entry point. Nothing sits between the application and the pen API, so every coordinate transformation is one the reader writes and can see.

Reference implementation: `Scribble.Win32` in WinPenKit.

---

## 1. Before any code: the build environment

*Intent: get the toolchain wrong here and the failures look like code failures. This section is a checklist the reader can verify before writing a line.*

- Exact Visual Studio workload and components
- `WIN32_LEAN_AND_MEAN` strips COM declarations that `GdiplusImaging.h` needs — `#include <objidl.h>` first
- `gdiplus.lib` in the linker inputs
- `WinPenKitNative.sln`, VS MSBuild, `-p:Platform=x64`
- **Verify before proceeding:** a trivial window builds and runs

## 2. Per-Monitor V2, before the first window

*Intent: this is load-bearing and invisible when wrong. Do it first so nothing downstream is measured in the wrong coordinate space.*

- `SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2)`
- Why a manifest entry is not enough / when it is
- What a DPI-unaware process sees instead, and why it cannot tell
- Link: [Per-Monitor V2 DPI Awareness](../pen-input-on-windows/implementation-notes/per-monitor-v2-dpi-awareness.md)

## 3. Diagnostics first

*Intent: the app must be able to report its own state before it can draw. This is the section that makes the guide usable by an agent, and it comes before the canvas on purpose.*

- What `--selftest` checks and why each check exists
- Wiring `selftest.h`: `AttachConsole` vs an inherited handle, exit codes
- **Verify before proceeding:** `--selftest` reports Level 0 passing

## 4. A window and a drawing surface

*Intent: build the canvas, then immediately prove it is the right size and in the right place.*

- A regular top-level window (not `HWND_MESSAGE` — see Wintab gotchas)
- `CreateCompatibleBitmap` sized from the client rect
- Why Win32 makes Level 1 nearly tautological: layout is in physical pixels, so the surface cannot be sized in the wrong unit
- **Verify:** `--selftest` reports 6/6

## 5. Opening a pen session

*Intent: get points arriving, and make their arrival visible in text.*

- `pen_session.h`, the C API surface
- Choosing an API: Wintab system, Wintab digitizer, WM_POINTER
- A point counter in the ribbon, so "no stroke" and "no points" are distinguishable
- Link: [Wintab Gotchas](../pen-input-on-windows/implementation-notes/wintab-gotchas.md)

## 6. Desktop pixels to canvas pixels

*Intent: the heart of the guide. In C++ the trap is visible in the type, which is the entire reason this is the canonical path.*

- `ScreenToClient` takes a `POINT` — two `LONG`s. Show the struct.
- Convert the **client origin**, not the pen position
- The rule, stated once: the origin is integral so a lossy conversion costs nothing; the pen position is the one value that must stay fractional
- **Verify:** `--replay` reports 9/9, including `turn(input) == turn(output)`
- Link: [Framework Coordinate Conversion](../pen-input-on-windows/implementation-notes/framework-coordinate-conversion.md)

## 7. Drawing a stroke

*Intent: the first stroke, and why it is drawn with GDI+ rather than GDI.*

- `MoveToEx`/`LineTo` are integer and aliased — they discard what section 6 preserved
- GDI+ `DrawLine(PointF)` with `SmoothingModeAntiAlias`
- Pressure to width
- **Verify:** a stroke appears, and `--replay` still reports 9/9

## 8. Handing it to a person

*Intent: the boundary. Everything above is machine-verifiable; this is not.*

- Wintab needs a real tablet — no synthetic injection reaches the driver
- What to ask someone to look for, and what their answer does and does not tell you
- If it looks wrong: [Diagnosing a bad stroke](diagnosing-a-bad-stroke.md)

---

## To write

- [ ] Exact component list, verified from a clean machine
- [ ] Decide how much `pen_session.h` to reproduce inline vs link
- [ ] Section 6 needs the strongest prose in the guide — it is the payload
- [ ] Confirm every "Verify" step is reachable in order (no check that needs a later section)
