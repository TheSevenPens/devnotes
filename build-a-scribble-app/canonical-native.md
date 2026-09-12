# Build a Scribble app: Native / C++

> **Status: complete first draft.** Tracked in [#8](https://github.com/TheSevenPens/devnotes/issues/8).

## Overview

By the end you have a Win32 application that opens a window, takes pen input through WinPenKit, and draws strokes that follow the pen below the width of a screen pixel. It also reports its own state as text, so you can tell a correct canvas from a broken one without looking at the screen.

You will build, in this order:

- A build environment, verified before any code
- Per-Monitor V2 awareness, before the first window exists
- Diagnostics that print what the application thinks its surface measures
- A window and a drawing surface
- A pen session
- The conversion from desktop coordinates to canvas coordinates
- The stroke itself

Here are some notes:

- This path puts nothing between your code and the pen API, so you write every coordinate transformation yourself
- That matters most for one thing: Win32 hands you a `POINT` holding two integers, and the central mistake in pen input comes from letting a type like that stand in for a pen position. Win32 shows you that struct directly, where other frameworks hide it behind a method
- The [WinForms path](canonical-winforms.md) reaches a working application in less time, and hides that struct behind a method. Take it if you would rather not set up a C++ toolchain
- The reference implementation lives in `Scribble.Win32` in WinPenKit
- Section 6 holds the main lesson of this guide. The sections before it build the application that section needs

---

## 1. Before any code: the build environment

A toolchain fault here produces errors from inside the Windows SDK headers, naming files you have never opened. Finish this section before writing any code of your own, and any later failure comes from your code rather than from the setup.

### What to install

- **Visual Studio**, with the *Desktop development with C++* workload
- **A Windows 10 SDK**, which that workload installs. The project asks for `10.0`, meaning the latest installed
- **An MSVC toolset.** The samples build with **v145**; GitHub's runners carry **v143**, so CI passes `-p:PlatformToolset=v143` to override. Either works. Match whichever you have rather than chasing the version in the project file

C++20, set through `<LanguageStandard>stdcpp20</LanguageStandard>`.

### Two traps in the project file

**`objidl.h` before `gdiplus.h`.** The order decides whether the file compiles. `GdiplusImaging.h` declares COM interfaces, and `WIN32_LEAN_AND_MEAN` strips the declarations it depends on out of `windows.h`:

```cpp
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#include <windows.h>
#include <windowsx.h>
#include <commctrl.h>

#include <objidl.h>      // must precede gdiplus.h
#include <gdiplus.h>
```

Without that line the compiler reports undeclared types inside the SDK headers, several files away from anything you wrote.

**`gdiplus.lib` in the linker inputs.** GDI+ arrives through a library the C++ workload installs and does not link for you:

```xml
<AdditionalDependencies>WinPenKit.Native.lib;gdiplus.lib;%(AdditionalDependencies)</AdditionalDependencies>
```

Section 7 explains why this application uses GDI+ rather than GDI. The short version: GDI draws lines between integer endpoints, which throws away the sub-pixel position that everything up to that point worked to keep.

### Building

The native solution builds with Visual Studio's MSBuild, not the dotnet CLI:

```
msbuild WinPenKitNative.sln -p:Configuration=Release -p:Platform=x64
```

It produces `WinPenKit.Native.dll`, its import library, and `ScribbleCpp.exe`.

### Verify before proceeding

Build and run the sample. A window opens. Nothing draws yet, and nothing should.

If the build fails, fix it here. Every later section adds something that can fail on its own, and a toolchain fault looks exactly like a fault in the code you just wrote.

## 2. Per-Monitor V2, before the first window

One call sets this up, and it has to run before you create any window:

```cpp
int WINAPI wWinMain(HINSTANCE hInst, HINSTANCE, LPWSTR, int nShow) {
    SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2);
    ...
```

Put it ahead of the window class registration, ahead of `CreateWindowExW`, and ahead of anything else that might create a window. `SetProcessDpiAwarenessContext` returns an error once the process already holds an awareness level, and creating a window gives it one.

### What the lower awareness levels report

Windows reports **scaled coordinates** to a process that claims less awareness. Window rectangles, cursor positions and monitor sizes all come back scaled, and any value you hand back gets converted the other way.

Mouse input hides the problem. Windows scales mouse coordinates by the same factor it scales your window rectangle, so the two agree with each other even though neither one describes the physical screen.

Wintab does not travel through Windows. It reads the tablet and reports true physical desktop pixels from the driver, so pen positions and your window rectangle describe different coordinate spaces. Neither number carries a unit, so both look equally real, and the stroke lands somewhere the pen never went.

| awareness | what Win32 reports | result with a pen |
| --- | --- | --- |
| Unaware | coordinates as if every display ran at 96 DPI | positions disagree with Wintab everywhere |
| System | the primary display's DPI, applied to all of them | correct on the primary display, wrong on the others |
| Per-Monitor V2 | true physical pixels | agrees with Wintab on every display |

### A worked example

Nothing reports an error when you get this wrong. The call succeeds, the numbers arrive, and the numbers are wrong.

A script written to drive these samples called `SetProcessDPIAware`, which asks for System awareness rather than Per-Monitor V2. It then measured a window on a 168 DPI display while the primary display ran at 216 DPI.

Windows scaled every rectangle it returned by 216 / 168, so the captured image covered 1 / 1.2857 = **78%** of the window. The bottom and right of the application appeared to be unpainted.

That looks like a rendering fault in the application, and the investigation went there first. A window that measures 2000 pixels wide while occupying 2571 reads exactly like a window that measures 2000 pixels wide, so the measurement gives you no reason to doubt it.

**Any tool that measures your window needs the same awareness your application has.** A screenshot utility, a test harness, an automation script: each one that claims less awareness reports a different window than the one on screen.

### Manifest or API call

Both work. The samples use the API call, which suits a single executable that controls its own startup.

A manifest entry applies before any of your code runs, which covers the case where something in your startup path creates a window before `wWinMain` reaches its first line. Prefer it when a framework or a library owns startup. See [Per-Monitor V2 DPI Awareness](../pen-input-on-windows/implementation-notes/per-monitor-v2-dpi-awareness.md) for the per-framework detail.

### Track the DPI after startup

Per-Monitor V2 means the DPI changes while the application runs, whenever the user drags the window to another display. Read it once the window exists and again on every change:

```cpp
g_dpi = static_cast<int>(GetDpiForWindow(hwnd));   // WM_CREATE
...
case WM_DPICHANGED:
    g_dpi = HIWORD(wp);
```

Everything measured in points rather than pixels scales through that value. `MulDiv(value, g_dpi, 96)` converts one.

### Verify before proceeding

Nothing draws yet, and the check that reports this value arrives in section 3. Build that, then come back: `--selftest` prints the awareness level and the display scale, which is how you confirm this section.

## 3. Diagnostics first

Build the reporting apparatus before the thing it reports on.

A stroke that looks wrong tells you something failed. A printed surface size tells you *which stage* failed. Writing the checks first takes about an hour, and it replaces a much longer stretch of guessing later.

A second reason decides the ordering. A build server, or an AI agent following a guide like this one, reads text and cannot look at a screen. Anything those two can check has to arrive as text.

### What can run at this point

The checks divide into levels, and each level needs more of the application to exist than the one before it:

| level | covers | available |
| --- | --- | --- |
| **L0** | DPI awareness, window placement, display scale | now |
| **L1** | surface size, pixel alignment, 1:1 presentation | after section 4 builds a surface |
| **L2, L3** | the pen stream and the coordinate conversion | after section 6 converts anything |

So this section builds the machinery and runs L0 against it. The rest fills in as the application grows, which is why sections 4 and 6 each end by running the checks again.

`selftest.h` in `Scribble.Win32` holds the implementation. Copy it, or write your own against the same output format: one line per check, and an exit code.

### Getting the output somewhere you can read it

A Win32 GUI application has no console. `printf` goes nowhere.

Three cases, and the order matters:

```cpp
int emit() const {
    std::string text = format();

    if (!write_to(GetStdHandle(STD_OUTPUT_HANDLE), text)) {
        if (AttachConsole(ATTACH_PARENT_PROCESS))
            write_to(GetStdHandle(STD_OUTPUT_HANDLE), text);
        else
            OutputDebugStringA(text.c_str());
    }
    return all_passed() ? 0 : 1;
}
```

**The inherited handle comes first.** When someone pipes your output to a file, or a script captures it, `GetStdHandle` already returns a usable handle and `AttachConsole` does nothing for you. An earlier version of this code called `AttachConsole` first: run from a terminal it printed the report, and run through a pipe it printed nothing at all. The first way anyone automates this is through a pipe.

`OutputDebugStringA` covers the last case, a double-click with no console anywhere.

### The exit code

Return 0 only when every check passes:

```cpp
return all_passed() ? 0 : 1;
```

A caller can then branch on the result without reading the text. Two warnings about that, both of which cost time in this project:

- **Return the value from `wWinMain`.** A `main` that ends in `return 0` regardless throws the result away, and every run reports success.
- **A GUI binary does not block the caller.** PowerShell's call operator returns immediately and leaves `$LASTEXITCODE` empty, so a script that checks it passes no matter what the report said. Use `Start-Process -Wait -PassThru` and read `ExitCode`.

Both produce a check that cannot fail, which is worth less than no check: it reports success and someone believes it.

### Verify before proceeding

```
ScribbleCpp.exe --selftest
```

Level 0 should report `PerMonitorV2`, a window inside the work area, and the display scale. That confirms section 2 as well, which you had no way to check when you wrote it.

Nothing above L0 runs yet, and the report should say so rather than omitting the lines.

## 4. A window and a drawing surface

### Use a regular top-level window

```cpp
HWND hwnd = CreateWindowExW(
    0, wc.lpszClassName, L"Scribble C++",
    WS_OVERLAPPEDWINDOW | WS_CLIPCHILDREN,
    CW_USEDEFAULT, CW_USEDEFAULT, 1400, 800,
    nullptr, nullptr, hInst, nullptr);
```

**Do not pass `HWND_MESSAGE` as the parent.** A message-only window costs nothing and handles messages, which makes it an attractive place to receive pen packets. The Wacom driver does not deliver `WT_PACKET` to a message-only window.

Nothing reports an error when that happens. `WTOpenA` returns a valid context handle, the session describes itself as running, and the packet count stays at zero. You get silence rather than a diagnosis, and the code reads as correct while you look for the problem elsewhere.

[Wintab Gotchas](../pen-input-on-windows/implementation-notes/wintab-gotchas.md) covers this and several others worth reading before section 5.

### Size the bitmap from the client rect

```cpp
static void create_bitmap(HWND hwnd) {
    HDC hdc = GetDC(hwnd);
    g_bitmap    = CreateCompatibleBitmap(hdc, g_width, g_height);
    g_bitmap_dc = CreateCompatibleDC(hdc);
    SelectObject(g_bitmap_dc, g_bitmap);
    ReleaseDC(hwnd, hdc);
    ...
}
```

`g_width` and `g_height` come from `WM_SIZE`, minus whatever the ribbon occupies:

```cpp
case WM_SIZE: {
    int new_w = LOWORD(lp);
    int new_h = HIWORD(lp) - ribbon_height();
    ...
}
```

Those numbers arrive in physical pixels, because a Per-Monitor V2 Win32 application lays out in physical pixels. The bitmap therefore holds exactly one pixel per screen pixel, and it does so without you converting anything.

### Win32 cannot get the surface wrong

Section 3 listed three L1 checks: surface size, pixel alignment, and 1:1 presentation. All three pass here, and all three pass for structural reasons rather than because you did something right.

| check | why it passes in Win32 |
| --- | --- |
| surface size | `WM_SIZE` reports physical pixels, so there is no second unit to confuse it with |
| pixel alignment | a window offset is an integer; Win32 has no layout system that can place the canvas between pixels |
| 1:1 presentation | `BitBlt` copies pixels without scaling |

Every one of those fails in a framework that lays out in logical units. `Scribble.Wpf`, `Scribble.Avalonia`, `Scribble.WinUI` and `Scribble.Rust` each shipped with at least one of them broken, and two of those went unnoticed after a person had inspected the strokes and approved them.

So this guide teaches the coordinate pipeline thoroughly, and teaches almost nothing about the drawing surface: how it comes to hold the wrong number of pixels, land between pixels, or get scaled on its way to the screen.

[Build a Scribble app: WPF](hard-mode-wpf.md), the next guide in this set, covers those three. WPF permits all three mistakes, and all three appeared while `Scribble.Wpf` was being written: a surface sized in logical units, that surface landing 0.64 pixels off the pixel grid, and a coordinate conversion that truncated every pen position. Each one got found and fixed, and the sample ships correct today. The framework draws correctly once you handle them; it offers more ways to get this wrong than Win32 does, which is why that guide takes them one at a time.

### One thing this section does introduce

The canvas does not start at the client origin. It starts below the ribbon:

```cpp
BitBlt(mem_dc, 0, rbh, g_width, g_height, g_bitmap_dc, 0, 0, SRCCOPY);
```

That `rbh` offset comes back in section 6. A pen position arrives in desktop coordinates and has to travel through two subtractions rather than one: desktop to client, then client to canvas.

### Verify

```
ScribbleCpp.exe --selftest
```

All six L0 and L1 checks should pass. Resize the window and run it again: the surface tracks the client area, and a window dragged partly off the display fails `L0.window-placement` rather than silently accepting pen input that never arrives.

## 5. Opening a pen session

`pen_session.h` is a flat C API. Five calls cover the whole lifecycle:

```c
PenSessionHandle pen_session_create(PenInputApi api);
const char*      pen_session_start(PenSessionHandle handle, void* app_hwnd);
int              pen_session_drain_points(PenSessionHandle handle,
                                          PenPoint* buffer, int max_count);
void             pen_session_stop(PenSessionHandle handle);
void             pen_session_destroy(PenSessionHandle handle);
```

`pen_session_start` returns `nullptr` on success and an error string otherwise. Print that string somewhere you can read it; a session that failed to start looks identical to a session receiving nothing.

Drain on a timer rather than per message. Each call empties the queue into your buffer and returns the count:

```c
PenPoint points[128];
int n = pen_session_drain_points(g_session, points, 128);
```

### Choosing an API

`pen_session_get_available_apis` reports what the machine offers. Three matter for a native application:

| API | reports positions in | use it |
| --- | --- | --- |
| `PEN_API_WINTAB_DIGITIZER` | tablet-native units, converted to sub-pixel desktop pixels | by default, when a tablet is present |
| `PEN_API_WINTAB_SYSTEM` | whole screen pixels | to compare against, and to see what quantization looks like |
| `PEN_API_WM_POINTER` | HIMETRIC, converted to sub-pixel desktop pixels | when Windows Ink suits you better than Wintab |

**Wintab system mode is quantized before your code runs.** The driver rounds to whole screen pixels and hands you the result, so no application-side fix exists. Offer it in your API selector anyway. Drawing the same stroke under both contexts takes ten seconds, and a stroke that comes out faceted under system mode and smooth under the digitizer context places the fault in the driver rather than in your code.

`pen_session_get_capabilities` returns a bitmask. `PEN_CAP_HIRES` says whether the device actually supplies sub-pixel positions, rather than whether the API can carry them.

### Tell the session when your window is activated

```c
case WM_ACTIVATE:
    if (g_session) pen_session_on_activated(g_session);
    break;
```

Wintab delivers packets to whichever context sits on top of the driver's overlap order. Losing focus drops yours down that order, and regaining focus does not put it back. Without this call the first stroke after returning to your application disappears, and every stroke after it draws normally.

The pointer-based APIs need nothing here; Windows routes their input by window. The call costs nothing when it does not apply.

### Count the points

Add a counter to your ribbon before you draw anything with the data:

```
Pts 4213   Off 0   Seg 4212
```

Three numbers, and each combination means something different:

| reading | meaning |
| --- | --- |
| `Pts 0` | nothing arrives. Look at the session, the API, and section 4's window style |
| `Pts > 0`, `Off > 0`, `Seg 0` | points arrive and convert to positions outside the canvas. Section 6 |
| `Pts > 0`, `Seg > 0`, nothing visible | points arrive, convert, and draw. Look at the surface or the brush |

Without those counters all three look the same from the outside: a blank canvas. Reading code to work out which of the three you have takes far longer than printing three integers.

### Verify

Draw with a pen. `Pts` climbs, `Off` stays at zero while the pen sits over the canvas, and the telemetry shows real pressure rather than `--`.

Nothing draws yet. Section 6 converts those positions, and section 7 puts ink on the surface.

[Wintab Gotchas](../pen-input-on-windows/implementation-notes/wintab-gotchas.md) covers the rest of the driver's behaviour: packet queue sizing, the inverted Y axis, and why `HCTX` has to be pointer-sized.

## 6. Desktop pixels to canvas pixels

A `PenPoint` carries its position as two `double`s, and it does so because a digitizer resolves finer than a screen pixel. Preserving that through the conversion to canvas coordinates is the single thing this guide exists to teach.

### ScreenToClient cannot carry a pen position

Win32 offers `ScreenToClient`, which converts a desktop position into a window-relative one. That is exactly the conversion this section needs, and it is the wrong function for the job. It takes this:

```c
typedef struct tagPOINT {
  LONG x;
  LONG y;
} POINT;
```

Two 32-bit integers. To pass a pen position through that function you have to put it into a `POINT` first, which means rounding it:

```cpp
POINT p = { (LONG)pt.desktop_x, (LONG)pt.desktop_y };   // the precision ends here
ScreenToClient(hwnd, &p);
```

The cast discards everything after the decimal point. The function then returns a perfectly correct answer to a question you asked in the wrong units, and no error appears anywhere.

### Get the origin from Windows, subtract it yourself

The conversion you need is a subtraction:

```
canvas position = desktop position - where the canvas sits on the desktop
```

Only Windows can tell you the second term, and `ClientToScreen` is how you ask. Do the subtraction yourself:

```cpp
POINT client_origin = { 0, 0 };
ClientToScreen(hwnd, &client_origin);

CanvasPt client_pt{
    pt.desktop_x - client_origin.x,
    pt.desktop_y - client_origin.y - rbh };
```

Two subtractions, as section 4 warned: the client origin, then the ribbon height.

`CanvasPt` holds two `double`s. Give it integer members and you have rebuilt the problem one line further down:

```cpp
struct CanvasPt { double x, y; };
```

### The origin is already a whole number

The code above still calls `ClientToScreen`, which uses the same `POINT` struct. That is safe here for one reason: **Windows places every window at whole-pixel screen coordinates, so a client origin never has a fractional part.** Rounding a number that is already whole changes nothing about it.

The pen position is the opposite case. A digitizer reports values like `2302.33`, and rounding that to `2302` throws away the one thing that separates a pen from a mouse.

Follow this in any framework:

> **Let the framework convert the origin. Subtract it from the pen position yourself.** The origin is a whole number, so an integer API returns it unchanged. The pen position keeps its fractional part because no API touches it.

### What it costs to get this wrong

Measured on a 1440p display at 1.75x, drawing through a Wintab digitizer context. Mean angle between consecutive segments, on the path the application actually drew:

| | mean turn angle | points landing on a whole pixel |
| --- | --- | --- |
| as the session delivered it | 4.11 deg | 0 of 3014 |
| after a conversion through an integer point | **17.51 deg** | **3014 of 3014** |

Every point snapped. On screen that reads as a stroke made of short straight segments meeting at visible angles, worst on slow curves. It looks like a brush engine problem, and no change to the brush engine removes it.

### Every framework has this problem

Win32 puts the integers in front of you. You write the `POINT` yourself, so the limitation shows up in your own code before it can cost you anything. Every other framework wraps the same conversion in a method call, and each one makes the integers harder or easier to see:

| framework | the API | how visible |
| --- | --- | --- |
| Win32 | `ScreenToClient(POINT*)` | the struct is in the signature |
| WinForms | `Control.PointToClient(Point)` | `System.Drawing.Point` has `int` members, and no `PointF` overload exists |
| Avalonia | `TopLevel.PointToScreen` | returns `PixelPoint`, whose members are `int` |
| WPF | `Visual.PointFromScreen(Point)` | **invisible**: takes and returns two `double`s, and truncates internally through a Win32 `POINT` |

**That is why this guide set starts with C++.** WPF gives no sign of the problem at all: a `Point` goes in, a `Point` comes out, and both hold `double`s. Someone who first wrote that `POINT` struct by hand knows to check the parameter type even when the signature shows only `double`. [Framework Coordinate Conversion](../pen-input-on-windows/implementation-notes/framework-coordinate-conversion.md) covers all four in detail.

### Verify

```
ScribbleCpp.exe --replay
```

Three checks matter here:

```
[PASS] L2.recording-subpixel   0.0% of 480 recorded points are on whole pixels
[PASS] L3.conversion-snap      0.0% of converted points land on whole device pixels
[PASS] L3.conversion-lossless  mean turn angle in 0.74 deg, out 0.74 deg (delta 0.00)
```

The last one is the strongest statement available about a coordinate conversion. A translation preserves angles exactly, so a correct implementation reproduces the input's turn angle to two decimal places. It needs no threshold and no reference value: it compares the output against its own input.

### A tenth check, for the term the others cannot see

A conversion is an origin and a scale, and every check above holds the window still. That leaves the origin uncovered: the replay places its input relative to the origin your application reports, then your application subtracts the same value back off, so an origin wrong by any amount cancels itself exactly. `L1.surface-alignment` does not close the gap either, because it asks whether the origin is a whole number rather than whether it is the right one.

```
[PASS] L3.origin-tracks-window  moved 37,23px; conversion followed
```

That check moves the window a known distance and converts the same desktop point again. A conversion that reads the origin fresh reports a position shifted by exactly that distance. One that cached the origin reports what it did before, because nothing told it the window moved.

`Scribble.Wpf` shipped with that fault: it cached the origin when it built its bitmap, dragging the window raised no size change, and every stroke after a drag landed the drag distance from the pen while nine checks passed. Someone drawing found it in seconds.

**Read the origin the way your input path reads it.** A conversion that re-reads it for the check while the pen code uses a cached copy tests something the pen never does.

Before moving on, put the fault back deliberately. Cast the pen position to a `POINT`, run `--replay` again, and watch `conversion-snap` report close to 100%. A check you have never seen fail has not yet demonstrated that it can.

## 7. Drawing a stroke

### MoveToEx and LineTo take integers

GDI's line drawing has the same limit as `ScreenToClient`, one stage further along:

```cpp
BOOL MoveToEx(HDC hdc, int x, int y, LPPOINT lppt);
BOOL LineTo  (HDC hdc, int x, int y);
```

Four `int` parameters. Section 6 carried the pen position through the conversion with its fractional part intact, and these functions round it at the last possible moment. The stroke comes out faceted, and every measurement you built along the way still passes, because the loss happens after the conversion the checks examine.

GDI also draws without antialiasing. Even given whole-number endpoints, a GDI line has hard pixel edges, so a stroke made of hundreds of short segments shows a stair-step on every one.

### Draw with GDI+

```cpp
static void draw_stroke(CanvasPt from, CanvasPt to, float width) {
    Gdiplus::Graphics g(g_bitmap_dc);
    g.SetSmoothingMode(Gdiplus::SmoothingModeAntiAlias);
    g.SetPixelOffsetMode(Gdiplus::PixelOffsetModeHalf);

    Gdiplus::Pen pen(Gdiplus::Color(255, 0, 0, 0), width);
    pen.SetStartCap(Gdiplus::LineCapRound);
    pen.SetEndCap(Gdiplus::LineCapRound);
    pen.SetLineJoin(Gdiplus::LineJoinRound);

    g.DrawLine(&pen,
        Gdiplus::PointF((Gdiplus::REAL)from.x, (Gdiplus::REAL)from.y),
        Gdiplus::PointF((Gdiplus::REAL)to.x,   (Gdiplus::REAL)to.y));
}
```

Four settings matter:

| setting | what it does |
| --- | --- |
| `PointF` | takes the endpoints as floats, so the position survives the call |
| `SmoothingModeAntiAlias` | shades partial pixels along each edge instead of snapping them |
| `PixelOffsetModeHalf` | samples at pixel centres, which keeps a line centred where you asked for it |
| round caps and joins | hides the seam where consecutive segments meet |

Round caps and joins matter more than they look. A stroke arrives as hundreds of separate short segments rather than one path, and butt caps leave a visible notch at every join where the width changes.

`Graphics` needs GDI+ started before the first window and shut down after the message loop:

```cpp
Gdiplus::GdiplusStartupInput gdiplus_input;
Gdiplus::GdiplusStartup(&g_gdiplus_token, &gdiplus_input, nullptr);
...
if (g_gdiplus_token) Gdiplus::GdiplusShutdown(g_gdiplus_token);
```

### Pressure sets the width

```cpp
float norm  = static_cast<float>(pt.pressure) / g_max_pressure;
float width = norm * g_brush_size + 0.5f;
```

`g_max_pressure` comes from `pen_session_get_max_pressure`. Read it rather than assuming 1024: tablets report 1024, 2048 or 8192 levels depending on the pen, and a hard-coded divisor turns a good pen into a light one.

The `+ 0.5` sets a minimum width so a light touch still marks. **`g_brush_size` counts physical pixels**, which is worth deciding explicitly now. The frameworks that lay out in logical units invite you to make it a logical size, and then the same slider draws a stroke 2.25x wider on a scaled display than this sample does.

### Verify

Draw. A stroke appears, thickening with pressure, with no stair-steps along its edges at 3x zoom.

Then run the checks once more:

```
ScribbleCpp.exe --replay
```

All ten should still pass. That run covers the environment, the surface and the coordinate conversion, and it says nothing at all about the drawing you just added: the checks measure where the stroke goes, not what it looks like when drawn. Antialiasing, caps, joins and the pressure curve are for a person to judge, which is section 8.

## 8. Handing it to a person

A passing `--replay` establishes this much:

- The process reports Per-Monitor V2, and the window sits inside the work area
- The surface holds one pixel per screen pixel, starts on a whole pixel, and reaches the screen unscaled
- A recorded stroke pushed through your conversion comes out with the same shape it went in with
- The canvas origin follows the window when the window moves, rather than going stale the moment someone drags it

That is everything the machine can settle. Four things remain.

### What no check covers

- **Wintab.** Synthetic pen injection never reaches the driver, so nothing in `--selftest` or `--replay` has exercised a single Wintab code path. The session, the packet queue, the activation handling from section 5: all untested until someone holds a pen.
- **The drawing.** Section 7 said this: the checks measure where the stroke goes, not what it looks like. Antialiasing, caps, joins and the pressure curve pass unexamined.
- **Whether the stroke feels right.** Latency, weight, and how a taper answers a change in pressure. No number on this page addresses any of it.
- **A fault nobody has thought of.** The checks cover faults already found.

### Ask for these four things

Each one exercises something the checks could not reach:

| ask | what it tests |
| --- | --- |
| Draw with each API in turn, on a slow gentle curve | the Wintab paths, and whether the digitizer context looks smoother than the system one |
| Click to another application, come back, draw immediately | the `WM_ACTIVATE` handling from section 5. The first stroke is the one that goes missing |
| Drag the window to a display with a different scale, then draw | the DPI change from section 2, which only fires when the window moves |
| Press hard, then lift slowly to nothing | the pressure curve and the taper from section 7 |

A slow, gently curving stroke matters for the first one. Faceting worsens as the pen slows, because the samples land closer together and each one-pixel error turns a larger angle. A fast scribble hides it.

### Read the answers carefully

**Treat "it looks wrong" as real even when the report says `10/10`.** Your checks cover three stages and the four things above sit outside all of them. Someone reporting a bad stroke against a clean report has found something the checks do not measure, and the useful response is to find out what.

**"It looks right" establishes less.** A wide brush, a fast stroke, or a display at 1:1 zoom all hide faults that a slow stroke at 3x zoom would show.

[Diagnosing a bad stroke](diagnosing-a-bad-stroke.md) covers the whole of this: the four symptoms, which stage each one comes from, and the measurements that cannot detect the fault.

### Where to go next

- [Build a Scribble app: WinForms](canonical-winforms.md) builds the same application with a managed library surface and the same coordinate model, which is one new variable rather than three.
- [Build a Scribble app: WPF](hard-mode-wpf.md) changes the coordinate model to logical units, and with it the three surface faults this path could not produce.

---

## To write

- [ ] Verify the component list from a clean machine. Written from what builds here and what CI installs, neither of which is a fresh install
- [ ] Decide how much `pen_session.h` to reproduce inline vs link
- [ ] Confirm every "Verify" step is reachable in order (no check that needs a later section)
