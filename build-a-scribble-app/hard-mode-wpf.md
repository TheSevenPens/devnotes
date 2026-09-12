# Build a Scribble app: WPF (hard mode)

> **Status: complete first draft.** Tracked in [#8](https://github.com/TheSevenPens/devnotes/issues/8).

## Overview

This guide builds the same Scribble application a third time, in WPF. Read one of the two canonical guides first — [Native / C++](canonical-native.md) or [WinForms](canonical-winforms.md) — because this page assumes you have the checks running and a working application to compare against.

One difference from those two paths produces everything hard about this one: **WPF lays out in device-independent pixels rather than device pixels.** Three separate faults follow from that single difference, and all three appeared while `Scribble.Wpf` was being written.

| trap | what breaks | which check catches it |
| --- | --- | --- |
| A conversion method that truncates behind a floating-point signature | the pen position | `L3.conversion-snap`, `L3.conversion-lossless` |
| A surface sized in logical units | the resolution the canvas draws at | `L1.surface-physical`, `L1.presentation-1to1` |
| A surface placed between device pixels | every edge in the canvas at once | `L1.surface-alignment` |

Each one got found and fixed. The sample ships correct today, and passes 9 of 9.

Here are some notes:

- Sections 3, 4 and 5 each name the trap, show the fix, then show the report a real run produces with the fault put back. Every number on this page comes from a run, and each one says which machine produced it
- The library underneath is the same one the canonical path already proved, so a failure here comes from the coordinate model rather than from WinPenKit
- The reference implementation lives in `Scribble.Wpf` and `WinPenKit.Wpf` in WinPenKit
- Section 3 matters more than the rest of this guide set combined. WPF is the one framework where the truncation leaves no trace in a method signature

---

## 1. What changes from the canonical path

Win32 and WinForms both lay out in device pixels. A window 1400 pixels wide reports 1400, a control origin lands on a whole pixel because Windows puts windows on whole pixels, and a bitmap sized from a control measures what the screen measures.

WPF lays out in device-independent pixels, which the framework defines as 1/96 inch. On a display at 225% scaling, one DIP covers 2.25 device pixels. Every number WPF hands you — `ActualWidth`, a `Point` from the stylus stack, an element's offset from its ancestor — arrives in DIPs, and the display scale relating the two changes when the window moves to another monitor.

Three consequences, one per section:

- Converting a desktop position to a canvas position now involves a scale as well as a translation, and WPF's own method for doing so destroys the pen's precision (section 3)
- A bitmap sized from `ActualWidth` measures DIPs, and WPF magnifies it to fill the pixels (section 4)
- Layout in DIPs can place the canvas at a fractional device pixel, and WPF resamples the whole canvas to draw it there (section 5)

Keep one number in your head for the rest of the guide. The measurements below come from a 225% display, so `1 / 2.25 = 0.444`: a canvas that gets this wrong draws at 44% of the resolution the screen can show.

## 2. Per-Monitor V2 needs a manifest here

WPF does not offer an API call or an SDK property for DPI awareness. Declare it in an application manifest:

```xml
<compatibility xmlns="urn:schemas-microsoft-com:compatibility.v1">
  <application>
    <supportedOS Id="{8e0f7a12-bfb3-4fe8-b9a5-48fd50a15a9a}" />
  </application>
</compatibility>

<application xmlns="urn:schemas-microsoft-com:asm.v3">
  <windowsSettings>
    <dpiAwareness xmlns="http://schemas.microsoft.com/SMI/2016/WindowsSettings">PerMonitorV2</dpiAwareness>
    <dpiAware xmlns="http://schemas.microsoft.com/SMI/2005/WindowsSettings">true/pm</dpiAware>
  </windowsSettings>
</application>
```

```xml
<ApplicationManifest>app.manifest</ApplicationManifest>
```

**The `supportedOS` entry is not decoration.** Windows ignores the `PerMonitorV2` setting unless the manifest also declares Windows 10 compatibility with that GUID. Leave it out and the process runs at System awareness, which reports the primary display's DPI applied to every display.

Both `dpiAwareness` and `dpiAware` appear above because they target different Windows versions. Windows 10 1703 and later read the first; earlier builds read the second.

Of the six Scribble samples, this is the only one that needed a manifest written by hand. Win32 calls `SetProcessDpiAwarenessContext`, WinForms sets an SDK property, WinUI ships its own manifest, and Avalonia and eframe handle it inside the framework. The omission showed up here and nowhere else.

### Verify before proceeding

```
Scribble.Wpf.exe --selftest
```

```
[PASS] L0.dpi-awareness        PerMonitorV2
```

`L0.scale` should report the display's actual scale, not `1.00x`. A `1.00x` reading on a scaled display means Windows is virtualizing coordinates for the process, and every measurement after that describes a display that does not exist.

The window has to be shown before the Level 1 checks can run, as in WinForms. WPF's equivalent of `Shown` is `ContentRendered`:

```csharp
window.ContentRendered += (_, _) =>
{
    int code = window.RunSelfTest(replay ? replayPath : null).Emit();
    Shutdown(code);
};
window.Show();
```

`Shutdown(code)` carries the exit code out of the application. `Application.Current.Shutdown()` with no argument exits 0 regardless of the report.

## 3. Trap one: a conversion that truncates behind a floating-point signature

WPF offers the conversion this application needs:

```csharp
public Point PointFromScreen(Point point);
public Point PointToScreen(Point point);
```

`System.Windows.Point` holds two `double`s. Both methods take one and return one, so the signature promises to carry a sub-pixel position in either direction.

**Neither method keeps it.** Both route the value through Win32 `ClientToScreen` and `ScreenToClient`, which take a `POINT` of two 32-bit integers. Every coordinate that passes through either method comes back rounded to a whole device pixel.

Nothing in the signature says so. Nothing at runtime reports it. The value arrives as a `double` and leaves as a `double`, and the digits after the decimal point have been replaced.

### Why this stays hidden longer here than anywhere else

Mouse positions arrive as whole numbers already, so rounding them changes nothing. Every WPF application that has only ever taken mouse input has used these methods correctly without knowing what they do.

A pen is the opposite case. A digitizer context reports positions like `2302.33`, and the fractional part is the one thing separating a pen from a mouse.

The trap survives a careless check as well. Measured on the 175% display used during this investigation, a position readout showed values like `400.571`, which reads as sub-pixel precision. The arithmetic produces that: `701 / 1.75 = 400.571`. A whole-numbered device position, divided by a display scale, produces a decimal DIP value whatever happened upstream. **A readout downstream of the division cannot detect truncation upstream of it.** I used exactly that readout to conclude WPF's coordinates were sound, and the conclusion was wrong.

### Convert the origin yourself, then subtract and divide

`WinPenKit.Wpf.WpfCoordinates.GetTransform` returns the canvas origin in desktop device pixels along with the scale, and it makes exactly one Win32 call:

```csharp
if (PresentationSource.FromVisual(element) is not HwndSource source ||
    source.RootVisual is null)
{
    return null;
}

var clientOrigin = new POINT { X = 0, Y = 0 };
if (!ClientToScreen(source.Handle, ref clientOrigin))
    return null;

// Where the element sits inside the window, in DIPs. A GeneralTransform, so this keeps
// its fractional part.
Point dipOffset = element
    .TransformToAncestor(source.RootVisual)
    .Transform(new Point(0, 0));

var dpi = VisualTreeHelper.GetDpi(element);

return (clientOrigin.X + dipOffset.X * dpi.DpiScaleX,
        clientOrigin.Y + dipOffset.Y * dpi.DpiScaleY,
        dpi.DpiScaleX,
        dpi.DpiScaleY);
```

Three pieces, and each one handles a quantity that survives the type it travels in:

| piece | what it produces | why the type costs nothing |
| --- | --- | --- |
| `ClientToScreen` | the window's client origin on the desktop | Windows places windows at whole-pixel coordinates |
| `TransformToAncestor` | the element's offset inside the window, in DIPs | a `GeneralTransform` keeps its fractional part |
| `VisualTreeHelper.GetDpi` | the scale relating the two | a `DpiScale` holds `double`s and no Win32 call touches it |

The pen position never enters any of them. The application subtracts the origin and divides by the scale itself:

```csharp
private (double X, double Y) DesktopToCanvas(double x, double y) =>
    ((x - _canvasOriginX) / _renderScale, (y - _canvasOriginY) / _renderScale);
```

Follow this in any framework:

> **Let the framework convert the origin. Subtract it from the pen position yourself.** The origin is a whole number, so an integer API returns it unchanged. The pen position keeps its fractional part because no API touches it.

Refresh the origin whenever the surface is rebuilt, which covers a resize, a move to another display, and a DPI change.

### What the fault produces

Replacing the conversion above with `PointFromScreen` and running `--replay`, on a 225% display against the 480-point reference recording:

```
[PASS] L2.recording-subpixel   0.0% of 480 recorded points are on whole pixels
[FAIL] L3.conversion-snap      100.0% of converted points land on whole device pixels  <- an integer-typed API is truncating the position
[FAIL] L3.conversion-lossless  mean turn angle in 0.74 deg, out 18.71 deg (delta 17.97)  <- the conversion changed the shape of the path
RESULT 7/9 passed
```

Every point snapped. The mean angle between consecutive segments went from 0.74 degrees to 18.71.

A live stream measured earlier in this investigation, on a 175% display through a Wintab digitizer context, produced the same result at a different magnitude: 4.11 degrees in, 17.51 degrees out, and 3014 of 3014 points on whole device pixels. The exact output angle depends on the display scale and on how densely the pen samples; that every point snaps does not.

On screen a reader sees a stroke made of short straight segments meeting at visible angles, worst on slow curves. It looks like a brush engine problem and survives any amount of work on the brush engine.

### Verify

```
Scribble.Wpf.exe --replay
```

```
[PASS] L3.conversion-snap      0.0% of converted points land on whole device pixels
[PASS] L3.conversion-lossless  mean turn angle in 0.74 deg, out 0.74 deg (delta 0.00)
```

`L3.conversion-lossless` compares the output against its own input, so it needs no threshold and no reference value. A translation and a uniform scale both preserve angles exactly, which is why a correct implementation reproduces the input angle to two decimal places even though this framework's conversion divides as well as subtracts.

## 4. Trap two: a surface sized in logical units

`ActualWidth` and `ActualHeight` report DIPs. A bitmap sized from them holds one pixel per DIP, which on a 225% display means it holds one pixel for every 2.25 the screen can show. WPF then magnifies that bitmap to fill the space, and every stroke in it gets 2.25 times wider than drawn, with soft edges.

Size the bitmap in device pixels:

```csharp
double dipW = CanvasArea.ActualWidth;
double dipH = CanvasArea.ActualHeight;

double scale = VisualTreeHelper.GetDpi(this).DpiScaleX;
if (scale <= 0) scale = 1.0;

int w = (int)Math.Ceiling(dipW * scale);
int h = (int)Math.Ceiling(dipH * scale);

_skBitmap = new SKBitmap(w, h, SKColorType.Bgra8888, SKAlphaType.Premul);
_skCanvas = new SKCanvas(_skBitmap);

// Drawing code keeps working in DIPs; the canvas transform is the only thing that
// knows about display scaling.
_skCanvas.Scale((float)scale);
```

`_skCanvas.Scale` keeps the rest of the drawing code in DIPs, which matches the units the stylus stack and the layout system already use. One transform holds all the knowledge of display scaling.

### The WriteableBitmap has to declare the display's DPI

```csharp
_wpfBitmap = new WriteableBitmap(w, h, 96 * scale, 96 * scale, PixelFormats.Bgra32, null);
```

WPF lays an `Image` out at the bitmap's DIP size, which it computes as the pixel count divided by the DPI the bitmap declares. Declare 96 and a 2672-pixel bitmap asks for 2672 DIPs of layout space, which covers 6012 device pixels, and WPF scales the bitmap up to fill them. Declare `96 * scale` and the same bitmap asks for 1188 DIPs, which covers exactly the 2672 device pixels it holds.

So the two settings have to agree. Sizing the bitmap correctly and declaring it at 96 produces a correctly sized bitmap magnified on the way to the screen, which looks the same as never having sized it correctly.

### Preserving content across a resize needs the transform removed

```csharp
_skCanvas.Save();
_skCanvas.ResetMatrix();
_skCanvas.DrawBitmap(oldBitmap, 0, 0);
_skCanvas.Restore();
```

The old bitmap already holds device pixels. Drawing it through a canvas carrying `Scale(2.25)` would magnify the preserved content by 2.25 on every resize.

### What the fault produces

Sizing the bitmap from DIPs, dropping `_skCanvas.Scale`, and declaring the `WriteableBitmap` at 96:

```
[FAIL] L1.surface-physical     bitmap 1188x547, expected 2672x1230 (= ceil(1188x547 logical x 2.25))  <- rendering at 44% of display resolution
[FAIL] L1.presentation-1to1    bitmap 1188x547 presented at 2673.0x1231.0 device px  <- magnified or shrunk on the way to the screen
```

Two checks, one fault, and they describe different halves of it: the bitmap holds too few pixels, and WPF stretches those pixels to cover the space. The coordinate checks all still pass. So does the pen stream. A canvas drawing at 44% of the display's resolution produces a bumpy stroke through every input API at once, which reads as a problem with the pen rather than with the surface — and that reading is what kept this fault alive while the coordinate work went on around it.

This is the fault that made every input API look equally bad in `Scribble.Wpf`, and it hid the coordinate truncation of section 3 underneath itself.

### Verify

```
[PASS] L1.surface-physical     bitmap 2672x1230, expected 2672x1230 (= ceil(1188x547 logical x 2.25))
[PASS] L1.presentation-1to1    bitmap 2672x1230 presented at 2672.0x1230.0 device px
```

Check the second one by measuring rather than by reasoning. `Stretch="None"` means WPF presents the image at the bitmap's own DIP size, and the sample computes the presented size from `DrawImage.ActualWidth * scale` instead of assuming the setting did what it claims. A correctly sized bitmap can still reach the screen scaled, and this is the check that says so.

## 5. Trap three: a surface placed between device pixels

WPF does not round layout positions to whole device pixels by default. A canvas that sits below a ribbon takes its position from whatever height the ribbon's content produced, and that height in DIPs times the display scale need not land on a whole pixel.

When it does not, WPF resamples the entire canvas bitmap to draw it at the fractional offset. Every edge in the drawing softens by the same amount, at once.

Turn on layout rounding at the window:

```xml
<Window x:Class="Scribble.Wpf.MainWindow"
        ...
        UseLayoutRounding="True">
```

### NearestNeighbor guards the fault, and does not fix it

```xml
<Image x:Name="DrawImage" Stretch="None"
       RenderOptions.BitmapScalingMode="NearestNeighbor"
       HorizontalAlignment="Left" VerticalAlignment="Top" />
```

`UseLayoutRounding` keeps the offset whole. `BitmapScalingMode="NearestNeighbor"` changes what a regression looks like: with the default mode WPF resamples and the canvas goes soft, which reads as a brush engine problem; with `NearestNeighbor` the same regression produces visible aliasing, which reads as a layout problem. Setting it without `UseLayoutRounding` leaves the canvas misplaced and merely changes how the damage appears.

### What the fault produces

Removing `UseLayoutRounding` from the window:

```
[FAIL] L1.surface-alignment    origin 69.00,385.68px  <- fractional on y; the whole surface is resampled to draw it
```

**The fault is one-dimensional.** The x origin landed on a whole pixel and the y origin landed 0.68 of a pixel below one, because only the vertical position depends on the ribbon's content height. The instance found during this investigation, on a 175% display, measured 0.00 horizontally and 0.64 vertically.

That detail cost real time. A check written to scan across a near-vertical stroke and measure how sharply its edges fell off reported the canvas clean, because it sampled along the axis that had no error. **A measurement taken along one axis says nothing about the other.** [Diagnosing a bad stroke](diagnosing-a-bad-stroke.md) covers this and the other measurements that mislead.

### Verify

```
[PASS] L1.surface-alignment    origin 399.00,716.00px
```

Both numbers whole. Resize the window, drag it to a display with a different scale, and run the check again — the ribbon's height in device pixels changes with the scale, so a layout that rounds at one scale can miss at another.

## 6. WPF's own stylus stack

`WpfStylusSession` takes input through WPF's stylus events rather than through Wintab or WM_POINTER. Two things about it matter.

### The truncation appears again, running the other way

```csharp
var stylusPoints = e.GetStylusPoints(_element);

// Once per event, not once per point: the element has not moved between them.
if (WpfCoordinates.GetTransform(_element) is not { } xf)
    return;

foreach (var sp in stylusPoints)
{
    var screenPt = new Point(
        xf.OriginX + sp.X * xf.ScaleX,
        xf.OriginY + sp.Y * xf.ScaleY);
```

`GetStylusPoints` returns good sub-pixel DIPs relative to the element. The session converts them outward, to desktop device pixels, so a WinPenKit consumer receives the same units from every API.

Section 3 met the truncation converting inward, from desktop pixels to canvas DIPs. Here the conversion runs outward, and `Visual.PointToScreen` would truncate exactly the same way — destroying the precision the stylus stack just delivered, before the position ever leaves the session. The same `GetTransform` call covers both directions, because a translation and a scale invert without loss.

### Its resolution still trails a Wintab digitizer context

Measured on the 175% display with a real tablet: the WPF stylus stack produced a mean turn angle of 5.32 degrees against 2.69 degrees from a Wintab digitizer context on the same hardware, with both conversions correct.

That difference belongs to the stack rather than to your code. WPF's stylus input travels through a different path with its own sampling, and no application-side change closes the gap. Offer both APIs and let the person drawing decide. A stroke that improves when they switch to the digitizer context tells them where the limit sits.

## 7. Handing it to a person

A passing `--replay` establishes this much:

```
SELFTEST Scribble.Wpf
[PASS] L0.dpi-awareness        PerMonitorV2
[PASS] L0.window-placement     client 2672x1496 at 399,450; work area 3840x2052 at 0,0
[PASS] L0.scale                2.25x
[PASS] L1.surface-physical     bitmap 2672x1230, expected 2672x1230 (= ceil(1188x547 logical x 2.25))
[PASS] L1.surface-alignment    origin 399.00,716.00px
[PASS] L1.presentation-1to1    bitmap 2672x1230 presented at 2672.0x1230.0 device px
[PASS] L2.recording-subpixel   0.0% of 480 recorded points are on whole pixels
[PASS] L3.conversion-snap      0.0% of converted points land on whole device pixels
[PASS] L3.conversion-lossless  mean turn angle in 0.74 deg, out 0.74 deg (delta 0.00)
RESULT 9/9 passed
```

All three traps on this page trip a check in that report. That is the whole reason the canonical guides made you write the checks in a framework where they could not fail.

### What no check covers

- **Wintab.** Synthetic pen injection never reaches the driver, so no Wintab code path has run.
- **The WPF stylus stack.** `WpfStylusSession` needs a real pen over a real digitizer as much as Wintab does.
- **The drawing.** The checks measure where the stroke goes, not what it looks like.
- **Whether the stroke feels right.** Latency, weight, and how a taper answers a change in pressure.
- **A fault nobody has thought of.** The checks cover faults already found.

### Ask for these five things

WPF earns one ask more than the other two paths, because two of its three traps only appear when the display scale changes:

| ask | what it tests |
| --- | --- |
| Draw with each API in turn, on a slow gentle curve | the Wintab paths and the WPF stylus stack, and how they compare |
| Click to another application, come back, draw immediately | the Wintab overlap-order handling. The first stroke is the one that goes missing |
| Drag the window to a display with a different scale, then draw | the whole of sections 3, 4 and 5 at a second scale factor |
| Resize the window slowly while watching the canvas edge | layout rounding, which can hold at one size and miss at another |
| Press hard, then lift slowly to nothing | the pressure curve and the taper |

The third one matters most here. Every scale-dependent fault on this page passes at 100% scaling, so a machine at 100% tests almost nothing this guide is about.

### Read the answers carefully

**Treat "it looks wrong" as real even when the report says `9/9`.** The checks cover three stages and the five things above sit outside all of them.

**"It looks right" establishes less.** A wide brush, a fast stroke, or a display at 100% scaling all hide faults that a slow stroke at 3x zoom on a scaled display would show.

[Diagnosing a bad stroke](diagnosing-a-bad-stroke.md) covers the whole of this: the four symptoms, which stage each one comes from, and the measurements that mislead.

### Where to go next

[Framework Coordinate Conversion](../pen-input-on-windows/implementation-notes/framework-coordinate-conversion.md) covers the same conversion in Win32, WinForms, Avalonia and WPF side by side, with the signature of each.

---

## To write

- [ ] Re-measure the WPF stylus stack against a Wintab digitizer context on the 225% display, so both figures in section 6 come from the same machine as the rest of the page
- [ ] Confirm whether `UseLayoutRounding` on the canvas element alone suffices, rather than on the window
- [ ] Decide whether section 4's `ResetMatrix` detail belongs here or in a SkiaSharp note
