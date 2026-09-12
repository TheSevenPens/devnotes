# Build a Scribble app: framework deltas

> **Status: outline.** Headings and intent only. Tracked in [#8](https://github.com/TheSevenPens/devnotes/issues/8).

Short pages, not tutorials. Each assumes [WPF hard mode](hard-mode-wpf.md) and covers only what differs.

---

## Avalonia

*Reference: `Scribble.Avalonia`, plus `PenDynamicsLab` as a larger example.*

- `TopLevel.PointToScreen` returns a `PixelPoint` — `int` members, so the trap is visible in the return type rather than hidden by it
- Avalonia had the same bug **internally** and fixed it in 11.3; an app on an earlier version gets quantized pen positions no matter how carefully it does its own conversion
- `Bounds` are DIPs — a surface sized from them is magnified. This was a real bug in the sample, found by `--selftest` after the app had already been signed off
- `RenderScaling`, and declaring the `WriteableBitmap` at `96 * scale`
- Window placement: clamping to the monitor work area, at startup *and* on scaling change

## WinUI 3

*Reference: `Scribble.WinUI`.*

- Unpackaged apps need Per-Monitor V2 in `app.manifest`; packaged apps get it free
- `ActualWidth` is in effective pixels; `XamlRoot.RasterizationScale` relates them to device pixels
- **No per-bitmap DPI** — so the `Image` must be sized explicitly in effective pixels to reach the screen 1:1. This is the one place the WPF technique does not transfer
- Also carried the DIP-sized surface bug, found the same way as Avalonia's
- Build quirk: the Windows App SDK PRI task ships with Visual Studio, not the dotnet SDK, so `dotnet build` fails in a way that looks like broken code

## Rust / egui

*Reference: `Scribble.Rust`.*

- `ui.available_size()` is in **points**, not pixels — a pixmap sized from it is magnified
- `TextureOptions::NEAREST` means that magnification has no filtering at all: hard blocky steps rather than a soft blur, so the same bug looks different here
- egui has no layout rounding; the canvas must be snapped to device pixels by hand
- Default window size is in points and multiplies by the display scale — a 700-point window does not fit a 2052px work area once the window manager cascades it
- `WinPenKit.Native.dll` must be placed next to the exe by hand; cargo will not copy it

---

## To write

- [ ] Keep each under a page. If one grows past that, it wants to be its own guide
- [ ] Each should end with the same acceptance run, so the checklist stays uniform across all six samples
