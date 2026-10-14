# Stage 8: Verifying the pipeline

This page lists, for each stage of the pipeline, what can go wrong, which check detects it, and what still needs a person holding a pen. Most faults in a pen pipeline look alike on screen: a stroke that is faceted, soft, blocky, offset or missing. A check that measures one stage at a time separates them, while looking at the stroke cannot. When checks are skipped, the usual result is a fix applied to the wrong stage while the actual fault remains.

## In short

- Run every Scribble app with `--selftest` (no tablet needed) and fix the first failing check, because each level assumes the levels above it pass.
- Record a hand-drawn stroke from the session under test with `--record`, then run `--replay` on it to test sub-pixel delivery and the app's own canvas conversion.
- Run the mapping wizard's quick check on each new Wintab driver and after display changes.
- No automated check reaches Wintab, pressure, buttons, the eraser or how the stroke looks, so test those by hand with a pen.
- Before trusting a check, put the fault back and confirm the check fails.

For working from a symptom ("the stroke looks wrong") back to a cause, use [Diagnosing a bad stroke](../../build-a-scribble-app/diagnosing-a-bad-stroke.md). This page is organised the other way round, by stage.

## The tools

| tool | what it is | needs a tablet? |
| --- | --- | --- |
| `--selftest` on every Scribble app | levels 0 and 1: environment and drawing surface | no |
| `--replay [path]` on every Scribble app | the above, plus levels 2 and 3: a recorded stroke pushed through the app's own conversion | no |
| `--record <path>` on every Scribble app | writes the live session's stream in the format `--replay` reads | yes |
| [`SelfTest`](https://github.com/TheSevenPens/WinPenKit/blob/main/WinPenKit/Diagnostics/SelfTest.cs) | the shared check runner and report format | no |
| [`StrokeReplay`, `SelfTestReplay`](https://github.com/TheSevenPens/WinPenKit/blob/main/WinPenKit/Diagnostics/StrokeReplay.cs) | loads recordings, `MeanTurnAngle`, `CheckReplay`, `CheckOriginTracksWindow` | no |
| [`StrokeRecorder`](https://github.com/TheSevenPens/WinPenKit/blob/main/WinPenKit/Diagnostics/StrokeRecorder.cs) | the writer behind `--record` | yes |
| [`PresentationProbe`](https://github.com/TheSevenPens/WinPenKit/blob/main/WinPenKit/Diagnostics/PresentationProbe.cs) | `L1.presentation-sampling`: finds two drawn markers on screen | no |
| [`WintabMappingProbe`](https://github.com/TheSevenPens/WinPenKit/blob/main/WinPenKit/Diagnostics/WintabMappingProbe.cs) | Wintab position against the cursor, per mode and monitor | yes |
| [`WinPenKit.MappingWizard`](https://github.com/TheSevenPens/WinPenKit/blob/main/Docs/MAPPING-WIZARD.md) | every pen API against the cursor across scaling, resolution and tablet-mapping setups | yes |
| [`WintabDiagnostics`, `WintabContextTable`](https://github.com/TheSevenPens/WinPenKit/blob/main/WinPenKit/Diagnostics/WintabContextTable.cs) | what the Wintab driver reports about itself | no (needs a driver) |
| [`IPacketCounts`](https://github.com/TheSevenPens/WinPenKit/blob/main/WinPenKit/Diagnostics/IPacketCounts.cs) | packets received, dropped by region, and delivered | yes |
| [`WinPenKit.TestConsole`](https://github.com/TheSevenPens/WinPenKit/blob/main/WinPenKit.TestConsole/Program.cs) | a live readout of any backend, and the clock and Wintab probes | depends on the flag |

`--selftest` and `--replay` print one line per check and exit 0 only when every check passes, so a script can branch on the exit code. `SelfTest.Emit` attaches to the parent's console, because a GUI-subsystem process has none of its own; if nothing can be printed, it writes the report to `%TEMP%\selftest-<AppName>.txt` and sends the path to the debugger output and to `ReportPath`. PowerShell does not wait for a GUI-subsystem binary, so `$LASTEXITCODE` comes back empty unless you wait for the process (for example with `Start-Process -Wait -PassThru`).

The checks run in pipeline order and the first failure is the one to fix: each level assumes the ones above it pass. `Scribble.Win32` and `Scribble.Rust` reimplement the same check identifiers, output format and exit code in C++ and Rust. [SELF-TEST.md](https://github.com/TheSevenPens/WinPenKit/blob/main/Docs/SELF-TEST.md) has a full sample report.

## Stage 1: Source

**What goes wrong.** No Wintab driver, or the wrong driver's `wintab32.dll`. The high-res context fails to open and the session falls back to the system context. Every open fails because the driver is in a bad state.

**What detects it.**

* `WinPenKit.TestConsole` with no flags lists `PenSessionFactory.GetAvailableApis()`, then prints the chosen session's `Capabilities` and `DebugInfo`.
* A Wintab high-res session that fell back reports `Conventions.RawUnits` = `ScreenPixels` instead of `TabletNative`, has no `PenCapabilities.HiRes`, and its `DebugInfo` says the high-res open failed. Check `HiRes` after `Start()` rather than assuming the context you asked for.
* `WintabDiagnostics.DeviceName()`, `DriverScreen()` (the default system context's `lcSys`, `lcOut` and `lcIn` extents) and `ContextTable()` answer without opening a context. A failed open appends the context counts to its error message. `WintabContextTable.AboveStatedMaximum` is true when the driver reports more contexts open than its stated maximum. On a Wacom driver stating 32, opens kept succeeding up to 334, so this is not a capacity check.
* `WintabDiagnostics.LogPath` names the per-process log, `%TEMP%\WinPenKit.<pid>.log`, which records the context before and after each open. The native DLL logs to `WintabSessionCpp.log`.

**Needs a person.** Every Wintab check. Synthetic pen injection does not reach the Wintab driver, so no automated check exercises any Wintab path.

## Stage 2: Delivery

**What goes wrong.** Points never arrive, or arrive and are dropped. Part of the window sits off its monitor or under the taskbar, and input aimed there is discarded while the window keeps running and painting. The first stroke after the app regains focus is lost on Wintab, because the context dropped down the driver's overlap order. A capture region drops points.

**What detects it.**

* `L0.window-placement`: the client area must lie inside one monitor's work area. Windows cascades each launch a little further down and right, so the samples call `WindowPlacement.ClampToWorkArea` at startup. Avalonia restores a saved position in logical units, so a display-scale change can push a window off the monitor; `Scribble.Avalonia` clamps again on `ScalingChanged`.
* `IPacketCounts`, implemented only by the Wintab sessions (test for it with `session is IPacketCounts`): `PacketsFromDriver` counts packets before anything judges them, `PacketsOutsideCaptureRegion` counts those dropped by the region, `PointsDelivered` counts what reached the queue. Silence with a rising `PacketsFromDriver` is the session; silence with a flat one is the device or driver. Treat a missing interface as "this backend cannot say", not as zero.
* The lost first stroke has no automated check. Every sample calls `OnActivated()` from the window's `Activated` event, which calls `WTEnable` and `WTOverlap`.

**Needs a person.** Drawing a stroke immediately after switching back from another application, on Wintab. Hover behaviour near window and monitor edges.

## Stage 3: Timing

**What goes wrong.** Timestamps in the wrong unit, a 32-bit millisecond counter that wraps every 49.7 days, an origin that is not documented (Wintab's `pkTime`), or coalesced points not recovered.

**What detects it.**

* `WinPenKit.TestConsole --selftest-clock` tests the `PenTimestamp` arithmetic (`FromSystemTicks` wrap anchoring, `FromPerformanceCount` overflow) against cases built forward from a known true time. It needs no tablet and no window. It calls `PenTimestamp` directly, so the wiring inside each session, and the C++ copy, are not covered.
* `--probe-wintab-epoch [seconds] [x y]` reads `pkTime` against `GetTickCount64` per packet. On a Wacom DTH246 it found `pkTime` on the `GetTickCount64` epoch: 41703 ms against 41703 ms of wall clock over 6217 packets, with a deliberate pause. The pause separates a free-running clock from one that advances only with packets. `WintabEpochSampler` attaches the same observer to a session inside an app that owns a window, because Wintab delivers packets only to the foreground application.
* `--verify-wintab-anchoring <csv>` replays recorded `pkTime`/tick pairs through the conversion, with no tablet.

**Needs a person.** The epoch probe needs a tablet and someone drawing. Whether recovered intermediate points arrive in the right order on a live device. See [Stage 3](3-timing.md).

## Stage 4: Device units to desktop pixels

**What goes wrong.** The process is not Per-Monitor V2. The session reads an integer field (`ptPixelLocationRaw`, a system context) or rounds on the way. The driver's `lcSys` does not match the physical desktop. See [Stage 4](4-device-to-desktop.md).

**What detects it.**

* `L0.dpi-awareness` reads the thread's DPI awareness context and fails on anything other than Per-Monitor V2. A DPI-unaware process reading a window rect on a 216 DPI monitor sees it scaled by 96/216 and cannot tell.
* `L2.recording-subpixel` on a recording made with `--record` from the session under test. It fails when 5% or more of points sit on whole pixels. A replay of the default recording says nothing about your session; a recording of your session does. Every hand-drawn recording in WinPenKit's `testdata` (Wintab high-res, WM\_POINTER, WPF, WinUI, Avalonia, Qt) has 0.0% of points on whole pixels.
* `WinPenKit.TestConsole` prints `Desktop` with one decimal and `Raw` with its unit label (`tablet`, `px`, `0.01mm`, or `--` for `RawUnits.None`). A desktop value that never shows a non-zero decimal is an integer source.
* `--probe-wintab-mapping [seconds-per-mode] [samples.csv]` runs each Wintab mode, records every packet with the cursor beside it, and reports per mode and monitor the mean error (pass at 3 px per axis, at least 100 samples), and a line fitted from raw value to cursor, which is the mapping the driver actually applied. `--report-wintab-mapping samples.csv` reports on a saved run. The cursor is the reference because, in pen mode, the driver moves it and Windows places it on the physical desktop correctly; in mouse mode the verdict means nothing. Hover, do not tap: a tap activates the window under the nib.
* `WinPenKit.MappingWizard` does the same for Wintab, Wintab high-res and WM\_POINTER across a plan of steps: resolution (native or one mode down), scaling (all 100%, all equal above 100%, and both mixed directions), and tablet mapping (each monitor, all displays). It sets resolution and then scaling itself (resolution first, since it changes scaling), and asks you to change the tablet mapping in the driver. **Quick check** is a Y/N per API on whether the red dot stays on the pointer. **Measure** uses four targets per monitor, held with the tip down for half a second; a step passes at 10 px. **Grid scan** uses a 3x3 grid per monitor, visited forward and back, to find where a driver's behaviour changes. Results go to `Documents\WinPenKit\MappingWizard\<date-time>\` (`summary.md`, `samples.csv`, `session.json`, resumable).

**Needs a person.** All of the probe and wizard runs: someone hovering or pressing the pen on every monitor, and changing the tablet mapping in the driver. Run the wizard's quick check on each new driver, and after any display change you care about.

## Stage 5: Desktop pixels to the canvas

**What goes wrong.** An integer-typed conversion (`PointFromScreen`, `PointToClient`, `PixelPoint`), a cached canvas origin, or an origin on a fractional device pixel. See [Stage 5](5-desktop-to-canvas.md).

**What detects it.** `--replay` pushes a recording through the application's own `DesktopToCanvas`, the function the pen uses, not a copy of it.

* `L3.conversion-snap`: fails when 5% or more of converted points land on a whole device pixel, `abs(x * scale - round(x * scale)) < 1e-6` on both axes. A real pen stream almost never lands on whole pixels, so a figure near 100% means an integer API upstream, without saying where.
* `L3.conversion-lossless`: the mean turn angle of the output must equal that of the input within 0.05°. A translation and a uniform scale preserve angles exactly, so this needs no threshold calibrated to how the stroke was drawn. Feed it the same points converted, never a second stroke.
* `L3.origin-tracks-window`: moves the window 37,23 px, converts the same desktop point again, and expects it to shift by that distance within half a device pixel. It is the only check that sees a wrong origin, because in every other check the replay positions its input relative to the origin the app reports and the app then subtracts the same value. It skips on a maximized window and runs last.
* `L1.surface-alignment`: the canvas origin in device pixels, each axis within 0.01 px of a whole number, reported per axis because the error is often on one axis only. It reports the origin after any snap, so it cannot see a `.5` tie; `L3.origin-tracks-window` can, intermittently.

The turn angle is the mean angle between consecutive segments:

```python
def mean_turn_angle(points):
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

Reference values: a path quantized to a grid turns by `atan(1/5)` = 11.31°, `atan(1/3)` = 18.43° or 45°. A clean high-res stream on a slow curve measures 2 to 4°; the same stroke quantized measures 17 to 22°. The default recording, `testdata/reference-stroke.csv` (synthetic, ~1.6 px sampling, no high-frequency noise), measures 0.74° clean and 18.71° quantized; real hardware measured 17.51° before the WPF fix. Lossless results:

```
Wintab high-res   in 2.69°   out 2.69°   passes
WPF Stylus        in 5.32°   out 5.32°   passes
PointFromScreen   in 0.74°   out 18.71°  fails
```

Do not use an image-based roughness metric for this: stroke steepness dominates it, and it has given both false passes and false failures.

**Needs a person.** Dragging the window mid-session and drawing again; moving the window to a monitor at another scale.

## The drawing surface

The surface is rendering, not part of this pipeline, but its faults look like position faults, so `--selftest` checks it before any coordinate check.

* `L1.surface-physical`: bitmap equals `ceil(logical size x scale)`. A logical-sized surface at 2.25x renders at 44% of the display's resolution. Pass the ratio of layout unit to device pixel: 1.0 for Win32 and WinForms even on a 2.25x display.
* `L1.presentation-1to1`: the host's layout size equals the bitmap's pixel size, within half a pixel.
* `L1.presentation-sampling` (`PresentationProbe`): draws two markers a known distance apart, finds them in a screen capture, and compares the distances. It caught a 2700 px bitmap in a 2700 px host with only its top-left 1200x600 drawn across it, which `L1.presentation-1to1` passed. The window must be visible and unobscured; the app draws, presents, then awaits `MeasureAsync`.

See [Rendering options for paint apps](../../rendering-for-pen-apps.md) and [framework deltas](../../build-a-scribble-app/framework-deltas.md).

## Stage 6: Values

**What goes wrong.** The wrong pressure maximum, a nonlinear or clipped pressure curve, Wintab button events read as a bitmask, an eraser not recognised because Wintab cursor numbers are device-assigned.

**What detects it.** No automated check. `WinPenKit.TestConsole` prints raw pressure with its percentage of `MaxPressure`, Z, `Cursor` and `Buttons` in hex on each update. `StrokeRecorder` writes the session's `MaxPressure` into the recording header when the session starts, not at save, because an app can switch API mid-recording. For a lumpy stroke, replay the same path with pressure held constant: if the width still varies, the fault is in the pressure path.

**Needs a person.** All of it: pressing through the full range, each barrel button, the eraser end, tilt and rotation. Check `Capabilities` against what the device does. Every session sets the `Twist` flag, and a pen without a rotation sensor reports 0 on every backend, so rotate a pen that has one and check that the value changes. See [Stage 6](6-values.md).

## Stage 7: Output and switching APIs

**What goes wrong.** An app that works on one backend breaks on another because it read `RawX` without checking `Conventions.RawUnits`, or assumed one button encoding.

**What detects it.** Record one stroke per API with `--record`, drawn by the same hand at the same speed, then `--replay` each: `L2.recording-subpixel` says whether that session delivered sub-pixel data, and the `in` figure of `L3.conversion-lossless` is that session's mean turn angle, comparable only between strokes drawn the same way. `Scribble.Qt` reaches the pen through Qt rather than WinPenKit, so its recordings are the only comparison in which the two sides share no code.

**Needs a person.** Drawing the comparison strokes. See [Stage 7](7-output.md).

## What a passing run does not cover

* **The session.** A recording holds what a session produced, so replaying it tests everything downstream and nothing inside. WPF's stylus stack once handed sub-pixel points to `PointToScreen`, which truncated them before any application code ran.
* **Wintab.** No synthetic input reaches it.
* **The brush engine and how the stroke looks.** Taper, caps, joins, antialiasing and pressure response all pass unexamined. Every fault found in the Scribble investigation was first reported by a person who said a stroke looked wrong; `Scribble.Avalonia` and `Scribble.WinUI` were both signed off by eye while rendering at 44% resolution.

Before trusting any check, confirm it can fail: put the fault back and see the number move. That exercise found two Scribble checks that could not fail at all. [Diagnosing a bad stroke, section 6](../../build-a-scribble-app/diagnosing-a-bad-stroke.md) lists measurements that looked like evidence and could not detect the fault.

## Further reading

* [Diagnosing a bad stroke](../../build-a-scribble-app/diagnosing-a-bad-stroke.md) and [Generating the symptom images](../../build-a-scribble-app/generating-symptom-images.md).
* [The pipeline at a glance](README.md), and stages [1](1-source.md), [2](2-delivery.md), [3](3-timing.md), [4](4-device-to-desktop.md), [5](5-desktop-to-canvas.md), [6](6-values.md), [7](7-output.md).
* WinPenKit: [SELF-TEST.md](https://github.com/TheSevenPens/WinPenKit/blob/main/Docs/SELF-TEST.md), [MAPPING-WIZARD.md](https://github.com/TheSevenPens/WinPenKit/blob/main/Docs/MAPPING-WIZARD.md).
