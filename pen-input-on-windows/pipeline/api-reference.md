# API reference card

One table of what each Windows pen API exposes, followed by short notes per API. The stage pages explain each row; this page is for looking a value up.

## In short

- Wintab works in every framework; WM\_POINTER works directly only in raw Win32 and through `IMessageFilter` in WinForms; WPF, WinUI 3 and Avalonia use their own pen events.
- Wintab high-res, WM\_POINTER (through `ptHimetricLocationRaw`), WPF, WinUI 3 and Avalonia all deliver sub-pixel positions; only the Wintab system context is limited to whole pixels.
- Pressure maximums differ (Wintab: the device's `axMax`; pointer backends: 1024), so always divide by the session's `MaxPressure`.
- Among the APIs WinPenKit implements, only Wintab reports Z, separate barrel buttons and a proximity status; RealTimeStylus also exposes Z and barrel pressure but has no WinPenKit backend.
- The tablet's sample rate (180 Hz on the DTH246) is a property of the device and was the same on every API measured.

Each cell is tagged with where the statement comes from:

* **K**: WinPenKit's code, or a measurement recorded in WinPenKit (Wacom DTH246, September 2026, unless stated).
* **M**: Microsoft documentation.
* **W**: the Wintab specification or Wacom documentation and tools.
* **N**: earlier notes on this site, not verified against code or documentation.

WinForms here means WM\_POINTER read through an `IMessageFilter`, which is how WinPenKit's `WinFormsPointerSession` does it. RealTimeStylus has no WinPenKit backend, so its column has no **K** entries.

## The matrix

| | Wintab system | Wintab high-res | WM\_POINTER | WPF Stylus | WinUI 3 PointerPoint | WinForms (WM\_POINTER) | Avalonia | RealTimeStylus |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **WinPenKit backend** | `WintabSystem` K | `WintabDigitizer`, "Wintab (high-res)" K | `WmPointer` K | `WpfStylus` K | `WinUiPointer` K | `WinFormsPointer` K | `AvaloniaPointer` K | none |
| **Position units** | screen pixels, whole K | tablet counts K | `ptHimetricLocationRaw` (0.01 mm) mapped through `GetPointerDeviceRects`; whole-pixel fallback K | element DIPs, `double` K | element DIPs (effective pixels) K | as WM\_POINTER K | element DIPs, `double` K | HIMETRIC (0.01 mm) M |
| **Sub-pixel position** | no K | yes K | yes, about 7x finer than pixels K | yes K | yes K | yes K | yes on Windows K | unit allows it; depends on driver N |
| **Pressure** | 0 to `DVC_NPRESSURE` `axMax` (32767 on DTH246, 8192 resolved) K | same K | `UINT32` 0 to 1024 M K | `PressureFactor` `float` 0 to 1 M | `Pressure` `float` 0 to 1 M | 0 to 1024 K | `float` 0 to 1 K | device-specific M |
| **Tilt** | azimuth, altitude in 0.1° W K | same W K | `tiltX`, `tiltY`, whole degrees, -90 to +90 M K | `XTiltOrientation`, `YTiltOrientation`, read as 0.01° K | `XTilt`, `YTilt`, degrees M | as WM\_POINTER K | `XTilt`, `YTilt`, degrees K | azimuth, altitude and X/Y tilt properties M |
| **Twist** | `orTwist`, 0 to 3600 (0.1°) W K | same W K | `rotation`, 0 to 359° M; capability flag set K | `TwistOrientation` when reported; flag set K | `Twist` M; flag set K | as WM\_POINTER K | `Twist`; flag set K | twist property M |
| **Barrel (tangential) pressure** | `pkTangentPressure`; no `PenPoint` field K | same K | no M | not read by WinPenKit | not read by WinPenKit | no | not read by WinPenKit | packet property N |
| **Z (height)** | `pkZ` W K | same W K | no M | not read by WinPenKit | not read by WinPenKit | no | not read by WinPenKit | packet property N |
| **Barrel buttons** | each button separately (1 to 3); event encoding in relative mode K | same K | one flag, `PEN_FLAG_BARREL` M K | `StylusButtons`; WinPenKit folds all non-tip buttons into one K | one flag, `IsBarrelButtonPressed` M | one flag K | one flag K | button properties N |
| **Eraser** | `pkCursor`, number assigned by the device (13 and 14 observed on Wacom); known on hover K | same K | `PEN_FLAG_INVERTED`, `PEN_FLAG_ERASER` M K | `Inverted` M K | `IsEraser` M K | as WM\_POINTER K | `IsEraser` K | cursor identity N |
| **Hover** | full packets while in range; `WT_PROXIMITY` W | same W | `WM_POINTERUPDATE` in range, not in contact; `WM_POINTERLEAVE` on exit M | `StylusInAirMove` M K | `PointerMoved` with `IsInContact` false M K | as WM\_POINTER | `PointerMoved` K | `InAirPackets` callback M |
| **Proximity flag in WinPenKit** | yes, raw `pkStatus`; `IsInProximity` is false on the leaving packet K | yes K | no; `IsInProximity` true on every point K | no; true on every point K | no; true on every point K | no; true on every point K | no; true on every point K | none |
| **Delivery thread** | thread owning the `WTOpen` window; WinPenKit's background thread K | same K | UI thread K | UI thread K | UI thread K | UI thread K | UI thread K | sync plug-in: pen thread; async: UI thread M |
| **Merged samples** | none; one message per packet K | same K | merged; `GetPointerPenInfoHistory`, newest first K | batch per event, `GetStylusPoints` K | merged; `GetIntermediatePoints`, newest first (measured; Microsoft documents the reverse) K | as WM\_POINTER K | merged; `GetIntermediatePoints`, oldest first (measured) K | packets arrive in arrays per callback M |
| **Timestamp resolution** | `pkTime`, 1 ms (measured on high-res) K | 1 ms, one per point K | `PerformanceCount`, 1 µs K | 1 ms clock, one per event (about 3 points each) K | 1 µs K | 1 µs K | 1 ms; one per event K | not measured |
| **Native spatial scope** | whole desktop K | whole desktop K | the window K | the element K | the element K | the whole application K | the control K | the attached window M |
| **System cursor follows pen** | yes, because the context is opened with `CXO_SYSTEM` W K | yes, same option K | yes K | yes K | yes K | yes K | yes K | earlier notes said no; not verified N |
| **Tablet brands** | any vendor that ships `Wintab32.dll`; WinPenKit has run on Wacom and Huion drivers K | same; position correct on mixed DPI only when the driver reports physical pixels (Wacom does, Huion V20 does not) K | any pen with a Windows Ink driver M | same M | same M | same M | same M | same M |
| **Works in** | any framework; it opens its own window K | same K | raw Win32 only: WPF, WinForms, WinUI and Avalonia consume the messages before a subclass sees them K | WPF only | WinUI 3 only | WinForms only | Avalonia only | WinForms and WPF through COM interop; others through COM N |
| **Multiple monitors** | works N | works; WinPenKit maps onto the driver's `lcSys` rectangle K | works N | works N | works N | works N | works N | works N |

Every pointer-family backend in WinPenKit reports `MaxPressure` as 1024 and scales the framework `float` by 1024, truncating. Every backend measured in WinPenKit agreed that the DTH246 reports at **180 Hz**: the rate belongs to the device, not to the API.

## How precise the position is

| API | Typical X range | Example |
| --- | --- | --- |
| Wintab system | 0 to 3840 | one 4K monitor, 3840 physical pixels wide |
| Wintab high-res | 0 to about 34,900 | Wacom Intuos Pro Large (PTK-870), 349 mm active width, as reported in Wacom's driver diagnostics: about 100 counts per mm on both axes (Y reaches about 19,500) W |
| WM\_POINTER, WinForms | 0 to 3840, with a fraction | pixels mapped from 0.01 mm units K |
| WinUI 3 | 0 to about 1707 | the same 4K monitor at 225% scaling, 3840 / 2.25 |
| WPF, Avalonia | depends on layout and scaling | DIPs |
| RealTimeStylus | 0 to about 26,400 | a 264 mm wide tablet in 0.01 mm units |

Use the counts the driver reports, not the marketed LPI; HIMETRIC's "about 2540 per inch" is the definition of the unit, not a hardware limit. WM\_POINTER is not limited to whole pixels, because `POINTER_INFO` carries `ptHimetricLocationRaw` as well as `ptPixelLocationRaw`. [Stage 4](4-device-to-desktop.md) has the measurements for both statements.

## Per-API notes

### Wintab (system context)

Provided by the tablet driver's `Wintab32.dll`, since 1991. WinPenKit opens a context from `WTI_DEFSYSCTX` with `CXO_SYSTEM | CXO_MESSAGES`, so the driver maps the tablet to the screen and also moves the system cursor. `pkX`/`pkY` arrive as whole screen pixels, and `pkCursor` passes through as the device's own number. The only API WinPenKit implements with barrel pressure and Z, but WinPenKit does not expose barrel pressure. Packets arrive on WinPenKit's own thread, regardless of UI load. Delivery and focus: [Stage 2](2-delivery.md). Mapping: [Stage 4](4-device-to-desktop.md). Values: [Stage 6](6-values.md).

### Wintab (high-res, digitizer context)

The system context with its output range set to its input range, so packets arrive in tablet counts instead of screen pixels ([Stage 1](1-source.md#two-wintab-modes-one-context-type)). WinPenKit keeps `CXO_SYSTEM`, so the cursor still follows the pen, and maps counts onto the driver's `lcSys` rectangle in floating point (`ScaleAxis`). If the open fails, it falls back to screen pixels and clears `PenCapabilities.HiRes`. Qt opens this context unconditionally; see [Qt pen API implementation notes](../../misc/krita-and-qt/qt-pen-api-implementation-notes.md#qt-always-uses-the-high-resolution-tablet-native-context). Mapping on mixed DPI: [Stage 4](4-device-to-desktop.md).

### WM\_POINTER

Built into Windows since Windows 8; no third-party driver required. WinPenKit subclasses the window with `SetWindowSubclass`, filters to `PT_PEN` with `GetPointerType`, recovers merged updates with `GetPointerPenInfoHistory` (`count > 1`, replayed newest to oldest), and reads position from `ptHimetricLocationRaw`. Timestamps come from `PerformanceCount`, not `dwTime`. Pointer IDs distinguish pen and touch contacts, which can coexist. The process's DPI awareness decides what pixel coordinates mean. Some drivers suppress WM\_POINTER pen events after Wintab is loaded or a context opened; switching works when sessions are stopped and started cleanly, but this depends on the driver. Timing: [Stage 3](3-timing.md). Position: [Stage 4](4-device-to-desktop.md).

### WinForms (WM\_POINTER through `IMessageFilter`)

The same messages as WM\_POINTER, read with `Application.AddMessageFilter`. `NativeWindow.AssignHandle` on a Form's handle crashes, which is why WinPenKit does not subclass. The filter is application-wide, so WinPenKit scopes points to the window or control by default. Conversion to the canvas: [Stage 5](5-desktop-to-canvas.md).

### WPF Stylus

`StylusMove`, `StylusDown`, `StylusUp` and `StylusInAirMove` on an element, each carrying a `StylusPointCollection`. WPF handles pen input in its own stylus stack (originally built on RealTimeStylus, the "Wisp" stack), so a WM\_POINTER subclass sees nothing. Positions are sub-pixel DIPs; converting them with `PointToScreen` truncates to whole pixels, so WinPenKit applies a transform computed once per event (`WpfCoordinates.GetTransform`). The timestamp belongs to the event. `InkCanvas` renders ink without code but is limited for custom brush engines. [Stage 5](5-desktop-to-canvas.md), [Stage 3](3-timing.md).

### WinUI 3 PointerPoint

XAML `PointerMoved`, `PointerPressed`, `PointerReleased`, built on WM\_POINTER; mixing a raw WM\_POINTER hook with these events in one app can conflict. Positions are element DIPs; WinPenKit converts with `TransformToVisual`, the monitor DPI and `ClientToScreen` under a Per-Monitor V2 thread context. That thread context is a safeguard: WinPenKit has no recorded case where it was needed in a process whose manifest declares Per-Monitor V2 ([Stage 4](4-device-to-desktop.md)). `GetIntermediatePoints` is newest first. Its timestamp is microsecond-resolved and is the one WinPenKit does not anchor against a 32-bit wrap. [Stage 3](3-timing.md), [Stage 5](5-desktop-to-canvas.md).

### Avalonia

Pointer events attached with tunnel routing, so child controls cannot mark them handled first. On Windows, Avalonia itself reads `ptHimetricLocationRaw` and maps it through `GetPointerDeviceRects`, so positions carry a fraction; `PointToScreen` returns an integer `PixelPoint`, so WinPenKit converts only the window origin with it. `GetIntermediatePoints` is oldest first. `PointerEventArgs.Timestamp` is a 64-bit property filled from 32-bit `GetMessageTime`. [Stage 3](3-timing.md), [Stage 5](5-desktop-to-canvas.md).

### RealTimeStylus

A COM API from about 2005, introduced with Windows XP Tablet PC Edition and part of Windows from Vista. It still ships, but Microsoft has not changed it since Windows 7, and WM\_POINTER is its successor. In .NET it needs COM interop. Plug-ins added to the synchronous list run on the pen thread; asynchronous plug-ins run on the UI thread. Positions are HIMETRIC. Pressure, tilt (both representations), twist, tangential pressure and Z are packet properties, available when the device reports them, so "only Wintab has barrel pressure and Z" is true only among the APIs WinPenKit implements. Hover arrives through `InAirPackets`. WinPenKit has no backend for it, and none of its values have been measured here.

## Further reading

* [The pipeline at a glance](README.md) for how the stages fit together.
* [Stage 1: Source](1-source.md) for choosing between these APIs.
* [Stage 7: The output contract](7-output.md) for what WinPenKit's `PenPoint`, `PenCapabilities` and `PenConventions` report for each backend.
* WinPenKit's [STYLUS.md](https://github.com/TheSevenPens/WinPenKit/blob/main/Docs/STYLUS.md) and [HOW\_TO\_USE.md](https://github.com/TheSevenPens/WinPenKit/blob/main/Docs/HOW_TO_USE.md). Where those disagree with this page, this page follows the code.
