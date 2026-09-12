# Build a Scribble app: WinForms

> **Status: complete first draft.** Tracked in [#8](https://github.com/TheSevenPens/devnotes/issues/8).

## Overview

By the end you have a WinForms application that opens a window, takes pen input through WinPenKit, and draws strokes that follow the pen below the width of a screen pixel. It also reports its own state as text, so you can tell a correct canvas from a broken one without looking at the screen.

The same application as the [native guide](canonical-native.md) builds. What changes between the two paths:

| | Native / C++ | WinForms |
| --- | --- | --- |
| coordinate model | physical pixels | physical pixels, the same |
| acceptance checks | ten | the same ten |
| library surface | a flat C API you call directly | a managed one |
| getting to a first window | MSBuild, a Windows SDK, two traps in the project file | `dotnet new winforms` |

You will build, in this order:

- A project, with Per-Monitor V2 set by the SDK
- Diagnostics that print what the application thinks its surface measures
- A canvas panel and a bitmap
- A pen session
- The conversion from desktop coordinates to canvas coordinates
- The stroke itself

Here are some notes:

- Take this path if you would rather not set up a C++ toolchain. It reaches a working application in less time and teaches the same coordinate model
- Section 5 holds the main lesson of this guide and states it in full. Reading the native guide first helps, and this path does not require it
- The reference implementation lives in `Scribble.WinForms` in WinPenKit
- Where WinForms differs from C++ in a way that changes what you write, the section says so

---

## 1. Project setup and the DPI mode

```
dotnet new winforms -n Scribble.WinForms
```

Four properties and three references:

```xml
<TargetFramework>net10.0-windows</TargetFramework>
<UseWindowsForms>true</UseWindowsForms>
<ApplicationHighDpiMode>PerMonitorV2</ApplicationHighDpiMode>
<AllowUnsafeBlocks>true</AllowUnsafeBlocks>
```

```xml
<PackageReference Include="SkiaSharp" Version="3.116.1" />
<ProjectReference Include="..\WinPenKit\WinPenKit.csproj" />
<ProjectReference Include="..\WinPenKit.WinForms\WinPenKit.WinForms.csproj" />
```

`AllowUnsafeBlocks` covers the bitmap copy in section 3. SkiaSharp draws the stroke in section 6.

### The SDK makes the DPI call for you

The native guide spent a section on `SetProcessDpiAwarenessContext` and on calling it before any window exists. `ApplicationHighDpiMode` does that work here: the SDK writes the setting into the generated `ApplicationConfiguration.Initialize()`, and `Main` calls that before constructing the form.

```csharp
static int Main(string[] args)
{
    ApplicationConfiguration.Initialize();   // the DPI call happens in here
    var form = new MainForm();
    ...
```

The ordering problem disappears, and a different problem takes its place. The property sits in a file you edit once; `Main` you edit often. Delete or reorder `ApplicationConfiguration.Initialize()` during some later change and the awareness call goes with it. The application still runs, the window still opens, and Windows starts reporting scaled coordinates instead of physical ones.

Nothing announces the loss. [Per-Monitor V2 DPI Awareness](../pen-input-on-windows/implementation-notes/per-monitor-v2-dpi-awareness.md) covers what the lower levels report and what a pen does under them. Section 2 builds the check that catches it.

### Verify before proceeding

```
dotnet run
```

A window opens. Nothing draws yet, and nothing should.

## 2. Diagnostics first

Build the reporting apparatus before the thing it reports on.

A stroke that looks wrong tells you something failed. A printed surface size tells you *which stage* failed. Writing the checks first takes about an hour, and it replaces a much longer stretch of guessing later.

A second reason decides the ordering. A build server, or an AI agent following a guide like this one, reads text and cannot look at a screen. Anything those two can check has to arrive as text.

`WinPenKit.Diagnostics.SelfTest` holds the implementation, and the same check identifiers appear in every Scribble sample. The levels divide by what has to exist before each one can run:

| level | covers | available |
| --- | --- | --- |
| **L0** | DPI awareness, window placement, display scale | now |
| **L1** | surface size, pixel alignment, 1:1 presentation | after section 3 builds a surface |
| **L2, L3** | the pen stream and the coordinate conversion | after section 5 converts anything |

### The form has to be shown before Level 1 can run

The native path runs its checks inline: by the time `wWinMain` reaches the message loop, `WM_SIZE` has arrived and the bitmap exists. WinForms defers layout. `Panel.Width` reports a design-time value until the first layout pass finishes, so checks that run before then measure a surface the application has not built yet.

Show the form, run the checks from `Shown`, then close it:

```csharp
static int Main(string[] args)
{
    ApplicationConfiguration.Initialize();

    var form = new MainForm();

    bool replay = StrokeReplay.Requested(args, out string? replayPath);
    if (!SelfTest.Requested(args) && !replay)
    {
        Application.Run(form);
        return 0;
    }

    int code = 0;
    form.Shown += (_, _) =>
    {
        code = form.RunSelfTest(replay ? replayPath : null).Emit();
        form.Close();
    };
    Application.Run(form);
    return code;
}
```

A `--selftest` run therefore opens a window for a moment and closes it. Accept the flicker: the alternative measures a panel that has not been laid out.

### Return the exit code

Two ways to lose the result, both of which cost time in this project:

- **`Main` has to return `int`, and the value has to reach the return statement.** A `Main` that ends in `return 0` regardless throws the report away, and every run claims success. That bug shipped in PenDynamicsLab and survived until someone made a check fail on purpose.
- **A GUI binary does not block the caller.** PowerShell's call operator returns immediately and leaves `$LASTEXITCODE` empty, so a script that branches on it passes whatever the report said. Use `Start-Process -Wait -PassThru` and read `ExitCode`.

Both produce a check that cannot fail, which is worth less than no check: it reports success and someone believes it.

### Verify before proceeding

```
Scribble.WinForms.exe --selftest
```

Level 0 should report `PerMonitorV2`, a window inside the work area, and the display scale. That confirms section 1 as well, which you had no way to check when you wrote it.

Watch what the process does as much as what it prints. The run has to exit on its own. A window that opens and stays open means the flag never took effect, and the most likely cause is a binary older than the code that handles it — which is how this guide's first attempt at a `--replay` run went, against a `Release` build compiled before the flag existed.

## 3. A canvas panel and a bitmap

### A panel that does not flicker

`Control.DoubleBuffered` is protected, so a plain `Panel` cannot have it set from outside. Subclass:

```csharp
internal sealed class DoubleBufferedPanel : Panel
{
    public DoubleBufferedPanel() => DoubleBuffered = true;
}
```

```csharp
_canvasPanel = new DoubleBufferedPanel
{
    Dock = DockStyle.Fill,
    BackColor = Color.FromArgb(0xF0, 0xF0, 0xF0)
};
```

### Layout handles the ribbon offset

The native guide subtracted a ribbon height by hand, and carried that second subtraction into its coordinate conversion. `DockStyle.Fill` removes it. The panel occupies whatever the ribbon leaves, and its own screen origin already accounts for the ribbon, so section 5 subtracts one thing rather than two.

### Size the bitmap from the panel

```csharp
int w = _canvasPanel.Width;
int h = _canvasPanel.Height;
if (w <= 0 || h <= 0) return;

_skBitmap = new SKBitmap(w, h, SKColorType.Bgra8888, SKAlphaType.Premul);
_skCanvas = new SKCanvas(_skBitmap);
```

`Panel.Width` and `Panel.Height` hold physical pixels, because a Per-Monitor V2 WinForms application lays out in physical pixels. The bitmap therefore holds one pixel per screen pixel without you converting anything.

Rebuild the bitmap from `Resize`, and copy the old contents in at the origin so a resize does not clear the drawing.

### WinForms cannot paint an SKBitmap

Skia owns the pixels; GDI+ does the painting. Copy between them:

```csharp
_gfxBitmap = new Bitmap(w, h, PixelFormat.Format32bppPArgb);
```

`Format32bppPArgb` matches `SKColorType.Bgra8888` with `SKAlphaType.Premul` byte for byte on x64, which makes the copy a single `Buffer.MemoryCopy` rather than a per-pixel conversion. Choose a different pair and you pay for a format conversion on every frame.

Then paint it:

```csharp
private void CanvasPanel_Paint(object? sender, PaintEventArgs e)
{
    if (_gfxBitmap != null)
        e.Graphics.DrawImageUnscaled(_gfxBitmap, 0, 0);
}
```

**`DrawImageUnscaled`, not `DrawImage`.** `DrawImage` fits the bitmap to a destination rectangle and resamples it to get there. The bitmap already measures exactly what the panel measures, so any resampling here softens the stroke for no gain.

### Three of the six checks cannot fail on this path

Section 2 listed three L1 checks: surface size, pixel alignment, and 1:1 presentation. All three pass here, and they pass for structural reasons rather than because you did something right.

| check | why it passes in WinForms |
| --- | --- |
| surface size | `Panel.Width` reports physical pixels, so no second unit exists to confuse it with |
| pixel alignment | a control origin is an integer; WinForms has no layout that can place the panel between pixels |
| 1:1 presentation | `DrawImageUnscaled` copies pixels without scaling |

Every one of those fails in a framework that lays out in logical units. `Scribble.Wpf`, `Scribble.Avalonia`, `Scribble.WinUI` and `Scribble.Rust` each shipped with at least one of them broken, and two of those went unnoticed after a person had inspected the strokes and approved them.

So the checks earn their place on this path by covering a stage this framework cannot break, which sounds like waste and is not. Write them here, where they pass, and you have a working instrument before you reach a framework that needs one. [Build a Scribble app: WPF](hard-mode-wpf.md) is that framework.

### Verify before proceeding

```
Scribble.WinForms.exe --selftest
```

All six L0 and L1 checks should pass. Resize the window and run it again: the surface tracks the panel, and a window dragged partly off the display fails `L0.window-placement` rather than silently accepting pen input that never arrives.

## 4. Opening a pen session

```csharp
_session = PenSessionFactory.Create(api);

var error = _session.Start(Handle);
if (error != null)
{
    Text = $"Scribble WinForms - {error}";   // put it where you will see it
    _session.Dispose();
    _session = null;
    return;
}
```

`Start` returns `null` on success and an error string otherwise. Put that string somewhere visible — the sample writes it into the title bar. A session that failed to start looks identical to a session receiving nothing.

### WM_POINTER needs the WinForms-specific session

`PenSessionFactory.GetAvailableApis()` reports what the machine offers, and one entry needs replacing before you show the list:

```csharp
var allApis = PenSessionFactory.GetAvailableApis();
var apiList = allApis.Where(a => a != InputApi.WmPointer).ToList();
apiList.Add(InputApi.WinFormsPointer);
```

`InputApi.WmPointer` subclasses the window from native code, which WinForms does not tolerate. `WinFormsPointerSession` reaches the same messages through a `NativeWindow` and a `WndProc` override, and it takes the control rather than a handle:

```csharp
_session = api == InputApi.WinFormsPointer
    ? new WinFormsPointerSession(this)
    : PenSessionFactory.Create(api);
```

The Wintab entries need no equivalent. Three APIs matter for this application:

| API | reports positions in | use it |
| --- | --- | --- |
| `WintabDigitizer` | tablet-native units, converted to sub-pixel desktop pixels | by default, when a tablet is present |
| `WintabSystem` | whole screen pixels | to compare against, and to see what quantization looks like |
| `WinFormsPointer` | HIMETRIC, converted to sub-pixel desktop pixels | when Windows Ink suits you better than Wintab |

**Wintab system mode arrives quantized.** The driver rounds to whole screen pixels before your code runs, so no application-side fix exists. Offer it in your selector anyway. Drawing the same stroke under both contexts takes ten seconds, and a stroke that comes out faceted under system mode and smooth under the digitizer context places the fault in the driver rather than in your code.

### Tell the session when the form is activated

```csharp
Activated += (_, _) => _session?.OnActivated();
```

Wintab delivers packets to whichever context sits on top of the driver's overlap order. Losing focus drops yours down that order, and regaining focus does not put it back. Without this line the first stroke after returning to your application disappears, and every stroke after it draws normally.

The pointer-based APIs need nothing here; Windows routes their input by window. The call costs nothing when it does not apply. [Wintab Gotchas](../pen-input-on-windows/implementation-notes/wintab-gotchas.md) covers the rest of the driver's behaviour.

### Drain on a timer

```csharp
private readonly System.Windows.Forms.Timer _renderTimer = new() { Interval = 16 };
...
var points = _session.DrainPoints();
```

Each call empties the queue. Draining on a timer rather than per message keeps the drawing rate independent of the packet rate.

### Count what arrives

Show a point count in the ribbon before you draw anything with the data. Three readings, each meaning something different:

| reading | meaning |
| --- | --- |
| no points | nothing arrives. Look at the session, the selected API, and the error string from `Start` |
| points arrive, none inside the canvas | the conversion puts them outside the panel. Section 5 |
| points arrive and convert, nothing visible | look at the surface or the brush |

Without those numbers all three look the same from the outside: a blank canvas. Reading code to work out which of the three you have takes far longer than printing a count.

### Verify before proceeding

Draw with a pen. The count climbs, and the telemetry shows real pressure rather than `--`.

Nothing draws yet. Section 5 converts those positions, and section 6 puts ink on the surface.

## 5. Desktop pixels to canvas pixels

A `PenPoint` carries its position as two `double`s, and it does so because a digitizer resolves finer than a screen pixel. Preserving that through the conversion to canvas coordinates is the single thing this guide exists to teach.

### WinForms offers exactly two conversions, and both take integers

Ask the framework what it has. Reflecting over `System.Windows.Forms.Control` on .NET 10.0.11:

```
System.Drawing.Point PointToClient(System.Drawing.Point p)
System.Drawing.Point PointToScreen(System.Drawing.Point p)
```

Two methods, one overload each. `System.Drawing.Point` holds two `Int32` fields. `System.Drawing.PointF` exists in the same namespace, holds two `float`s, and no overload accepts one.

So the framework offers no way to convert a sub-pixel position between coordinate spaces. Whatever you pass has to become whole numbers first.

### One of the two is safe, and the difference is what you pass

Put the pen position through `PointToClient` and you round it to construct the argument:

```csharp
// The precision ends on this line, before the conversion runs.
var p = _canvasPanel.PointToClient(
    new Point((int)pt.DesktopX, (int)pt.DesktopY));
```

The cast discards everything after the decimal point. `PointToClient` then returns a correct answer to a question asked in the wrong units, and no error appears anywhere.

Pass the panel's origin through the same integer type and you lose nothing:

```csharp
var origin = _canvasPanel.PointToScreen(Point.Empty);
var canvasPt = new PointF(
    (float)(pt.DesktopX - origin.X),
    (float)(pt.DesktopY - origin.Y));
```

`Point.Empty` holds `(0, 0)` exactly, so the argument loses nothing on the way in. The return value gives the panel's position on the desktop, and **Windows places every window at whole-pixel screen coordinates**, so that number has no fractional part to lose on the way out.

Both calls appear in the same file, use the same integer type, and one of them is correct. What separates them is the value you hand over, not the method you pick.

### The conversion is a subtraction

```
canvas position = desktop position - where the canvas sits on the desktop
```

Only the framework can tell you the second term, and `PointToScreen` is how you ask. Do the subtraction yourself, in floating point.

Follow this in any framework:

> **Let the framework convert the origin. Subtract it from the pen position yourself.** The origin is a whole number, so an integer API returns it unchanged. The pen position keeps its fractional part because no API touches it.

### Keep the result in a float type

```csharp
private PointF? _lastCanvasPoint;
```

Declare that `Point` and you have rebuilt the problem one line further down. The conversion preserved the fractional part and the field would throw it away, with the same faceted stroke at the end of it.

### Every framework has this problem

Each one makes the integers easier or harder to see:

| framework | the API | how visible |
| --- | --- | --- |
| Win32 | `ScreenToClient(POINT*)` | the struct sits in the signature |
| WinForms | `Control.PointToClient(Point)` | `System.Drawing.Point` has `int` members, and no `PointF` overload exists |
| Avalonia | `TopLevel.PointToScreen` | returns `PixelPoint`, whose members are `int` |
| WPF | `Visual.PointFromScreen(Point)` | **invisible**: takes and returns two `double`s, and truncates internally through a Win32 `POINT` |

WinForms sits one step along from Win32. The type still says `int`, and you have to read the parameter type rather than the method name to see it. WPF gives no sign at all — a `Point` of two `double`s goes in and comes out — which is why [Build a Scribble app: WPF](hard-mode-wpf.md) comes after this one rather than before. [Framework Coordinate Conversion](../pen-input-on-windows/implementation-notes/framework-coordinate-conversion.md) covers all four in detail.

### What it costs to get this wrong

The reference recording holds 480 points, none of which sits on a whole pixel. Replacing the subtraction above with a `PointToClient` call and running `--replay` produces this:

```
[PASS] L2.recording-subpixel   0.0% of 480 recorded points are on whole pixels
[FAIL] L3.conversion-snap      100.0% of converted points land on whole device pixels  <- an integer-typed API is truncating the position
[FAIL] L3.conversion-lossless  mean turn angle in 0.74 deg, out 19.35 deg (delta 18.61)  <- the conversion changed the shape of the path
RESULT 7/9 passed
```

Every point snapped, and the mean angle between consecutive segments went from 0.74 degrees to 19.35. The exact output angle shifts a little with the window position and with whether the code truncates or rounds. The size of the change does not.

On screen that reads as a stroke made of short straight segments meeting at visible angles, worst on slow curves. It looks like a brush engine problem and survives any amount of work on the brush engine.

### Verify

```
Scribble.WinForms.exe --replay
```

```
SELFTEST Scribble.WinForms
[PASS] L0.dpi-awareness         PerMonitorV2
[PASS] L0.window-placement      client 1172x621 at 289,340; work area 3840x2052 at 0,0
[PASS] L0.scale                 2.25x
[PASS] L1.surface-physical      bitmap 1172x431, expected 1172x431 (= ceil(1172x431 logical x 1.00))
[PASS] L1.surface-alignment     origin 289.00,530.00px
[PASS] L1.presentation-1to1     bitmap 1172x431 presented at 1172.0x431.0 device px
[PASS] L2.recording-subpixel    0.0% of 480 recorded points are on whole pixels
[PASS] L3.conversion-snap       0.0% of converted points land on whole device pixels
[PASS] L3.conversion-lossless   mean turn angle in 0.74 deg, out 0.74 deg (delta 0.00)
[PASS] L3.origin-tracks-window  moved 37,23px; conversion followed
RESULT 10/10 passed
```

Note `L0.scale` reporting `2.25x` while `L1.surface-physical` compares against a ratio of `1.00`. Both numbers are correct and they measure different things: the display runs at 2.25x, and WinForms lays out in physical pixels, so the bitmap and the panel share one unit. Pass the display scale into that check instead and it compares the bitmap against a size the application never meant to produce.

`L3.conversion-lossless` makes the strongest statement available about a coordinate conversion. A translation preserves angles exactly, so a correct implementation reproduces the input's turn angle to two decimal places. It needs no threshold and no reference value: it compares the output against its own input.

Run the replay through the same method the pen uses. A replay with its own copy of the arithmetic tests only itself:

```csharp
private (double X, double Y) DesktopToCanvas(double x, double y)
{
    var origin = _canvasPanel.PointToScreen(Point.Empty);
    return (x - origin.X, y - origin.Y);
}
```

### A tenth check, for the term the others cannot see

A conversion is an origin and a scale, and every check above holds the window still. That leaves the origin uncovered: the replay places its input relative to the origin your application reports, then your application subtracts the same value back off, so an origin wrong by any amount cancels itself exactly. `L1.surface-alignment` does not close the gap either, because it asks whether the origin is a whole number rather than whether it is the right one.

```
[PASS] L3.origin-tracks-window  moved 37,23px; conversion followed
```

That check moves the window a known distance and converts the same desktop point again. A conversion that reads the origin fresh reports a position shifted by exactly that distance. One that cached the origin reports what it did before, because nothing told it the window moved.

`Scribble.Wpf` shipped with that fault: it cached the origin when it built its bitmap, dragging the window raised no size change, and every stroke after a drag landed the drag distance from the pen while nine checks passed. Someone drawing found it in seconds.

**Read the origin the way your input path reads it.** A conversion that re-reads it for the check while the pen code uses a cached copy tests something the pen never does.

Before moving on, reproduce the failing report above yourself. Replace the body of `DesktopToCanvas` with the `PointToClient` version, rebuild, run `--replay`, and confirm two things: the two L3 checks fail, and the process exits with code 1. Then put the subtraction back.

That second confirmation matters as much as the first. A check you have never seen fail has not yet demonstrated that it can, and an exit code you have never seen turn non-zero has not demonstrated that it reaches the caller.

## 6. Drawing a stroke

```csharp
float width = (float)pt.Pressure / maxP * (float)_brushSize + 0.5f;

using var paint = new SKPaint
{
    Color = SKColors.Black,
    StrokeWidth = width,
    StrokeCap = SKStrokeCap.Round,
    IsAntialias = true,
    Style = SKPaintStyle.Stroke
};

_skCanvas.DrawLine(from.X, from.Y, canvasPt.X, canvasPt.Y, paint);
```

Four things in there matter:

| setting | what it does |
| --- | --- |
| `DrawLine` taking floats | the position survives the call, as it did through the conversion |
| `IsAntialias` | shades partial pixels along each edge instead of snapping them |
| `SKStrokeCap.Round` | hides the seam where consecutive segments meet |
| `+ 0.5f` | sets a minimum width, so a light touch still marks |

Round caps matter more than they look. A stroke arrives as hundreds of separate short segments rather than one path, and flat caps leave a visible notch at every join where the width changes.

`maxP` comes from `_session.MaxPressure`. Read it rather than assuming 1024: tablets report 1024, 2048 or 8192 levels depending on the pen, and a hard-coded divisor turns a good pen into a light one.

### Brush size counts physical pixels

`_brushSize` holds physical pixels, and the sample's slider label says `px` to make the unit visible. Decide this explicitly now, because the frameworks that lay out in logical units invite the other answer. Set the same nominal size in device-independent units and a 2.25x display draws a stroke 2.25 times wider than this application does, from the same slider position. That difference broke a side-by-side comparison between these samples until someone measured the widths.

### Copy and invalidate

Drawing into the Skia bitmap changes nothing on screen until the copy from section 3 runs and the panel repaints:

```csharp
CopyToGfxBitmap();
_canvasPanel.Invalidate();
```

Do both once per timer tick rather than once per point.

### Verify

Draw. A stroke appears, thickening with pressure, with no stair-steps along its edges at 3x zoom.

Then run the checks once more:

```
Scribble.WinForms.exe --replay
```

All ten should still pass. That run covers the environment, the surface and the coordinate conversion, and it says nothing about the drawing you just added: the checks measure where the stroke goes, not what it looks like. Antialiasing, caps and the pressure curve are for a person to judge, which is section 7.

## 7. Handing it to a person

A passing `--replay` establishes this much:

- The process reports Per-Monitor V2, and the window sits inside the work area
- The surface holds one pixel per screen pixel, starts on a whole pixel, and reaches the screen unscaled
- A recorded stroke pushed through your conversion comes out with the same shape it went in with
- The canvas origin follows the window when the window moves, rather than going stale the moment someone drags it

That is everything the machine can settle. Four things remain.

### What no check covers

- **Wintab.** Synthetic pen injection never reaches the driver, so nothing in `--selftest` or `--replay` has exercised a single Wintab code path. The session, the packet queue, the `Activated` handler from section 4: all untested until someone holds a pen.
- **The drawing.** The checks measure where the stroke goes, not what it looks like.
- **Whether the stroke feels right.** Latency, weight, and how a taper answers a change in pressure.
- **A fault nobody has thought of.** The checks cover faults already found.

### Ask for these four things

Each one exercises something the checks could not reach:

| ask | what it tests |
| --- | --- |
| Draw with each API in turn, on a slow gentle curve | the Wintab paths, and whether the digitizer context looks smoother than the system one |
| Click to another application, come back, draw immediately | the `Activated` handler from section 4. The first stroke is the one that goes missing |
| Drag the window to a display with a different scale, then draw | a DPI change, which only happens when the window moves |
| Press hard, then lift slowly to nothing | the pressure curve and the taper from section 6 |

A slow, gently curving stroke matters for the first one. Faceting worsens as the pen slows, because the samples land closer together and each one-pixel error turns a larger angle. A fast scribble hides it.

### Read the answers carefully

**Treat "it looks wrong" as real even when the report says `10/10`.** Your checks cover three stages and the four things above sit outside all of them. Someone reporting a bad stroke against a clean report has found something the checks do not measure, and the useful response is to find out what.

**"It looks right" establishes less.** A wide brush, a fast stroke, or a display at 1:1 zoom all hide faults that a slow stroke at 3x zoom would show.

[Diagnosing a bad stroke](diagnosing-a-bad-stroke.md) covers the whole of this: the four symptoms, which stage each one comes from, and the measurements that mislead.

### Where to go next

[Build a Scribble app: WPF](hard-mode-wpf.md) changes the coordinate model to logical units. The conversion you wrote in section 5 stops working, the three surface checks that could not fail here start failing, and the API that truncates the pen position advertises two `double`s in its signature.

---

## To write

- [ ] Confirm the `Format32bppPArgb` / `Bgra8888` byte-for-byte claim, or narrow it further than x64
- [ ] Decide whether the `WinFormsPointer` substitution belongs here or in a WinPenKit note
