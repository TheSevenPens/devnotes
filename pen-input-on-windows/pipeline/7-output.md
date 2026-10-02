# Stage 7: The output contract: PenPoint and switching APIs

This stage defines what the application receives at the end of the pipeline: one record type for every pen sample, plus session properties that say what the values mean. It also covers changing the input API while the app runs. When it is done badly, the app's drawing code needs a branch per API, buttons or eraser read correctly on one API and never on another, a raw value is read in the wrong unit, or changing the pen API requires restarting the app.

## In short

- Draw from `PenPoint.DesktopX` and `DesktopY`, which are physical desktop pixels as `double` on every backend; treat `RawX` and `RawY` as diagnostics in the unit named by `Conventions.RawUnits`.
- Normalize pressure as `Pressure / session.MaxPressure`, because the maximum is 1024 on pointer backends and the device's own range on Wintab.
- Decode buttons and the eraser with `PenButtonTracker` and `IsEraser`, not with the `[Obsolete]` `PenPoint` button properties.
- Read `Capabilities` and `Conventions` after `Start` returns, because a high-res Wintab session can fall back to screen pixels during `Start`.
- To switch API at runtime, call `Stop()` and `Dispose()` on the old session before you create and start the new one.

## The problem

Each API returns a different shape of data: Wintab a `PACKET` struct fetched with `WTPacket`, WM\_POINTER a `POINTER_PEN_INFO`, WinUI and Avalonia a `PointerPoint` per event, WPF a `StylusPointCollection` per event. Units differ too: pressure ranges, tilt representation, position space, button encoding, clock. A unifying layer has to pick one record, convert what can be converted without loss, and say plainly which fields still depend on the backend.

Switching APIs adds a second problem. Most applications bind their input path once:

- Driver handles and API bindings are created at process start.
- Framework input stacks (WPF's Wisp, WinUI's composition layer) initialise once.
- Cached state such as context handles, function pointers and message routing can become invalid when the path changes.

So a restart is the common answer, and the safe one, even in apps that claim not to need it.

### Related projects

- **Qt `QTabletEvent`.** Qt delivers tablet input from Windows (Wintab or WM\_POINTER), Linux (XInput) and Apple platforms as one event class. It normalises values (pressure 0.0 to 1.0, tilt in degrees), is event-driven rather than polled, and does not tell the caller which API produced the event. On Windows the two backends are mutually exclusive, WM\_POINTER is the default, and Qt chooses between them while the Windows platform plugin initialises, before `QApplication` is running (`-platform windows:nowmpointer` selects Wintab). It cannot switch after that. Krita implements neither API itself: it saves the user's choice, and on the next start configures Qt from it, so changing the setting requires restarting Krita. Afterwards Krita knows only what it asked for. Qt's Wintab context is always the high-res one. Qt does not report the device's pressure range. See [QTabletEvent docs](https://doc.qt.io/qt-6/qtabletevent.html), the [Qt tablet example](https://doc.qt.io/qt-6/qtwidgets-widgets-tablet-example.html), [Krita tablet settings](https://docs.krita.org/en/reference_manual/preferences/tablet_settings.html) and [How Krita and Qt handle pen input](../../misc/krita-and-qt/README.md).
- **octotablet (Rust).** A crate that gives Rust applications one interface over platform tablet APIs, with pressure, tilt and multiple tools, without going through a UI framework. See [crates.io](https://crates.io/crates/octotablet), [GitHub](https://github.com/Fuzzyzilla/octotablet) and [docs](https://docs.rs/octotablet/0.1.0/octotablet/).

## How WinPenKit handles it

### The session is polled

All backends buffer points internally, and the app polls [`IPenSession`](https://github.com/TheSevenPens/WinPenKit/blob/main/WinPenKit/IPenSession.cs) with `DrainPoints()` or `DrainPoints(Span<PenPoint>)` and `HasNewData` (ARCHITECTURE.md decision 1), so there is one code path whether points come from a background thread (Wintab) or from UI-thread events (everything else). [Stage 3](3-timing.md#how-winpenkit-handles-it) describes how the drains and the flag behave.

### PenPoint

[`PenPoint`](https://github.com/TheSevenPens/WinPenKit/blob/main/WinPenKit/PenPoint.cs) is a `readonly record struct`. Every backend produces the same struct, so drawing code does not change with the API. Positions are in physical desktop pixels on every backend (decision 2); converting to the canvas is the app's job ([Stage 5](5-desktop-to-canvas.md)). Both tilt representations are filled on every backend (decision 3); each backend computes the one its API does not provide ([Stage 6](6-values.md)).

| Field | Type | Unit | Where each backend gets it |
| --- | --- | --- | --- |
| `DesktopX`, `DesktopY` | `double` | Physical desktop pixels, sub-pixel where the source allows | Wintab system: `pkX`/`pkY`, whole pixels. Wintab high-res: tablet counts mapped through the context's `lcIn` and `lcSys` ranges. WM\_POINTER and WinForms: `ptHimetricLocationRaw` mapped through `GetPointerDeviceRects`, or `ptPixelLocationRaw` if the rects are unavailable. WPF, WinUI, Avalonia: the framework's DIP position scaled by DPI and added to the window origin. See [Stage 4](4-device-to-desktop.md). |
| `RawX`, `RawY` | `int` | `Conventions.RawUnits` | Wintab high-res: tablet counts. Wintab system, or high-res after fallback: screen pixels. WM\_POINTER and WinForms: hundredths of a millimetre (`ptHimetricLocationRaw`). WPF, WinUI, Avalonia: 0. A diagnostic, not a position. |
| `Pressure` | `uint` | 0 to `MaxPressure` | Wintab: `pkNormalPressure`, device range. WM\_POINTER and WinForms: 0 to 1024. WPF, WinUI, Avalonia: the framework's 0.0 to 1.0 value multiplied by 1024 and truncated to an integer. |
| `Azimuth` | `double` | Degrees, 0 to 360 | Wintab: `orAzimuth / 10`. Others: computed from tilt; 0 when the tilt magnitude is 0.5° or less. |
| `Altitude` | `double` | Degrees, 0 (flat) to 90 (vertical) | Wintab: `orAltitude / 10`. Others: `90 - sqrt(TiltX² + TiltY²)`, clamped. |
| `Twist` | `double` | Degrees, 0 to 360; 0 if not reported | Wintab: `orTwist / 10`. WM\_POINTER and WinForms: `rotation`. WPF: `TwistOrientation / 100`. WinUI and Avalonia: `Properties.Twist`. |
| `TiltX`, `TiltY` | `double` | Degrees, -90 to +90; `PenPoint` documents +X as a tilt to the right and +Y as a tilt toward the user. For Wintab, WinPenKit computes the sign itself and it has not been checked against a device ([Stage 6](6-values.md)) | Wintab: computed from azimuth and altitude. WM\_POINTER: `tiltX`/`tiltY`. WPF: `X/YTiltOrientation / 100`. WinUI and Avalonia: `XTilt`/`YTilt`. |
| `Z` | `int` | Wintab device units | Wintab: `pkZ`. Others: 0. |
| `Status` | `uint` | Wintab status bits | Wintab: `pkStatus`. Others: 0. |
| `Buttons` | `uint` | `Conventions.Buttons` | Wintab: one event per packet, `action << 16` combined with `buttonNumber` in the low word. Others: bitmask, bit 0 barrel, bit 1 eraser. |
| `Cursor` | `uint` | `Conventions.Cursor` | Wintab: `pkCursor`, the device's own number. Others: 13 (pen tip) or 14 (eraser). |
| `Source` | `InputApi` | | The API that produced the point. |
| `TimestampMicroseconds` | `long` | Microseconds, origin unstated | Wintab: `pkTime` (ms). WM\_POINTER and WinForms: `PerformanceCount` (QPC). WPF: event `Timestamp` (ms, one per batch). WinUI: `PointerPoint.Timestamp` (µs). Avalonia: event `Timestamp` (ms). Subtract two values; do not read one alone. See [Stage 3](3-timing.md). |

Derived members:

- `IsEraser` is `Cursor == PenCursorType.Eraser` (14). It is true while the eraser end is in proximity, before it touches.
- `IsInProximity` is `(Status & 0x0001) != 0`. Only Wintab sessions advertise `PenCapabilities.Proximity`; elsewhere `Status` is 0 and the property is false on every point, including hover points, so false there means "not reported". What the bit means on Wintab is an open question; see [Stage 6](6-values.md#traps), trap 7.
- `ButtonAction`, `ButtonNumber`, `IsButtonPressed`, `IsButtonReleased` and `IsTipPressed` are marked `[Obsolete]`. They decode the Wintab encoding whatever the source, so they are always false on the five pointer backends. Use `PenButtonTracker`, which decodes per `Source` and resets its state when the source changes between Wintab and a pointer backend.

### Session properties that say what the values mean

- `MaxPressure` is a range, not a count of distinguishable levels. Wintab sessions query `WTInfoA(WTI_DEVICES, DVC_NPRESSURE)`; every other session returns the API's fixed 1024. A Wacom DTH246 reports 32767 and resolves 8192 levels, in steps of 4.
- `Api` names the backend. `InputApi.Label()` gives the name to show in a dropdown: "Wintab", "Wintab (high-res)", "WM\_Pointer", "WinUI Pointer", "WPF Stylus", "Avalonia Pointer", "WinForms Pointer" (decision 11). The C ABI returns the same strings from `pen_session_get_api_label`. Before this, six hand-written tables in C#, C++ and Rust each spelled the names separately.
- `Capabilities` ([`PenCapabilities`](https://github.com/TheSevenPens/WinPenKit/blob/main/WinPenKit/PenCapabilities.cs)) says whether a feature is supported. The per-backend table is in [Stage 1](1-source.md).
- `Conventions` ([`PenConventions`](https://github.com/TheSevenPens/WinPenKit/blob/main/WinPenKit/PenConventions.cs)) says which convention a backend-dependent field follows (decision 10). It is a separate property from `Capabilities` because one flag answering both questions once let a hi-res capability flag survive a fallback that had turned hi-res off. `IPenSession.Conventions` has no default implementation, so a new backend that does not state its conventions does not compile.

| Session | `RawUnits` | `Buttons` | `Cursor` | `Timestamp` |
| --- | --- | --- | --- | --- |
| `WintabSystem` | `ScreenPixels` | `WintabEvent` | `DeviceAssigned` | `DeviceTicks` |
| `WintabDigitizer` | `TabletNative`, or `ScreenPixels` after fallback | `WintabEvent` | `DeviceAssigned` | `DeviceTicks` |
| `WmPointer`, `WinFormsPointer` | `HundredthsOfMillimetre` | `PointerFlags` | `Normalised` | `PerformanceCounter` |
| `WpfStylus`, `WinUiPointer`, `AvaloniaPointer` | `None` | `PointerFlags` | `Normalised` | `SystemTicks` |

`PenRawUnitsExtensions.Label()` gives the short unit name for a readout ("tablet", "px", "0.01mm", or empty for `None`).

### Creating and switching sessions

`PenSessionFactory.Create(api)` creates the framework-agnostic sessions; framework sessions need a UI element and are constructed directly (decision 4):

```csharp
IPenSession s1 = PenSessionFactory.Create(InputApi.WintabDigitizer);
IPenSession s2 = new WinUiPointerSession(canvasElement, hwnd);   // WinPenKit.WinUI
IPenSession s3 = new WpfStylusSession(canvasElement);            // WinPenKit.Wpf
IPenSession s4 = new AvaloniaPointerSession(control);            // WinPenKit.Avalonia
IPenSession s5 = new WinFormsPointerSession(form);               // WinPenKit.WinForms
```

Switching is a runtime operation, with no restart (decision 8):

```csharp
session.Stop();
session.Dispose();
session = PenSessionFactory.Create(newApi);   // or a framework constructor
session.Start(hwnd);
```

This works because each session owns its whole input path. A Wintab session creates and destroys its own pump window and thread; a pointer session adds and removes its subclass, message filter or event handlers. WinPenKit can do what Qt cannot because it owns the input layer instead of going through a framework's platform plugin. Switching was checked for context leaks: all nine ordered pairs of `WintabDigitizer`, `WintabSystem` and `WmPointer` through the factory (24 switches), and all six ordered pairs of Wintab, Wintab (high-res) and Avalonia Pointer through an app's settings dialog (12 switches). The driver's context count returned to its baseline every time.

Driver behaviour still applies (decision 7). If a driver suppresses WM\_POINTER once a Wintab context has been opened, switching to a pointer session may produce no data until the process restarts. Sequential stop-then-start switching has worked in practice, but this is not characterised across drivers.

### The native C ABI

[`WinPenKit.Native`](https://github.com/TheSevenPens/WinPenKit/blob/main/WinPenKit.Native/include/pen_session.h) is a C++ DLL for C++, Rust and other native callers. It shares no code with the managed library (decision 5); the two implement the same design separately. Its `PenPoint` struct has the same fields in snake case (`desktop_x` ... `timestamp_us`), and its `PenInputApi`, `PenCapabilities` and conventions enums use the same numeric values as the managed enums. `pen_session_get_point_size()` and `pen_session_get_conventions_size()` return the DLL's struct sizes. A binding should compare them with its own at startup and refuse to run on a mismatch, because `pen_session_drain_points` copies an array and a size difference misreads every point after the first. Both structs have grown once (`PenPoint` from 96 to 104 bytes, `PenConventions` from 12 to 16).

Differences from the managed library:

- Only Wintab system, Wintab high-res and WM\_POINTER. `pen_session_create` returns `NULL` for the four framework values, which exist only so `source` can carry them.
- No context keep-alive: a native Wintab session does not detect a tablet service restart or reopen its context.
- No packet counts (`IPacketCounts`).
- A different log: `%TEMP%\WintabSessionCpp.log`, one shared file, instead of `WinPenKit.<pid>.log`. It does not log the driver's context counts.
- No capture region for WM\_POINTER; the capture-region functions affect Wintab sessions only.
- Call `pen_session_get_conventions` and `pen_session_get_capabilities` after `pen_session_start`, because whether the high-res context opened is known only then.

## Traps

1. **Decoding `Buttons` with the obsolete helpers.** Symptom: barrel and tip presses never register on pointer backends. Fix: use `PenButtonTracker`.
2. **Using `IsEraser` on Wintab with a non-Wacom device.** `Cursor` is the device's own number and 13/14 are observed Wacom values. Symptom: the eraser works as a pen. Fix: check `Conventions.Cursor`; for `DeviceAssigned`, learn the device's numbers.
3. **Reading `RawX` as a position.** Symptom: a stroke in the wrong place, or all zeros on WPF, WinUI and Avalonia. Fix: draw from `DesktopX`/`DesktopY`; read `RawX` only with `Conventions.RawUnits`.
4. **Normalising pressure by 1024 on every backend.** Symptom: Wintab strokes reach full width at a light touch, because the range is often 8191 or 32767. Fix: divide by `session.MaxPressure`.
5. **Reading `Capabilities` or `Conventions` before `Start`.** Symptom: hi-res reported for a session that fell back to screen pixels. Fix: read them after `Start` returns.
6. **Starting the new session before stopping the old one.** Symptom: two input paths active at once, and on some drivers the pointer path goes quiet. Fix: `Stop()` and `Dispose()` first.
7. **Comparing timestamps across sessions or reading one as wall-clock time.** The origin differs per backend. Fix: subtract values from the same session only, and allow a difference of zero.
8. **A native binding with an old `PenPoint` definition.** Symptom: plausible numbers in every field after the first point. Fix: check `pen_session_get_point_size()` at startup.

## Further reading

- [Stage 1: Source](1-source.md), for discovery and capabilities per backend
- [Stage 2: Delivery](2-delivery.md), for how each session receives its data
- [Stage 3: Timing](3-timing.md) and [Stage 6: Values](6-values.md), for timestamps, pressure, tilt and buttons
- [Stage 8: Verifying the pipeline](8-verifying.md)
- [Build a Scribble app](../../build-a-scribble-app/README.md), [canonical WinForms](../../build-a-scribble-app/canonical-winforms.md), [canonical native](../../build-a-scribble-app/canonical-native.md)
- [How Krita and Qt handle pen input](../../misc/krita-and-qt/README.md) and [QTabletEvent](../../misc/krita-and-qt/qtabletevent.md)
- WinPenKit: [HOW\_TO\_USE.md](https://github.com/TheSevenPens/WinPenKit/blob/main/Docs/HOW_TO_USE.md), [ARCHITECTURE.md](https://github.com/TheSevenPens/WinPenKit/blob/main/Docs/ARCHITECTURE.md)
