# Framework Coordinate Conversion

Every UI framework offers a pair of methods for converting between a control's coordinate space and the screen — `PointFromScreen`, `PointToClient`, and their equivalents. **None of them are safe for pen input.** All of them quantize to whole pixels, because all of them are built on Win32 `ClientToScreen` / `ScreenToClient`, which take an integer `POINT`.

For mouse input this costs nothing: mouse positions are integral to begin with. For pen input it destroys the single thing a digitizer context exists to provide.

The symptom is a stroke with flat facets and small kinks, most visible on slow, gently curving lines. It is easy to mistake for a brush engine problem, and it will survive any amount of work on the brush engine.

## The rule

> **Convert the element origin, not the pen position.**

The origin is on a pixel boundary, so a lossy conversion costs nothing when applied to it. The pen position is the one value that must stay fractional — so it should never be passed to one of these APIs at all. Subtract the origin and apply the DPI scale yourself.

Every instance of this bug found across a full investigation of six sample applications — eight instances in total — was the same mistake of applying an integer conversion to the point rather than to the origin.

## 1. WPF: the signature hides it

`Visual.PointToScreen` and `Visual.PointFromScreen` take and return `System.Windows.Point`, which is a pair of `double`. Nothing in the signature suggests a loss of precision. Internally the value is converted to a `POINT`:

```c
typedef struct tagPOINT {
  LONG x;
  LONG y;
} POINT;
```

The fractional part is discarded, and the `double` handed back is a `double` holding a whole number.

Measured on a 1440p display at 1.75× scaling, with a Wintab digitizer context. Mean turn angle between consecutive segments, on the path the application actually drew:

| stage | mean turn angle | points on a whole device pixel |
| ----- | --------------- | ------------------------------ |
| pen data as delivered | 4.11° | 0 / 3014 |
| after `PointFromScreen` | **17.51°** | **3014 / 3014** |

Every point snapped. The p90 turn angle reached 45°, the signature of a path quantized to a square lattice: consecutive segments differ by whole pixel steps, so direction changes arrive in discrete jumps.

### The fix

The only value needed from Win32 is the window's client origin, which is integral by nature — so asking for it through a `POINT` loses nothing.

```csharp
using System.Runtime.InteropServices;
using System.Windows;
using System.Windows.Interop;
using System.Windows.Media;

public static class WpfCoordinates
{
    [DllImport("user32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool ClientToScreen(IntPtr hWnd, ref POINT lpPoint);

    [StructLayout(LayoutKind.Sequential)]
    private struct POINT { public int X; public int Y; }

    /// <summary>
    /// The element's top-left corner in desktop device pixels, plus the DPI scale relating
    /// its DIPs to those pixels. Null if the element is not connected to a window.
    /// </summary>
    public static (double OriginX, double OriginY, double ScaleX, double ScaleY)? GetTransform(
        Visual element)
    {
        if (PresentationSource.FromVisual(element) is not HwndSource source ||
            source.RootVisual is null)
        {
            return null;
        }

        // The window's client origin. Integral by nature, so the POINT costs nothing here.
        var clientOrigin = new POINT { X = 0, Y = 0 };
        if (!ClientToScreen(source.Handle, ref clientOrigin))
            return null;

        // Where the element sits inside the window, in DIPs. A GeneralTransform, so this
        // keeps its fractional part — unlike anything routed through a POINT.
        Point dipOffset;
        try
        {
            dipOffset = element.TransformToAncestor(source.RootVisual).Transform(new Point(0, 0));
        }
        catch (InvalidOperationException)
        {
            return null;   // not in the same visual tree, or not yet arranged
        }

        var dpi = VisualTreeHelper.GetDpi(element);
        double scaleX = dpi.DpiScaleX > 0 ? dpi.DpiScaleX : 1.0;
        double scaleY = dpi.DpiScaleY > 0 ? dpi.DpiScaleY : 1.0;

        return (clientOrigin.X + dipOffset.X * scaleX,
                clientOrigin.Y + dipOffset.Y * scaleY,
                scaleX, scaleY);
    }
}
```

Both directions are then arithmetic:

```csharp
// Screen device pixels -> element DIPs   (replaces PointFromScreen)
var p = new Point((desktopX - xf.OriginX) / xf.ScaleX,
                  (desktopY - xf.OriginY) / xf.ScaleY);

// Element DIPs -> screen device pixels   (replaces PointToScreen)
var s = new Point(xf.OriginX + elementX * xf.ScaleX,
                  xf.OriginY + elementY * xf.ScaleY);
```

Cache the transform per input event rather than per point — a stylus event carries many points and the element has not moved between them.

### This also affects WPF's own stylus stack

`StylusEventArgs.GetStylusPoints(element)` correctly returns sub-pixel DIPs. Calling `element.PointToScreen(...)` to normalise them to screen coordinates throws that away immediately. The high-resolution data was there; the conversion discarded it.

## 2. WinForms: the type says so out loud

`Control.PointToClient` cannot carry a sub-pixel position at all. There is exactly one overload of each method and no `PointF` variant:

```
System.Drawing.Point PointToClient(System.Drawing.Point)
System.Drawing.Point PointToScreen(System.Drawing.Point)

System.Drawing.Point
    X: System.Int32
    Y: System.Int32
```

This is a blunter failure than WPF's, and an easier one to catch — the compiler objects at the call site. The real risk is documentation recommending it.

The fix is the same shape, and simpler: a Per-Monitor V2 WinForms application already works in physical pixels, so there is no scale factor to apply.

```csharp
// WRONG — cannot express a pen position:
var canvasPt = _canvasPanel.PointToClient(new Point((int)pt.DesktopX, (int)pt.DesktopY));

// CORRECT — convert the origin, subtract in floating point:
var origin = _canvasPanel.PointToScreen(Point.Empty);
var canvasPt = new PointF(
    (float)(pt.DesktopX - origin.X),
    (float)(pt.DesktopY - origin.Y));
```

## 3. Avalonia: the return type gives it away

`TopLevel.PointToScreen(Point)` returns a `PixelPoint`, whose members are `int`. Same trap, visible in the signature.

```csharp
// WRONG:
var clientPt = topLevel.PointToClient(new PixelPoint((int)pt.DesktopX, (int)pt.DesktopY));

// CORRECT:
var windowOrigin = topLevel.PointToScreen(new Point(0, 0));
double scale = topLevel.RenderScaling;
var clientPt = new Point((pt.DesktopX - windowOrigin.X) / scale,
                         (pt.DesktopY - windowOrigin.Y) / scale);
```

Avalonia's own pointer handling had this bug internally and fixed it in **11.3**. Applications on earlier versions get quantized pen positions no matter how carefully they do their own conversion.

## 4. Why it survives review

Three things conspire, and the second is the one that does the damage.

**The signature can lie.** WPF's is `Point PointFromScreen(Point)` — all doubles, no hint of an integer. WinForms and Avalonia are honest by comparison; WPF is not.

**The output still has decimals.** On a scaled display the conversion divides by the DPI scale, so an integer input *still* produces a fractional result:

```
701 device px / 1.75 = 400.571428...   ← looks like sub-pixel precision
```

A debug readout showing `Canvas: 400.57, 233.14` looks perfectly healthy and proves nothing whatsoever about the input. A readout like that was, during one investigation, taken as confirmation that coordinates were fine — it could not have detected the problem it was being used to rule out. **If a coordinate readout is being used as evidence, print the raw screen position with decimals, before any scale division.**

**Correct DPI awareness does not help.** Per-Monitor V2 makes these APIs operate in the right *coordinate space*. It does nothing about the truncation. See [Per-Monitor V2 DPI Awareness](per-monitor-v2-dpi-awareness.md).

## 5. How to test for it

Do not eyeball this, and do not use an image-based roughness metric — such a metric is dominated by stroke steepness rather than by quantization, and has produced both false negatives and false positives here.

Measure the turn angle between consecutive segments on the input path:

```python
def mean_turn_angle(points):
    """Mean angle between consecutive segments, in degrees."""
    angles = []
    for i in range(1, len(points) - 1):
        ax, ay = points[i][0] - points[i-1][0], points[i][1] - points[i-1][1]
        bx, by = points[i+1][0] - points[i][0], points[i+1][1] - points[i][1]
        na, nb = math.hypot(ax, ay), math.hypot(bx, by)
        if na < 1e-9 or nb < 1e-9:
            continue
        cos = max(-1, min(1, (ax*bx + ay*by) / (na*nb)))
        angles.append(math.degrees(math.acos(cos)))
    return sum(angles) / len(angles)
```

Reference values for a lattice-quantized path: `atan(1/5)` = 11.31°, `atan(1/3)` = 18.43°, `atan(1/1)` = 45°. A clean digitizer stream on a slow curve sits near 2–4°.

Two assertions are worth keeping permanently.

**Snap test** — no legitimate pen stream lands on whole device pixels:

```csharp
// scale = DPI scale. If this holds for ~100% of a stroke, something upstream quantized.
bool snapped = Math.Abs(canvasX * scale - Math.Round(canvasX * scale)) < 1e-6;
```

**Lossless test** — the stronger of the two. Measure turn angle *before* and *after* a conversion stage. If the stage is lossless, the two are identical:

```
Wintab high-res   turn(input) = 2.69°   turn(after conversion) = 2.69°   ✓
WPF Stylus        turn(input) = 5.32°   turn(after conversion) = 5.32°   ✓
```

This is falsifiable in a way "it looks smooth" is not, and it isolates a single stage instead of judging the whole pipeline at once.

## 6. Two neighbouring bugs with the same symptom

Both of these also present as "the strokes look wrong" and are invisible to coordinate checks, so they are worth ruling out at the same time.

**A surface sized in logical units.** A canvas bitmap allocated from `ActualWidth`/`ActualHeight` (DIPs) rather than physical pixels is magnified to fit. At 1.75× that is a canvas drawn at 57% of the display's resolution. No coordinate precision survives it.

```csharp
double scale = VisualTreeHelper.GetDpi(this).DpiScaleX;
int w = (int)Math.Ceiling(CanvasArea.ActualWidth * scale);
int h = (int)Math.Ceiling(CanvasArea.ActualHeight * scale);

// Declared at the display's DPI, so WPF lays it out at its DIP size
// and presents the pixels 1:1 instead of scaling them.
var bmp = new WriteableBitmap(w, h, 96 * scale, 96 * scale, PixelFormats.Bgra32, null);
```

This is worse in frameworks that magnify without filtering. An egui/`tiny-skia` canvas sized in points and displayed with `TextureOptions::NEAREST` gets hard blocky steps rather than a blur.

**A surface landing on a fractional pixel.** WPF does not round layout to device pixels by default, so an element can be arranged at a fractional device-pixel offset — one canvas landed 0.64px off vertically. WPF then resamples the whole surface to draw it between pixel rows, softening every edge uniformly, while coordinates and resolution both still measure correct.

```xml
<Window UseLayoutRounding="True">
  ...
  <Image RenderOptions.BitmapScalingMode="NearestNeighbor" Stretch="None" />
```

`UseLayoutRounding` is the fix. `NearestNeighbor` is a guard, not a fix: at a correct 1:1 mapping it is identical to the default, but if alignment regresses it surfaces as aliasing rather than as a blur that will be mistaken for a rendering problem.

Note that the offset was `0.00` horizontally and fractional only vertically, so the blur was one-dimensional. A check that scans across a near-vertical stroke measures the axis with no error and reports it clean.

## See also

- [DPI and Pen Coordinates](dpi-and-pen-coordinates.md)
- [Per-Monitor V2 DPI Awareness](per-monitor-v2-dpi-awareness.md)
- [Known Quirks and Gotchas](known-quirks-and-gotchas.md)
