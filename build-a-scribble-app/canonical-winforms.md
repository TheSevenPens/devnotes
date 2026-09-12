# Build a Scribble app: WinForms

> **Status: outline.** Headings and intent only. Tracked in [#8](https://github.com/TheSevenPens/devnotes/issues/8).

Canonical entry point, and the faster of the two. Same app, same diagnostics, same acceptance checklist as the [native path](canonical-native.md) — the coordinate model is identical, so the only new variable is the managed library surface.

Reference implementation: `Scribble.WinForms` in WinPenKit.

---

## 1. Project setup

*Intent: short, because this is the point of choosing WinForms.*

- `dotnet new winforms`, target framework, `<ApplicationHighDpiMode>PerMonitorV2</ApplicationHighDpiMode>`
- `WinPenKit` and `WinPenKit.WinForms` references
- **Verify:** the app runs

## 2. Per-Monitor V2, and why it is already done

*Intent: .NET does this for you, which is convenient and worth confirming rather than trusting.*

- What the SDK property actually emits
- How to check it at runtime instead of assuming
- Link: [Per-Monitor V2 DPI Awareness](../pen-input-on-windows/implementation-notes/per-monitor-v2-dpi-awareness.md)

## 3. Diagnostics first

*Intent: same position in the guide as the native path, for the same reason — the app reports its own state before it can draw.*

- `WinPenKit.Diagnostics.SelfTest`, wired from `Program.Main`
- Returning the exit code rather than discarding it (a real bug, caught by running it)
- **Verify:** `--selftest` reports Level 0 passing

## 4. A canvas panel and a bitmap

*Intent: build the surface, then prove it.*

- A double-buffered `Panel`
- `SKBitmap` sized from `Panel.Width`/`Height` — already physical pixels under Per-Monitor V2
- Why Level 1 is near-tautological here, as in C++, and what that does and does not prove
- **Verify:** `--selftest` reports 6/6

## 5. Opening a pen session

*Intent: the managed API surface, which is the one genuinely new thing on this path.*

- `PenSessionFactory.GetAvailableApis()` and `Create`
- `WinFormsPointerSession` for WM_POINTER
- Draining points on a timer; a point counter so "no stroke" and "no points" are distinguishable

## 6. Desktop pixels to canvas pixels

*Intent: the payload. Here the trap is behind a method call, but the type still gives it away.*

- `Control.PointToClient` takes a `System.Drawing.Point` — `Int32` fields, and there is no `PointF` overload
- Show the reflection output: it cannot carry a sub-pixel position at all
- Convert the **control origin**, subtract in floating point
- Contrast with WPF, where the same flaw hides behind a `double` signature — forward reference to [hard mode](hard-mode-wpf.md)
- **Verify:** `--replay` reports 9/9
- Link: [Framework Coordinate Conversion](../pen-input-on-windows/implementation-notes/framework-coordinate-conversion.md)

## 7. Drawing a stroke

- SkiaSharp `DrawLine` into the `SKBitmap`, blitted unscaled
- Pressure to width — note brush size is in pixels here and DIPs in WPF
- **Verify:** a stroke appears, `--replay` still 9/9

## 8. Handing it to a person

- Same boundary as the native path: Wintab needs a tablet, feel is not machine-checkable
- If it looks wrong: [Diagnosing a bad stroke](diagnosing-a-bad-stroke.md)

---

## To write

- [ ] Decide how much of section 6 to restate vs link — this path must stand alone for a reader who skipped C++
- [ ] The reflection output in section 6 is the strongest evidence available; get it exact
- [ ] Flag the brush-size unit inconsistency once, here, rather than on every framework page
