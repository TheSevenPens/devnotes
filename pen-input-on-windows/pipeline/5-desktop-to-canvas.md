# Stage 5: Position: desktop pixels to your canvas

This stage turns a position in physical desktop pixels, as a `double`, into a position on your drawing surface, in whatever unit your drawing code uses. Every UI framework offers a method that looks right for the job (`PointFromScreen`, `PointToClient`, `ScreenToClient`), and none of them is safe for pen input, because all of them pass through an integer `POINT`. The visible symptom is a faceted stroke: straight segments meeting at small angles, worst on slow, gently curving lines. Changing the brush engine does not remove it.

## In short

- Never pass a pen position to `PointFromScreen`, `PointToClient`, `ScreenToClient` or any other conversion that goes through an integer `POINT`, because it discards the fractional part.
- Convert only the canvas origin with those APIs, then compute `(desktop - origin) / scale` yourself in floating point.
- Read the origin again on every input event or render tick, because moving the window changes it without raising a size change.
- Put the canvas origin on a whole device pixel (`UseLayoutRounding="True"` in WPF; a toolbar height whose device-pixel size is a whole number in Qt and egui), or the framework resamples and softens the whole surface.

## The problem

Win32 `ClientToScreen` and `ScreenToClient` take a `POINT`:

```c
typedef struct tagPOINT {
  LONG x;
  LONG y;
} POINT;
```

Every framework conversion method is built on them, so each one discards the fractional part of whatever position it is given. A mouse position is already an integer, so for the mouse the truncation does not change the value. A pen position from a high-res source has a fractional part, which is the reason for using a high-res source.

The rule:

> **Convert the element origin, not the pen position.**

The window's client origin is on a whole pixel, so passing it through a `POINT` does not change its value. Ask Win32 for the origin only, then subtract it from the pen position and divide by the display scale yourself, in floating point. Across an investigation of six sample applications, all eight instances of this bug found were the same mistake: an integer conversion applied to the point instead of to the origin.

Two further conditions apply to the origin itself:

* It must be read fresh. Moving the window changes it and raises no size change.
* It must sit on a whole device pixel, or the framework resamples the whole surface. See [Layout rounding](#layout-rounding-and-the-canvas-origin) below.

## How the APIs differ here

Each framework has the same trap, behind a different signature:

| framework | layout unit | its own desktop conversion | how the integer shows |
| --- | --- | --- | --- |
| Win32 | device pixel | `ScreenToClient(POINT*)` | in the signature |
| WinForms | device pixel | `Control.PointToClient(Point)` | `System.Drawing.Point` has `Int32` members, with no `PointF` overload |
| WPF | DIP | `Visual.PointFromScreen(Point)` | not shown: `Point` is two `double` |
| Avalonia | DIP | `TopLevel.PointToScreen(Point)` | returns `PixelPoint`, two `int` |
| WinUI 3 | effective pixel | none | |
| Rust / egui | point | none | |

WinUI and egui offer no method to misuse, so the origin-and-subtract approach is the only one available there.

### WPF: double in the signature, truncation inside

`PointToScreen` and `PointFromScreen` take and return `System.Windows.Point`, a pair of `double`, and route the value through a `POINT`. The `double` handed back holds a whole number of device pixels. Measured on a 1440p display at 1.75x with a Wintab high-res context, on the path the application drew:

| stage | mean turn angle | points on a whole device pixel |
| --- | --- | --- |
| pen data as delivered | 4.11° | 0 / 3014 |
| after `PointFromScreen` | **17.51°** | **3014 / 3014** |

The p90 turn angle reached 45°, the value a path quantized to a square grid produces.

The fix asks Win32 only for the client origin. This is [`WpfCoordinates.GetTransform`](https://github.com/TheSevenPens/WinPenKit/blob/main/WinPenKit.Wpf/WpfCoordinates.cs):

```csharp
public static (double OriginX, double OriginY, double ScaleX, double ScaleY)? GetTransform(
    Visual element)
{
    if (PresentationSource.FromVisual(element) is not HwndSource source ||
        source.RootVisual is null)
        return null;

    // An integer, so converting it through a POINT does not change its value.
    var clientOrigin = new POINT { X = 0, Y = 0 };
    if (!ClientToScreen(source.Handle, ref clientOrigin))
        return null;

    // Where the element sits in the window, in DIPs. A GeneralTransform, so it keeps
    // its fractional part.
    Point dipOffset;
    try { dipOffset = element.TransformToAncestor(source.RootVisual).Transform(new Point(0, 0)); }
    catch (InvalidOperationException) { return null; }   // not in the tree, or not arranged

    var dpi = VisualTreeHelper.GetDpi(element);
    double scaleX = dpi.DpiScaleX > 0 ? dpi.DpiScaleX : 1.0;
    double scaleY = dpi.DpiScaleY > 0 ? dpi.DpiScaleY : 1.0;

    return (clientOrigin.X + dipOffset.X * scaleX,
            clientOrigin.Y + dipOffset.Y * scaleY,
            scaleX, scaleY);
}
```

Both directions are then arithmetic:

```csharp
// desktop pixels -> element DIPs   (replaces PointFromScreen)
var p = new Point((desktopX - xf.OriginX) / xf.ScaleX, (desktopY - xf.OriginY) / xf.ScaleY);

// element DIPs -> desktop pixels   (replaces PointToScreen)
var s = new Point(xf.OriginX + elementX * xf.ScaleX, xf.OriginY + elementY * xf.ScaleY);
```

Read the transform once per input event or render tick, not once per point: a stylus event carries many points and the element has not moved between them.

### WinForms: Int32 in the signature

A Per-Monitor V2 WinForms application lays out in physical pixels, so there is no scale factor:

```csharp
// Wrong: cannot express a pen position.
var canvasPt = _canvasPanel.PointToClient(new Point((int)pt.DesktopX, (int)pt.DesktopY));

// Right: convert the origin, subtract in floating point.
var origin = _canvasPanel.PointToScreen(Point.Empty);
var canvasPt = new PointF((float)(pt.DesktopX - origin.X), (float)(pt.DesktopY - origin.Y));
```

The compiler objects to the wrong version at the call site, which makes it the easier of the two to catch. The risk is documentation that recommends it.

### Avalonia: int in the return type

```csharp
// Wrong:
var clientPt = topLevel.PointToClient(new PixelPoint((int)pt.DesktopX, (int)pt.DesktopY));

// Right:
var windowOrigin = topLevel.PointToScreen(new Point(0, 0));
double scale = topLevel.RenderScaling;
var clientPt = new Point((pt.DesktopX - windowOrigin.X) / scale,
                         (pt.DesktopY - windowOrigin.Y) / scale);
```

An Avalonia version earlier than 11.3 quantizes pen positions inside its own pointer handling, whatever the application's conversion does.

### WinUI 3: no conversion offered

`Scribble.WinUI` returns effective pixels, because the rest of a WinUI application works in them:

```csharp
private (double X, double Y) DesktopToCanvas(double x, double y)
{
    double scale = Canvas.CanvasLogicalSize.Scale;     // XamlRoot.RasterizationScale
    var pos = Canvas.GetPositionInWindow();
    var origin = new POINT { X = 0, Y = 0 };
    ClientToScreen(WindowNative.GetWindowHandle(this), ref origin);
    return ((x - origin.X) / scale - pos.X, (y - origin.Y) / scale - pos.Y);
}
```

That is `canvasDip = (desktopPx - clientOriginPx) x (96 / DPI) - canvasPositionDip`. Call `ClientToScreen` with a Per-Monitor V2 thread context, as [Stage 4](4-device-to-desktop.md) describes.

### Why review does not catch the truncation

* **WPF's signature gives no sign of it.** WinForms and Avalonia show the integer in a type; WPF does not.
* **The output still has decimals.** On a scaled display the conversion divides by the scale, so a truncated input still produces a fractional result: `701 / 1.75 = 400.571428...`. A readout of `Canvas: 400.57, 233.14` was once taken as proof that coordinates were fine. To use a readout as evidence, print the desktop position with decimals, before any scale division. `Scribble.Wpf` prints `Screen:` with two decimals for this reason.
* **Per-Monitor V2 does not help.** It fixes the coordinate space, not the truncation.

## How WinPenKit handles it

Every WinPenKit session delivers `DesktopX`/`DesktopY` in physical desktop pixels as `double` (see [Stage 4](4-device-to-desktop.md)). The conversion to the canvas belongs to the application, because only the application knows its canvas. WinPenKit supplies `WpfCoordinates` for WPF and shows the pattern in each Scribble sample:

| sample | conversion | unit it returns |
| --- | --- | --- |
| [`Scribble.Wpf/MainWindow.xaml.cs`](https://github.com/TheSevenPens/WinPenKit/blob/main/Scribble.Wpf/MainWindow.xaml.cs) | `RefreshCanvasOrigin()` reads `WpfCoordinates.GetTransform(CanvasArea)` on every render tick that has points; then `(pt.DesktopX - _canvasOriginX) / _renderScale` | DIPs (the SkiaSharp canvas carries the scale) |
| [`Scribble.WinForms/MainForm.cs`](https://github.com/TheSevenPens/WinPenKit/blob/main/Scribble.WinForms/MainForm.cs) | `_canvasPanel.PointToScreen(Point.Empty)` per point, then subtract | device pixels |
| [`Scribble.Avalonia/MainWindow.axaml.cs`](https://github.com/TheSevenPens/WinPenKit/blob/main/Scribble.Avalonia/MainWindow.axaml.cs) | window origin from `PointToScreen`, divide by `RenderScaling`, subtract `CanvasArea.TranslatePoint` origin, then multiply back by the scale | device pixels |
| [`Scribble.WinUI/MainWindow.xaml.cs`](https://github.com/TheSevenPens/WinPenKit/blob/main/Scribble.WinUI/MainWindow.xaml.cs) | `DesktopToCanvas` above | effective pixels |

Each sample exposes its conversion as a `DesktopToCanvas` method, and its self test passes that same method to `CheckReplay` and `CheckOriginTracksWindow`, so the test exercises the code the pen goes through. [Stage 8](8-verifying.md) describes those checks.

`Scribble.Wpf` once cached the origin when the bitmap was created. Dragging the window raised no size change, so every stroke after a drag landed the drag distance away from the pen while all the other checks passed. `RefreshCanvasOrigin()` is now called on every render tick, and `L3.origin-tracks-window` checks it.

## Layout rounding and the canvas origin

A canvas placed below a toolbar starts where the toolbar ends. In a framework that lays out in logical units, that is a whole number of logical units, which at a fractional scale is not a whole number of device pixels:

```
130 logical units x 2.25 = 292.5 device pixels
```

The framework then resamples the whole surface to draw it between pixel rows. Every edge softens by the same amount, while coordinates and resolution both still measure correct. One WPF canvas landed 0.00 px off horizontally and 0.64 px off vertically, so the softening affected one axis only.

Which frameworks round layout to device pixels, measured on 12 Sep 2026 at 2.25x by moving each sample's toolbar by one logical unit and reading the canvas origin from `--selftest`:

| framework | rounds layout to device pixels? | evidence |
| --- | --- | --- |
| Win32, WinForms | not applicable | they lay out in device pixels |
| WPF | only with `UseLayoutRounding="True"` | `Scribble.Wpf` sets it on the window |
| Avalonia | yes, by default | origin 678 px = 301.33 DIP: whole in device pixels, fractional in logical units |
| WinUI 3 | yes, by default | origin 730 px = 324.44 effective px |
| Qt Widgets | no | a 211-point toolbar put the origin at y = 475.25 px |
| egui | no | needs a manual snap |

For WPF:

```xml
<Window UseLayoutRounding="True">
  ...
  <Image RenderOptions.BitmapScalingMode="NearestNeighbor" Stretch="None" />
```

`UseLayoutRounding` is the fix. `NearestNeighbor` gives the same result as the default at a correct 1:1 mapping; if alignment later regresses, it shows the fault as aliasing instead of a blur that would be mistaken for a rendering problem.

### Snapping a permanent .5 is decided by floating-point noise

Where the framework does not round, the obvious repair is to snap the origin: `snapped = (raw * ppp).round() / ppp`. If the offset is exactly `.5` on every frame, every snap is a tie, and the floating-point result decides it. Measured in `Scribble.Rust` on 12 Sep 2026, with a toolbar of exactly 130 points:

```
frame 1   raw*ppp = 650.5000  ->  651  ->  289.333344
frame 2   raw*ppp = 673.4999  ->  673  ->  299.111115     (673.5 would give 674)
```

`f32` put the two frames on opposite sides of the tie, so the canvas moved a pixel with nothing on screen having moved. This made an acceptance check fail about one run in eight, reporting a 22 px window move where the window had moved 23. The check reported a cached origin, which was not the cause.

The fix removes the tie: size the toolbar so that its height times the scale is a whole number. At 2.25 that is a multiple of 4 logical units, at 1.5 a multiple of 2, at 2.0 any integer. Grow the toolbar rather than shrink it, so it does not clip its contents, and recompute when the scale changes. Keep the snap as well, with a small epsilon so a value a ten-thousandth either side of `.5` resolves the same way, and comment that the height calculation is the fix and the snap only a safeguard.

A surface-alignment check reports the origin after snapping, so it cannot see a tie. Only a check that moves the window and compares how far the origin followed (`L3.origin-tracks-window`) can.

## Traps

1. **Passing the pen position to `PointFromScreen`, `PointToClient` or `ScreenToClient`.** Symptom: faceted strokes; 100% of points on whole device pixels. Fix: convert the origin, subtract in floating point.
2. **Truncating to call an integer API** (`(int)pt.DesktopX`). Same symptom, same fix.
3. **Trusting a readout taken after the scale division.** Symptom: decimals that prove nothing. Fix: print the desktop position with at least two decimals before dividing.
4. **Caching the canvas origin.** Symptom: ink lands the drag distance from the pen after the window moves. Fix: read the origin per event or render tick.
5. **Canvas origin on a fractional device pixel.** Symptom: every edge soft, often on one axis only. Fix: `UseLayoutRounding` in WPF; a toolbar height that is a whole number of device pixels in egui and Qt.
6. **Snapping a permanent `.5`.** Symptom: an intermittent one-pixel jump and flaky origin checks. Fix: remove the tie by sizing the toolbar.
7. **Mixing units.** Symptom: strokes scaled by the display factor. Fix: decide whether your canvas works in device pixels or logical units, and pass the matching scale to your checks (`Scribble.Avalonia` passes 1.0 because its conversion returns device pixels; `Scribble.WinUI` passes `RasterizationScale`).
8. **A surface sized in logical units.** Symptom: blocky or soft strokes while coordinates measure correct. This belongs to rendering: see [framework deltas](../../build-a-scribble-app/framework-deltas.md) and [Rendering options for paint apps](../../rendering-for-pen-apps.md).

## Further reading

* [Stage 4: device units to desktop pixels](4-device-to-desktop.md) and [Stage 6: Values](6-values.md).
* [Stage 8: Verifying the pipeline](8-verifying.md), for the snap, lossless and origin checks.
* [Diagnosing a bad stroke](../../build-a-scribble-app/diagnosing-a-bad-stroke.md), for telling faceted, blocky, soft and lumpy strokes apart.
* [Build a Scribble app: WPF](../../build-a-scribble-app/hard-mode-wpf.md) and [framework deltas](../../build-a-scribble-app/framework-deltas.md).
* [Position smoothing](../../processing-pen-data/position-smoothing.md): mild smoothing recovers part of the error quantization introduces, where quantization cannot be avoided.
