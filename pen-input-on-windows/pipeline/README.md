# The pen input pipeline

Windows has several APIs for reading a pen: Wintab, WM\_POINTER, RealTimeStylus, and the pointer or stylus events of each UI framework (WPF, WinUI 3, WinForms, Avalonia). Comparing them one API at a time produces a long list of differences with no order to them. This section uses a different structure. Every pen API, whichever one you pick, has to do the same six jobs to turn a pen touching a tablet into a point on your canvas. The differences between the APIs are differences in how each one does those jobs.

[WinPenKit](https://github.com/TheSevenPens/WinPenKit) is a library that reads pen input through all of these APIs and returns the same `PenPoint` stream from each of them. Its code is organised around those six jobs, so it serves here as a reference implementation. Each stage page explains one job, describes how each API behaves at that job, and shows the WinPenKit code that makes the APIs agree.

## The stages

```
 Tablet + driver
      │
 [1] Source        Which driver path and which API produce the data,
      │            and what that API is able to report.
 [2] Delivery      Which thread and which window receive the data, for which
      │            region of the screen, and what happens when focus changes.
 [3] Timing        How points are batched, how coalesced points are recovered,
      │            and what each point's timestamp means.
 [4] Position      Device units (tablet counts, HIMETRIC, DIPs, pixels)
      │            converted to physical desktop pixels.
 [5] Position      Desktop pixels converted to your canvas, without
      │            truncating the fractional part.
 [6] Values        Pressure, tilt, twist, buttons and eraser, each in one
      │            stated unit and encoding.
 [7] Output        One PenPoint stream, polled with DrainPoints(), with
      │            the same meaning whichever API produced it.
 Your app
```

| Stage | Page | WinPenKit code to read |
|---|---|---|
| 1 | [Source: drivers and APIs](1-source.md) | `InputApi`, `PenSessionFactory`, `*PenApis.GetAvailable()`, `PenCapabilities` |
| 2 | [Delivery: getting packets to your code](2-delivery.md) | `WintabMessagePump`, `WmPointerSession`, the framework sessions, `CaptureRegion`, `OnActivated()` |
| 3 | [Timing: batches, coalescing and timestamps](3-timing.md) | `WmPointerSession` history replay, `PenTimestamp`, `DrainPoints()` |
| 4 | [Position: device units to desktop pixels](4-device-to-desktop.md) | `WintabSystemSession`, `WintabDigitizerSession`, `WmPointerSession`, `WpfCoordinates` |
| 5 | [Position: desktop pixels to your canvas](5-desktop-to-canvas.md) | `WpfCoordinates`, the Scribble apps |
| 6 | [Values: pressure, tilt, buttons and eraser](6-values.md) | `PenConventions`, `PenButtonTracker`, `PenCursorType` |
| 7 | [The output contract: PenPoint and switching APIs](7-output.md) | `PenPoint`, `IPenSession` |
| 8 | [Verifying the pipeline](8-verifying.md) | `SelfTest`, `StrokeReplay`, the mapping wizard |

The [API reference card](api-reference.md) puts what each API exposes into one table, with links back to the stage that explains each row.

## Terms used in this section

* **Wintab.** A pen API defined by Wacom in 1991 and implemented by each tablet vendor's driver in its own `wintab32.dll`. An application opens a *context* that describes which packet fields it wants and how positions are scaled.
* **Wintab system context and high-res context.** Both are opened from the driver's default system context (`WTI_DEFSYSCTX`). The system context reports positions in screen pixels. The high-res context, also called the digitizer context, sets the output extent equal to the input extent, so positions arrive in tablet counts and the application scales them itself. It is the same context type with a different output extent, not a separate kind of context. WinPenKit calls these `WintabSystem` and `WintabDigitizer` ("Wintab (high-res)").
* **WM\_POINTER.** The Win32 pointer messages (`WM_POINTERDOWN`, `WM_POINTERUPDATE`, `WM_POINTERUP`) introduced in Windows 8, which carry pen, touch and mouse input.
* **Framework APIs.** WPF stylus events, WinUI 3 `PointerPoint`, Avalonia pointer events, and WinForms, which has no pen API of its own and receives WM\_POINTER messages through a message filter.
* **"Windows Ink".** This name is used for three different things: Microsoft's brand for pen features, the checkbox in a tablet driver that enables the WM\_POINTER path, and, loosely, the WM\_POINTER family of APIs. This section uses the specific API names instead. See [Stage 1](1-source.md) for the driver checkbox.
* **Desktop pixels.** Physical pixels on the virtual desktop that spans all monitors. This is the one coordinate space every WinPenKit backend reports in.

## Why this is hard on Windows

Windows has accumulated pen APIs over thirty years, and the official documentation describes each API separately without describing how to combine them or which one fits a given framework. Tablet vendors ship a third-party API (Wintab) alongside the operating system's own. Each UI framework intercepts pointer input differently, which changes which APIs an application can use. The stage pages describe each of these problems at the point in the pipeline where it affects the data.

## Related sections

* [Build a Scribble app](../../build-a-scribble-app/README.md) builds a drawing app in each framework on top of WinPenKit.
* [Windows pen behaviors](../windows-pen-behaviors/README.md) covers the shell's own pen feedback and gestures, which act on pen input before or alongside your application.
* [Processing pen data](../../processing-pen-data/README.md) and [Rendering options for paint apps](../../rendering-for-pen-apps.md) cover what an application does with the points after stage 7.
* [How Krita & Qt handle pen input](../../misc/krita-and-qt/README.md) is a second implementation to compare against WinPenKit.
