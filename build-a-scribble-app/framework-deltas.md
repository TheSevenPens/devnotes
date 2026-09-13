# Build a Scribble app: framework deltas

> **Status: complete first draft.** Tracked in [#8](https://github.com/TheSevenPens/devnotes/issues/8).

Three short sections, one per framework, covering only what differs from the guides already written. Read [Build a Scribble app: WPF](hard-mode-wpf.md) first: Avalonia, WinUI and egui all lay out in logical units, so all three inherit its three traps and change only the names of the methods involved.

This page also does one thing no other page in the set does. It puts all six Scribble samples side by side, and ends with one acceptance run across all of them.

---

## The six side by side

Each column names a working implementation in WinPenKit. Every row holds something a reader has to decide differently per framework.

| | Win32 | WinForms | WPF | Avalonia | WinUI 3 | Rust / egui |
| --- | --- | --- | --- | --- | --- | --- |
| layout unit | device pixel | device pixel | DIP | DIP | effective pixel | point |
| where the scale comes from | `GetDpiForWindow` | not needed | `VisualTreeHelper.GetDpi` | `TopLevel.RenderScaling` | `XamlRoot.RasterizationScale` | `ctx.pixels_per_point()` |
| how the process claims Per-Monitor V2 | `SetProcessDpiAwarenessContext` | SDK property | `app.manifest` | the framework | `app.manifest`, unpackaged only | the framework |
| the framework's own desktop conversion | `ScreenToClient(POINT*)` | `Control.PointToClient(Point)` | `Visual.PointFromScreen(Point)` | `TopLevel.PointToScreen(Point)` | none | none |
| what that method costs you | a `POINT` of two `LONG`, in the signature | `Point` with `int` members, behind a method | two `double`s, truncating with no sign of it | returns `PixelPoint`, whose members are `int` | — | — |
| surface sized from | `WM_SIZE` | `Panel.Width` | `ActualWidth` × scale | `Bounds` × `RenderScaling` | `ActualWidth` × `RasterizationScale` | `available_size()` × ppp |
| what keeps presentation 1:1 | `BitBlt` | `DrawImageUnscaled` | bitmap DPI `96 * scale` | bitmap DPI `96 * scale` | `Image.Width = w / scale` | present at the pixmap's own size |
| explicit layout rounding | not applicable | not applicable | `UseLayoutRounding` | none needed, the framework rounds | none needed, the framework rounds | by hand |

Two readings of that table matter more than the individual cells.

**The first four columns are the same lesson four times.** The conversion method exists in every framework, and its parameter type gets harder to read from left to right until WPF, whose signature gives no sign of the limit. [Framework Coordinate Conversion](../pen-input-on-windows/implementation-notes/framework-coordinate-conversion.md) covers the four signatures in detail.

**The last two columns offer no such method, and that helps rather than hurts.** WinUI and egui give you nothing to misuse. You compute the origin and subtract it because no alternative exists, which is the correct approach anyway.

---

## Avalonia

*Reference: `Scribble.Avalonia`, pinned to Avalonia 11.3.22. [PenDynamicsLab](https://github.com/TheSevenPens/PenDynamicsLab) is a larger application on the same path.*

### The trap sits in the return type

```csharp
PixelPoint PointToScreen(Point p);
```

`PixelPoint` holds two `int` members. Avalonia states the limitation in the type rather than hiding it behind a `double`, which puts this framework closer to WinForms than to WPF.

Convert the window origin and keep the element offset in DIPs:

```csharp
var windowOrigin = topLevel.PointToScreen(new Point(0, 0));
double scale = topLevel.RenderScaling;
desktopX = windowOrigin.X + elementPos.Value.X * scale;
desktopY = windowOrigin.Y + elementPos.Value.Y * scale;
```

`TranslatePoint` produces `elementPos` and keeps its fractional part. The window origin passes through the integer type and loses nothing, because Windows places windows on whole pixels.

### Avalonia's own pointer path carries a fraction

On Windows, Avalonia reads `ptHimetricLocationRaw` and maps it through `GetPointerDeviceRects`, so `point.Position` genuinely holds sub-pixel values. It falls back to whole pixels only where that API is missing.

So `PointToScreen` would discard precision the framework had already gone to trouble to deliver. Avalonia corrected its own internal handling of this in 11.3; an application on an earlier version receives quantized pen positions whatever its own conversion does.

### The surface bug appeared here, and a person had already approved the strokes

`Bounds` reports DIPs. A bitmap sized from `Bounds` alone holds one pixel per DIP, and Avalonia magnifies it to fill the canvas.

```csharp
double scale = RenderScaling;
int w = (int)Math.Ceiling(CanvasArea.Bounds.Width * scale);
int h = (int)Math.Ceiling(CanvasArea.Bounds.Height * scale);
...
_avBitmap = new WriteableBitmap(
    new PixelSize(w, h),
    new Vector(96 * scale, 96 * scale),
    PixelFormat.Bgra8888,
    AlphaFormat.Premul);
```

The `Vector(96 * scale, 96 * scale)` is the same technique WPF needs, for the same reason: the framework lays the image out at the bitmap's logical size, which it computes from the pixel count and the declared DPI.

`Scribble.Avalonia` shipped with this fault. `--selftest` found it after a person had drawn on the canvas and approved what they saw, which is the clearest argument this project produced for writing the checks at all.

### Clamp the window to the work area, at startup and on every scaling change

```csharp
ScalingChanged += (_, _) => Dispatcher.UIThread.Post(ClampToWorkArea, ...);
```

A window whose bottom edge sits under the taskbar discards every pen point aimed there, and reports nothing. Avalonia restores a saved window position in logical units, so a position that fitted at one display scale can hang off the monitor at another. `L0.window-placement` catches the result; the handler above prevents it.

### Open work

[WinPenKit#23](https://github.com/TheSevenPens/WinPenKit/issues/23) proposes swapping `Avalonia.Desktop` for `Avalonia.Win32` in this sample, which would drop the X11 and macOS backends the application never uses.

---

## WinUI 3

*Reference: `Scribble.WinUI`.*

### Per-Monitor V2 depends on how the application ships

A packaged application gets Per-Monitor V2 from its package manifest. An unpackaged one needs `app.manifest`, the same as WPF, including the `supportedOS` entry without which Windows ignores the setting.

### No framework conversion, so call ClientToScreen yourself

```csharp
private (double X, double Y) DesktopToCanvas(double x, double y)
{
    double scale = Canvas.CanvasLogicalSize.Scale;
    var pos = Canvas.GetPositionInWindow();
    var origin = new POINT { X = 0, Y = 0 };
    ClientToScreen(WindowNative.GetWindowHandle(this), ref origin);
    return ((x - origin.X) / scale - pos.X, (y - origin.Y) / scale - pos.Y);
}
```

This conversion returns effective pixels rather than device pixels, because the rest of the WinUI application works in them. The replay check therefore receives `RasterizationScale` as the factor that turns its output back into device pixels, which is what `L3.conversion-snap` needs to test the right quantity.

### WriteableBitmap has no DPI, so the Image carries the correction

This is the one place the WPF and Avalonia technique does not transfer:

```csharp
_wbBitmap = new WriteableBitmap(w, h);

// WinUI has no per-bitmap dpi, so the image is sized explicitly in effective pixels:
// w physical px shown across w/scale epx is exactly one texel per device pixel.
DrawImage.Width = w / scale;
DrawImage.Height = h / scale;
```

`new WriteableBitmap(w, h)` takes no DPI argument. Left at its natural size the image occupies `w` effective pixels, which covers `w * scale` device pixels, and WinUI magnifies the bitmap to fill them. Setting `Width` and `Height` explicitly is the only way to pin one texel to one device pixel.

`Scribble.WinUI` carried the DIP-sized surface fault as well, and `--selftest` found it the same way it found Avalonia's.

### dotnet build does not work here

The Windows App SDK's PRI generation task ships with Visual Studio rather than with the .NET SDK. `dotnet build` fails partway through with an error about a missing task, which reads as a broken project rather than a missing tool. Build with MSBuild from a Visual Studio installation:

```
"C:\Program Files\Microsoft Visual Studio\18\Community\MSBuild\Current\Bin\MSBuild.exe" ^
    Scribble.WinUI/Scribble.WinUI.csproj -p:Configuration=Debug -p:Platform=x64
```

`vswhere.exe`, under `%ProgramFiles(x86)%\Microsoft Visual Studio\Installer`, locates MSBuild on a machine whose Visual Studio version differs.

---

## Rust / egui

*Reference: `Scribble.Rust`, an eframe application over the `pen_session_*` C API in `WinPenKit.Native.dll`.*

### Points, not pixels

```rust
let available = ui.available_size();      // points
let ppp = ctx.pixels_per_point();

self.ensure_pixmap(
    (available.x * ppp).ceil() as usize,
    (available.y * ppp).ceil() as usize,
);
```

`ceil`, not truncate. A pixmap one pixel short of the canvas leaves a strip the stroke can never reach, and egui then stretches it to fill the rectangle it is presented into.

The conversion multiplies the origin up rather than dividing the pen position down, so the drawing code works in physical pixels throughout:

```rust
let canvas_x = pt.desktop_x as f32 - canvas_screen_min.x * ppp;
let canvas_y = pt.desktop_y as f32 - canvas_screen_min.y * ppp;
```

### The same surface fault looks different here

`TextureOptions::NEAREST` applies no filtering. A point-sized pixmap magnified by 2.25 therefore produces hard blocky steps rather than a soft blur.

That changes which symptom a person reports. In WPF and Avalonia an undersized surface reads as softness, which points at antialiasing; here it reads as aliasing, which points at the texture. Both come from the same cause. [Diagnosing a bad stroke](diagnosing-a-bad-stroke.md) separates the two symptoms and names what each one indicates.

### egui has no layout rounding, so snap the canvas by hand

```rust
let canvas_screen_min = egui::pos2(
    (raw_screen_min.x * ppp + TIE).round() / ppp,
    (raw_screen_min.y * ppp + TIE).round() / ppp,
);
let snap_shift = canvas_screen_min - raw_screen_min;
```

A panel below a text-sized ribbon starts wherever that ribbon happens to end, which lands on a fraction of a pixel routinely.

**Snapping alone is not enough, and the sample shipped with only the snap for four months.** Size the panel first, so the offset is a whole number of device pixels and there is nothing to snap:

```rust
egui::TopBottomPanel::top("ribbon").exact_height(snap_panel_height(130.0, ppp))
```

130 points at 2.25 is 292.5 device pixels. A permanent half means every snap resolves a tie, and a tie is decided by `f32` noise rather than by the rounding rule — one frame reading 673.4999 where the next reads 673.5000 moves the canvas a pixel with nothing on screen having moved. That produced an acceptance failure on roughly one run in eight, blamed on a cached origin it had nothing to do with.

`TIE` above is a small epsilon, and it is insurance rather than the fix: it makes a value either side of `.5` resolve consistently for whatever margin the height calculation did not anticipate. [Layout rounding and the canvas origin](../pen-input-on-windows/implementation-notes/layout-rounding-and-the-canvas-origin.md) has the measurements and the per-framework table.

Present at the snapped origin, and at the pixmap's own size:

```rust
let size_pt = egui::vec2(
    self.canvas_size[0] as f32 / ppp,
    self.canvas_size[1] as f32 / ppp,
);
let rect = egui::Rect::from_min_size(canvas_rect.min + snap_shift, size_pt);
```

Drawing it at `available` instead would stretch a `ceil`-rounded pixmap by a fraction of a pixel and undo the snapping. The snap and the presented size have to agree, or neither one holds.

### The window size is in points, and the window manager cascades

```rust
.with_inner_size([1100.0, 600.0])
```

At 2.25x, 600 points is 1350 device pixels before chrome. A larger figure that looks reasonable in points — 700, say — produces 1575 pixels, and after the window manager has cascaded the window down a few launches its bottom edge sits below a 2052-pixel work area. Pen points aimed there never arrive, and nothing reports the loss.

### Building

`build.rs` looks for `WinPenKit.Native.lib` and panics if it finds nothing, so build the C++ DLL first. Cargo does not copy `WinPenKit.Native.dll` to the output directory; place it next to the executable by hand.

`cargo` may not sit on `PATH` in a non-interactive shell even when an interactive one finds it. `%USERPROFILE%\.cargo\bin` is the usual location.

---

## One acceptance run, all six

Measured today on a 225% display, work area 3840x2052, each sample rebuilt first and run as `--replay` against the 480-point reference recording:

| sample | display scale | logical to physical ratio | bitmap | result |
| --- | --- | --- | --- | --- |
| `Scribble.Win32` | 2.25x | 1.00 | 1372x496 | 10/10 |
| `Scribble.WinForms` | 2.25x | 1.00 | 1172x431 | 10/10 |
| `Scribble.Wpf` | 2.25x | 2.25 | 2672x1230 | 10/10 |
| `Scribble.Avalonia` | 2.25x | 2.25 | 2700x1348 | 10/10 |
| `Scribble.WinUI` | 2.25x | 2.25 | 2852x1196 | 10/10 |
| `Scribble.Rust` | 2.25x | 2.25 | 2439x1022 | 10/10 |

The third column separates the two groups exactly. Win32 and WinForms lay out in device pixels, so their surface check compares the bitmap against the canvas at a ratio of 1.00 even though the display runs at 2.25x. The other four lay out in logical units, so the same check multiplies by 2.25. A sample reporting 1.00 from one of those four would be the DIP-sized surface fault, stated as a number.

Every sample prints the same ten check identifiers in the same order, which is the point of putting them in `WinPenKit.Diagnostics` rather than writing each one per application. `Scribble.Win32` reimplements them in C++ and `Scribble.Rust` in Rust, against the same identifiers and the same output format.

### What this run does not establish

The same limits apply to all six:

- **Wintab needs a tablet.** Synthetic pen injection does not reach the driver, so no Wintab code path ran in any of these.
- **The session is not covered.** A recording holds what a session produced, so replaying it tests everything downstream of the session and nothing inside it.
- **Nothing here judges the drawing.** The checks measure where the stroke goes, not what it looks like.

---

## To write

- [ ] Cite the Avalonia change that fixed its internal quantization in 11.3, rather than asserting the version from memory
- [x] Confirm whether Avalonia and WinUI round layout to device pixels by default, or whether the samples pass by luck of their ribbon heights — **both round by default; not luck.** Shifting each sample's ribbon by one logical unit at 2.25x left the canvas origin on a whole device pixel and therefore on a fractional logical one: Avalonia 678px = 301.33 DIP, WinUI 730px = 324.44 effective px. Measured 12 Sep 2026
- [ ] Re-run the six-sample table at 100% scaling, where the logical-to-physical column should read 1.00 for all six, and check that every sample still passes
