# Stage 2: Delivery: getting packets to your code

This stage covers how pen data reaches your code once a source is chosen: which window receives it, on which thread, over which part of the screen, and for how long the connection stays valid. When it is done badly, the pen produces nothing in one framework, the first stroke after switching back to the app is lost, the app draws while the pen is over a different application, or the pen stops working after a driver restart with no error anywhere.

## In short

- In WPF, WinUI 3 and Avalonia, read pen input through the framework's own events; in WinForms, read WM\_POINTER through `Application.AddMessageFilter`; subclass the window only in raw Win32.
- Keep only pen input: filter on `PT_PEN` from `GetPointerType`, or the framework's pen device type.
- On Wintab, call `OnActivated()` from your window's activation event, or the first stroke after switching back to the app is lost.
- Pass your window handle to `Start`, or set `CaptureRegion`, because a Wintab session started without one reports points from the whole desktop.
- Keep calling `DrainPoints()` on a timer and close the app through its window, so a Wintab session can reopen its context after a driver restart and does not leak a context in the driver.

## The problem

WM\_POINTER messages go to the window under the pointer. In a raw Win32 app you can subclass that window and read them. UI frameworks have their own input stacks that process those messages before your window procedure runs, so in a framework app you have to receive pen input through the framework's own events or through a hook the framework allows.

Wintab works the other way round. The app passes a window handle to `WTOpenA`, and the driver posts `WT_PACKET` messages to that window wherever the pen is on the desktop. The app then calls `WTPacket` with the serial number from `wParam` to fetch the packet. The driver keeps contexts in an overlap order and delivers to the one on top. A context also belongs to the driver, not to your process: if your process ends without `WTClose`, or the tablet service restarts, the context's state changes without your code being told.

The paths therefore differ on four things a pen app has to make consistent: the receiving mechanism, the thread, the spatial scope, and what happens while the pen hovers.

## How the APIs differ here

| API | How data arrives | Thread | Natural spatial scope | Hover |
| --- | --- | --- | --- | --- |
| Wintab (both modes) | `WT_PACKET` posted to the window given to `WTOpenA`; the app calls `WTPacket` | Whichever thread owns that window; WinPenKit uses a dedicated background thread | The whole desktop | Full packets (position, tilt, buttons, cursor type) while in range. `WT_PROXIMITY` on entering and leaving range. The specification defines the `pkStatus` proximity bit (`TPS_PROXIMITY`) as set when the pen is out of the context, and WinPenKit reads it that way; this has not been checked against a logged `pkStatus` stream ([Stage 6](6-values.md#hover-and-proximity)). Packets stop when the pen leaves range. |
| WM\_POINTER, raw Win32 | `WM_POINTERDOWN`/`UPDATE`/`UP` to the window under the pen; read through `SetWindowSubclass` | UI thread | The window. Windows captures the pointer to the window on pen-down, so updates keep arriving while a pressed pen is dragged outside it. | `WM_POINTERUPDATE` with `INRANGE` set and `INCONTACT` clear; `WM_POINTERLEAVE` when the pen exits range |
| WM\_POINTER, WinForms | Same messages, read with `IMessageFilter` before dispatch | UI thread | Every window on the message loop | As above |
| WinUI 3 | `PointerPressed`/`PointerMoved`/`PointerReleased` on a `UIElement`. Input is routed through the composition `InputSite`, so no WM\_POINTER message reaches the top-level HWND, even if you subclass it. | UI thread | The element | `PointerMoved` with `IsInContact` false; `PointerEntered`/`PointerExited` mark range |
| WPF | `StylusDown`/`StylusMove`/`StylusUp`/`StylusInAirMove` on a `UIElement`, through WPF's own stylus stack (originally built on RTS, the "Wisp" stack) | UI thread | The element | `StylusInAirMove`; `StylusDevice.InAir` gives the state. Less data than contact events. |
| Avalonia | `PointerPressed`/`PointerMoved`/`PointerReleased` on a `Control` | UI thread | The control | `PointerMoved` while in range |
| egui / winit (Rust) | winit uses raw Win32, so subclassing works as in the Win32 row | UI thread | The window | As WM\_POINTER |
| RealTimeStylus | Plugins on an `IStylusPlugin` chain | Sync plugins on the pen thread, async plugins on the UI thread | The attached window | `IStylusPlugin::InAirPackets`, a separate callback from contact packets |

**Pointer IDs.** Every WM\_POINTER message carries a pointer ID in the low word of `wParam` (`GET_POINTERID_WPARAM`). Each contact has its own ID, so pen and touch can be active at once. Call `GetPointerType` on the ID and keep only `PT_PEN`, or touch and mouse input will be read as pen. Frameworks need the same filter: `TabletDeviceType.Stylus` in WPF, `PointerDeviceType.Pen` in WinUI, `PointerType.Pen` in Avalonia.

**WinForms.** WinForms processes WM\_POINTER in each form's own window procedure. Calling `NativeWindow.AssignHandle` on a form's HWND to intercept them crashes the process (exit code -1), because WinForms already owns that HWND through its own internal `NativeWindow`. `Application.AddMessageFilter` with an `IMessageFilter` works: it sees every message at the application message pump before any window procedure. Return `false` so WinForms still processes the message.

**WinUI 3 and WM\_POINTER.** Using the XAML pointer events and WM\_POINTER in the same WinUI app can conflict, because `PointerPoint` events are built on WM\_POINTER.

## How WinPenKit handles it

Every session implements [`IPenSession`](https://github.com/TheSevenPens/WinPenKit/blob/main/WinPenKit/IPenSession.cs): `Start(appWindowHandle)` returns `null` or an error string, `Stop()`, `IsRunning`, and the polled output `DrainPoints()` and `HasNewData`. Each session puts points into a `ConcurrentQueue<PenPoint>`, so the app reads them the same way whatever thread produced them ([Stage 7](7-output.md)).

### Wintab: its own window on its own thread

[`WintabMessagePump`](https://github.com/TheSevenPens/WinPenKit/blob/main/WinPenKit/Wintab/WintabMessagePump.cs) creates a background thread named `WinPenKit.WintabMessagePump`. On it, the pump registers a window class with a unique name and creates a hidden `WS_OVERLAPPED` top-level window with no parent. It does not use `HWND_MESSAGE`: the Wacom driver does not deliver `WT_PACKET` to message-only windows. The window procedure passes every message in the `WT_*` range (`0x7FF0` to `0x7FFF`) to the session. Because the session owns this window, Wintab works the same in every framework.

[`WintabSessionBase.Start`](https://github.com/TheSevenPens/WinPenKit/blob/main/WinPenKit/Wintab/WintabSessionBase.cs) records `PenCaptureRegion.Window(appWindowHandle)` as the default region, checks that Wintab is present, queries the maximum pressure, logs the driver's context counts ("before opening"), creates the pump, opens the context on the pump's HWND, and logs the counts again ("after opening"). `Stop` calls `WTClose`, logs "after closing", and disposes the pump. `Dispose` calls `Stop`.

`OnWintabMessage` handles only `WT_PACKET`; `WT_PROXIMITY` is ignored. For each packet it calls `WTPacket`, drops packets with `pkContext == 0`, converts the position ([Stage 4](4-device-to-desktop.md)), applies the capture region, and queues a `PenPoint`. The session implements `Diagnostics.IPacketCounts`, which counts at three points: `PacketsFromDriver` (before any filtering), `PacketsOutsideCaptureRegion` and `PointsDelivered`. Only Wintab sessions implement it; test for it with a type check.

### Wintab: getting the context back on top

When another application takes focus, your context drops down the driver's overlap order and nothing puts it back. The symptom is that the first stroke after returning to the app is lost and every later stroke draws. This was reproduced in the Avalonia, WinForms and WPF samples. `OnActivated()` calls `WTEnable(hCtx, true)` then `WTOverlap(hCtx, true)`, the same pair in the same order as Qt's `QWindowsTabletSupport::notifyActivate`, which is why Qt apps such as Krita do not show the problem while Clip Studio Paint does. A failure is logged, not thrown.

The context is bound to the hidden pump window, which never receives `WM_ACTIVATE`, so the app has to call `OnActivated()` from its real window's activation event. Every sample does: `Activated += (_, _) => _session?.OnActivated();` in WPF, WinForms and Avalonia; WinUI checks `WindowActivationState != Deactivated` first; Win32 and Rust call `pen_session_on_activated`. On pointer sessions it is a default interface method that does nothing, so a wrapper class that holds an `IPenSession` must forward the call explicitly or the Wintab session never receives it.

### Wintab: noticing that the driver took the context away

Restarting the tablet service invalidates every open context and tells no application. Measured before WinPenKit handled it: an app kept running, its status line still said "Wintab (high-res)", nothing was logged, and the pen stopped working. `WTGetA` returns false for a handle the driver no longer knows.

`KeepContextAlive()` runs at the start of every `DrainPoints` call, paced to once a second. If `WTGetA` fails it logs that the context was taken away, sets `IsRunning` to false, and opens a new context. If the reopen fails it waits five seconds before trying again: a refusing driver takes about 90 ms to answer, which would cause a visible stutter once a second on the drawing thread. While the service is restarting, the driver returns degenerate defaults (`Options=0x5`, `Device=0` instead of `0x8015` and `4294967295`) and an open based on them is refused, so the first retry usually fails and a later one succeeds. The check runs only from the drain, so an app that stops calling `DrainPoints` does not recover.

### Wintab: leaked contexts

These conclusions come from WinPenKit's [WINTAB-CONTEXT-LEAK.md](https://github.com/TheSevenPens/WinPenKit/blob/main/Docs/WINTAB-CONTEXT-LEAK.md), measured on one Wacom driver (Wacom Tablet 6.4.14-1, Cintiq 24, Windows 11). Other vendors' drivers were not tested.

- **A process that ends without `WTClose` leaves its context in the driver.** This happens when the process is killed (Task Manager, `Stop-Process`, a debugger's stop button), crashes, returns from `main` without closing, or destroys its window before exit. A default (virtual device) open takes two counter units. Krita and Clip Studio Paint leak the same way when killed.
- **The driver collects half of a leak, once, at the next pen input.** It does not collect on a timer, so an idle tablet keeps the leaked count. The other half stays until the tablet service restarts. WinPenKit's own code comment saying the driver "never takes it back" is out of date on this point.
- **A context manager can close known leaked contexts** (`WTMgrContextEnum`, then `WTClose` on each) without a service restart, on the tested driver. Run while the pen was in contact, this was followed by a heap-corruption crash in `Wacom_Tablet.exe`. Do not close another process's context while the pen is in use, and do not use this as a production cleanup tool.
- **The count is not a capacity limit.** `IFC_NCONTEXTS` reports 32 and opens succeed well past it. A high count shows leaks, not exhaustion.
- **Restarting the tablet service clears a driver that refuses every open**, in seconds: `Restart-Service WTabletServicePro -Force` from an administrator PowerShell on a Wacom machine. It invalidates every running app's context; WinPenKit sessions reopen on their own.
- **Switching pen API in WinPenKit does not leak.** Each session has exactly one `WTOpenA` and one `WTClose`.

What a developer should do: close pen apps through their window, not by killing them; close every window your automated tests show, enforced in the test harness, because a suite that drops windows leaks far faster than manual use (41 runs took one machine from 22 to 1074 counter units); and read the log. Each process writes `%TEMP%\WinPenKit.<pid>.log` (the native DLL writes `%TEMP%\WintabSessionCpp.log`), and each Wintab session brackets itself with "Contexts before opening", "after opening" and "after closing" lines. A run with no "after closing" line was killed and leaked its context. `Start(IntPtr.Zero)` still opens a real context through the pump window, so headless tests on a machine with a tablet are not isolated from the driver.

### WM\_POINTER and the framework sessions

- [`WmPointerSession`](https://github.com/TheSevenPens/WinPenKit/blob/main/WinPenKit/Pointer/WmPointerSession.cs) requires a window handle (`Start` returns an error without one), installs a subclass with `SetWindowSubclass` (ID `0xAE5E5510`), handles `WM_POINTERUPDATE`, `WM_POINTERDOWN` and `WM_POINTERUP`, and removes the subclass on `WM_NCDESTROY` or `Stop`. It reads `GET_POINTERID_WPARAM` and keeps only `PT_PEN`.
- [`WinFormsPointerSession`](https://github.com/TheSevenPens/WinPenKit/blob/main/WinPenKit.WinForms/WinFormsPointerSession.cs) implements `IMessageFilter` and calls `Application.AddMessageFilter(this)` in `Start`. `PreFilterMessage` always returns `false`. Some WinPenKit comments (`InputApi.cs`, `WinFormsPenApis.cs`, `pen_session.h`) still say it uses a `NativeWindow` WndProc override; the code uses `IMessageFilter`.
- [`WpfStylusSession`](https://github.com/TheSevenPens/WinPenKit/blob/main/WinPenKit.Wpf/WpfStylusSession.cs) subscribes to `StylusMove`, `StylusDown`, `StylusUp` and `StylusInAirMove` on the element.
- [`WinUiPointerSession`](https://github.com/TheSevenPens/WinPenKit/blob/main/WinPenKit.WinUI/WinUiPointerSession.cs) subscribes to `PointerMoved`, `PointerPressed` and `PointerReleased`. It takes the HWND in its constructor and ignores the one passed to `Start`.
- [`AvaloniaPointerSession`](https://github.com/TheSevenPens/WinPenKit/blob/main/WinPenKit.Avalonia/AvaloniaPointerSession.cs) adds handlers for the same three events with `RoutingStrategies.Tunnel`, so it receives them before a child control such as a `TextBox` can mark them handled.

### Capture region: one spatial scope for every backend

[`IPenCaptureRegion`](https://github.com/TheSevenPens/WinPenKit/blob/main/WinPenKit/CaptureRegion.cs) has one method, `Contains(desktopX, desktopY)`, in physical screen pixels. Each session tests it before queuing a point. `PenCaptureRegion` provides three regions:

- `Unbounded`: accepts every point. Only sessions with `PenCapabilities.GlobalCapture` (the two Wintab sessions) can deliver points outside the app window; on the others it has no effect.
- `Window(hwnd)`: calls `GetWindowRect` on every point, so it follows moves and resizes. The rectangle includes the title bar and border. A zero handle, or a failed `GetWindowRect`, accepts every point.
- `Rect(x, y, w, h)`: a fixed rectangle, left and top inclusive, right and bottom exclusive.

`CaptureRegion` can be set before or after `Start` and applies from the next point. The filter is a rectangle test only: a point passes even if another window covers it.

WinPenKit's own docs say a `null` region means window-scoped on every backend. The code does this:

| Session | `CaptureRegion == null` means |
| --- | --- |
| Wintab, `Start(hwnd)` | `Window(hwnd)` |
| Wintab, `Start()` or `Start(IntPtr.Zero)` (as in the C# Quick Start) | No filtering: the whole desktop, including over other applications |
| `WmPointer` | `Window(hwnd)`; this drops the points that pointer capture delivers after a pressed pen leaves the window |
| `WinFormsPointer` | `Window` of the handle passed to `Start`, or else of the control's handle if it exists, or else no filtering |
| `WpfStylus`, `WinUiPointer`, `AvaloniaPointer` | No filtering. Points arrive only from the framework's events on the element, so the scope is whatever those events cover. |

`Contains` runs on the thread that produces points. For Wintab that is the pump thread, not the UI thread, so a region must be thread-safe and must not touch UI objects. Cache bounds on the UI thread and read the cached value; return `true` while the bounds are unknown, so input is not dropped. [`ControlCaptureRegion`](https://github.com/TheSevenPens/WinPenKit/blob/main/WinPenKit.Avalonia/ControlCaptureRegion.cs) in WinPenKit.Avalonia is the reference implementation: it recomputes the control's screen rectangle on layout updates and window moves, and `Contains` only reads the cache. Construct and dispose it on the UI thread.

The native DLL ([`pen_session.h`](https://github.com/TheSevenPens/WinPenKit/blob/main/WinPenKit.Native/include/pen_session.h)) has `pen_session_set_capture_window`, `pen_session_set_capture_rect` and `pen_session_set_capture_unbounded`, which apply to Wintab sessions only. `pen_session_start` with a window scopes Wintab to that window; with `NULL` it reports the whole desktop. The native WM\_POINTER session has no region and does not filter points that arrive through pointer capture.

## Traps

1. **Creating the Wintab window with `HWND_MESSAGE` as parent.** Symptom: the context opens and no packets arrive. Fix: create a hidden top-level window with no parent.
2. **Subclassing the HWND in a WPF, WinUI or Avalonia app.** Symptom: no pointer messages. Fix: use the framework's events, or Wintab.
3. **Calling `NativeWindow.AssignHandle` on a WinForms form.** Symptom: the process exits with code -1. Fix: `IMessageFilter`.
4. **Not filtering by pointer type.** Symptom: touch or mouse movement draws strokes. Fix: keep only `PT_PEN` (or the framework equivalent).
5. **Not calling `OnActivated()` from the window's activation event.** Symptom: on Wintab, the first stroke after returning to the app is lost. Fix: wire the activation event, and forward the call through any wrapper.
6. **Starting Wintab without a window handle.** Symptom: the app draws while the pen is over other applications. Fix: pass the app's HWND to `Start`, or set `CaptureRegion`.
7. **Reading UI state inside `Contains`.** Symptom: cross-thread exceptions or stale bounds on Wintab. Fix: cache bounds on the UI thread.
8. **Stopping the drain loop while the window is hidden or idle.** Symptom: after a tablet service restart the pen does not come back. Fix: keep calling `DrainPoints` on the frame timer.
9. **Ending the process without `Stop()`.** Symptom: the driver's context count climbs across runs; on a machine with many leaks, opens can fail. Fix: close apps and test windows normally; restart the tablet service to clear the driver.
10. **Hosting Wintab in a console or windowless process.** Wintab delivers `WT_PACKET` to the foreground application, and the pump window is never shown. Symptom: no packets, which looks the same as nobody drawing. Fix: give the host a visible foreground window.

## Further reading

- [Stage 1: Source](1-source.md), for which APIs a framework can use
- [Stage 3: Timing](3-timing.md), for what arrives in each delivery
- [Stage 7: The output contract](7-output.md), for `DrainPoints` and switching sessions
- [Build a Scribble app](../../build-a-scribble-app/README.md) and [framework deltas](../../build-a-scribble-app/framework-deltas.md)
- WinPenKit: [HOW\_TO\_USE.md, capture region](https://github.com/TheSevenPens/WinPenKit/blob/main/Docs/HOW_TO_USE.md#capture-region-spatial-scope), [WINTAB-CONTEXT-LEAK.md](https://github.com/TheSevenPens/WinPenKit/blob/main/Docs/WINTAB-CONTEXT-LEAK.md), [STYLUS.md](https://github.com/TheSevenPens/WinPenKit/blob/main/Docs/STYLUS.md)
- [WinTabUtils](https://github.com/TheSevenPens/WinTabUtils): a small app that shows the driver's context count, with a button that restarts the Wacom driver
