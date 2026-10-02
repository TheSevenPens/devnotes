# Stage 1: Source: drivers and APIs

This stage decides where pen data comes from: which input paths the tablet driver exposes, which API your application reads, and how that API is opened. When it is done badly the visible symptoms are an API in the app's dropdown that never produces a point, a Wintab context that opens successfully and then delivers no packets, or packets whose fields are shifted so that pressure holds the Z value.

## In short

- Pick the API from what your UI framework allows: Wintab works in every framework, WM\_POINTER only in raw Win32 (and in WinForms through `IMessageFilter`), and WPF, WinUI 3 and Avalonia reach the pointer path only through their own pen events.
- Build the API list from the framework package's `GetAvailable()` (for example `WpfPenApis.GetAvailable()`), not from `PenSessionFactory.GetAvailableApis()`, so the app never offers an API that cannot deliver points.
- Open a Wintab context from `WTI_DEFSYSCTX` with `CXO_SYSTEM` set, `lcPktData` set to the fields your `PACKET` struct declares, and `pkContext` declared as a pointer-sized type.
- The high-res (digitizer) context is the system context with its output range set to its input range, and it can fall back to screen pixels, so check `Capabilities.HasFlag(PenCapabilities.HiRes)` after `Start`.
- Run one session at a time, because some drivers stop delivering one path while the other is open.

## The problem

Windows has had pen input for a long time, so there are several APIs, from more than one vendor, and the UI framework you choose limits which of them you can use. Microsoft's documentation works as reference material, but it does not say which API works in which situation, what the trade-offs are, or how to assemble the pieces into a working app, and there are few end-to-end samples.

The APIs, in order of introduction:

| API | Provided by | Introduced | Notes |
| --- | --- | --- | --- |
| Wintab | The tablet driver (`wintab32.dll`), originally Wacom | 1991 | Nearly every creative app supports it. For a long time it was the only way to get pressure and tilt from a drawing tablet. |
| RealTimeStylus (RTS) | Windows (Tablet PC effort) | about 2005, with Windows XP Tablet PC Edition; part of Windows from Vista | COM API. Still ships, but Microsoft has not changed it since Windows 7. Before Windows 8 it could not have used WM\_POINTER; whether it uses it now is not established. |
| WPF `StylusPoint` | WPF 1.0 | late 2006 | Originally built on RTS (the "Wisp" stack). Whether current WPF still routes through RTS by default is not fully established; WinPenKit treats it as its own stack. |
| WM\_POINTER | Windows 8 | 2012 | Win32 messages that unify pen, touch and mouse. |
| WinUI `PointerPoint` | Windows 10 / Windows App SDK | | Built on WM\_POINTER. |

`InkCanvas` (WPF and WinUI) is a ready-made control that renders ink. It is easy to use but limited for a custom brush engine, so it is outside this pipeline.

### "Windows Ink" is not an API name

The phrase means different things depending on who uses it:

| Context | "Windows Ink" means |
| --- | --- |
| End user, Microsoft marketing | The pen feature brand from Windows 10 Anniversary Update (2016): Ink Workspace, Sticky Notes, Screen Sketch, handwriting in text fields |
| Tablet driver settings | The checkbox that turns the WM\_POINTER path on or off alongside Wintab |
| App developer | WM\_POINTER and/or a framework's pointer or stylus events |
| App preferences ("Use Windows Ink") | The app reads WM\_POINTER instead of Wintab |

So "turn off Windows Ink in the driver to fix the lag" means "disable the driver's WM\_POINTER path so only Wintab is active", and "we switched from Wintab to Windows Ink" means "the app now reads WM\_POINTER or a framework layer on top of it". In technical discussion, name the specific API: WM\_POINTER, `PointerPoint`, `StylusPoint` or `InkCanvas`.

### The driver decides what is available

Tablet drivers always expose Wintab; it cannot be turned off. The WM\_POINTER path is optional:

| Driver setting | APIs available |
| --- | --- |
| Windows Ink **enabled** (the default for Wacom, Huion and XP-Pen drivers) | Wintab and WM\_POINTER |
| Windows Ink **disabled** | Wintab only |

With Windows Ink disabled, WM\_POINTER and every framework event built on it (WinUI `PointerMoved`, WPF `StylusMove`) receive no pen data. The checkbox can be changed at any time without restarting the driver, but running applications may need a restart because they initialised against the previous state.

Two more driver facts constrain the choice:

- **One Wintab per machine.** Each tablet vendor installs its own `wintab32.dll`, and installing a second vendor's driver overwrites the first. In practice you cannot use two tablet brands at once through Wintab. WM\_POINTER is part of Windows and works with several brands at the same time.
- **Using both paths in one process is unreliable.** With a Wintab context open, some drivers stop delivering WM\_POINTER pen events. With Windows Ink as the active path, a driver may not load `wintab32.dll` or may deliver incomplete Wintab data. This varies by driver and driver version, which is why most applications offer the choice as a single either/or setting.

## How the APIs differ here

### Which API a framework can use

| Your app | Wintab | WM\_POINTER | Framework API | RealTimeStylus |
| --- | --- | --- | --- | --- |
| Raw Win32 / C++ | Yes, with the `Wintab.h` header | Yes, natively | none | Yes, through COM |
| WinForms | Yes, through P/Invoke | Yes, but only through `IMessageFilter` (see [Stage 2](2-delivery.md)) | none | Yes, through COM interop |
| WPF | Yes, through P/Invoke | No (see below) | `StylusPoint` | Yes, through COM interop |
| WinUI 3 | Yes, through P/Invoke | No: messages never reach the HWND | `PointerPoint` | Through COM |
| Avalonia | Yes, through P/Invoke | No (see below) | Avalonia `PointerPoint` | Through COM |
| egui / winit (Rust) | Yes | Yes: winit uses raw Win32 | none | |

Wintab works in every framework because it delivers packets to a window it owns, not to your UI. An older version of these notes said WPF could read WM\_POINTER through `WndProc` or `HwndSource` and Avalonia through platform interop. WinPenKit does not offer WM\_POINTER in either: its `WpfPenApis` and `AvaloniaPenApis` exclude it because the framework consumes pointer input before a window subclass sees it. Treat WM\_POINTER as unavailable in WPF, WinUI and Avalonia unless you have measured otherwise in your own app.

### Two Wintab modes, one context type

Wintab has a system context and what is often called a "digitizer context". The second is not a separate context type. Both are opened from the default system context, `WTI_DEFSYSCTX`. In the system context the driver maps output to screen pixels. In the high-res (digitizer) context the app overwrites the output range (`lcOutOrg`/`lcOutExt`) with the input range (`lcInOrg`/`lcInExt`), so packets arrive in tablet counts, and the app maps them to the desktop itself ([Stage 4](4-device-to-desktop.md)). That keeps the tablet's sub-pixel resolution, but the app has to do the mapping itself. WinPenKit calls the two `InputApi.WintabSystem` ("Wintab") and `InputApi.WintabDigitizer` ("Wintab (high-res)"). Qt opens every Wintab context as a high-res context, so every Qt application that uses Wintab, Krita included, gets tablet-native input. Qt 5.12 and later use WM\_POINTER by default and make Wintab opt-in ([Stage 7](7-output.md#related-projects)).

### Which API to pick for a scenario

| Scenario | Use | Qualification |
| --- | --- | --- |
| Maximum position precision | Wintab high-res context | WM\_POINTER also delivers sub-pixel positions through `ptHimetricLocationRaw` ([Stage 4](4-device-to-desktop.md)), so Wintab is not the only sub-pixel source. |
| Simple pen input in a modern app | The framework's API (`PointerPoint`, `StylusPoint`) | No extra dependency. |
| Cross-framework pen library | Wintab, plus one session per framework for the pointer path | WinPenKit's design. |
| Pen and touch in one app | WM\_POINTER | Each contact has a pointer ID and a pointer type. |
| Barrel (tangential) pressure, airbrush wheel | Wintab `pkTangentPressure` | RTS also exposes it through packet properties. WM\_POINTER, WinUI and WPF do not. WinPenKit's `PenPoint` does not carry it. |
| Pen height above the tablet | Wintab `pkZ` | RTS also exposes Z through packet properties. WinPenKit carries Z from Wintab only (`PenCapabilities.ZHeight`). |

### Opening a Wintab context correctly

These are requirements of real drivers that the Wintab 1.4 specification does not state:

- **Use `WTI_DEFSYSCTX`, not `WTI_DEFCONTEXT`.** The digitizer default context may not deliver packets on some Wacom driver versions. Use the system default as the base for both modes.
- **Set `CXO_SYSTEM`.** Without it the Wacom driver accepts `WTOpenA` and returns a valid handle, but no `WT_PACKET` messages arrive.
- **Read the context back with `WTGetA` after opening.** The driver may change values during `WTOpenA`.
- **Set `lcPktData` to match your `PACKET` struct.** The default context may not include every field your struct expects, and the driver then writes fields at the wrong offsets. Request all of them (`PK_PKTBITS_ALL`, `0x1FFF`).
- **`HCTX` is pointer-sized.** `pkContext` is a `HANDLE`: 8 bytes on x64, 4 on x86. Declaring it as `uint` or `DWORD` shifts every later field by 4 bytes on x64. The values still look like numbers, but Y holds X's value and pressure holds Z's. Use `IntPtr` in C#.

## How WinPenKit handles it

**One enum names every source.** [`InputApi`](https://github.com/TheSevenPens/WinPenKit/blob/main/WinPenKit/InputApi.cs) has seven values: `WintabSystem`, `WintabDigitizer`, `WmPointer`, `WinUiPointer`, `WpfStylus`, `AvaloniaPointer`, `WinFormsPointer`. `InputApiExtensions.IsFrameworkAgnostic()` is true for the first three.

**Discovery asks the driver, not the OS version.** [`PenSessionFactory.GetAvailableApis()`](https://github.com/TheSevenPens/WinPenKit/blob/main/WinPenKit/PenSessionFactory.cs) adds both Wintab values when [`WintabNative.IsAvailable()`](https://github.com/TheSevenPens/WinPenKit/blob/main/WinPenKit/Wintab/WintabNative.cs) succeeds (`WTInfoA(0, 0, NULL)` returns more than zero, and a missing `Wintab32.dll` is caught as `DllNotFoundException`), and adds `WmPointer` when `GetPointerType` exists (Windows 8 and later). WinPenKit's STYLUS.md says the check uses `GetPointerPenInfo`; the code calls `GetPointerType`.

**The framework package answers for a framework app** (ARCHITECTURE.md decision 11). The factory reports what the machine has, not what an app can offer. Each package has its own `GetAvailable()`: [`WpfPenApis`](https://github.com/TheSevenPens/WinPenKit/blob/main/WinPenKit.Wpf/WpfPenApis.cs), [`WinUiPenApis`](https://github.com/TheSevenPens/WinPenKit/blob/main/WinPenKit.WinUI/WinUiPenApis.cs), [`AvaloniaPenApis`](https://github.com/TheSevenPens/WinPenKit/blob/main/WinPenKit.Avalonia/AvaloniaPenApis.cs) and [`WinFormsPenApis`](https://github.com/TheSevenPens/WinPenKit/blob/main/WinPenKit.WinForms/WinFormsPenApis.cs). Each removes `WmPointer`, which is present on the system but cannot reach a framework app, then appends the framework's own API. WPF, WinUI and Avalonia always append theirs. WinForms appends `WinFormsPointer` only when the pointer API exists, because it reads the same WM\_POINTER messages. Before this existed, four samples repeated the same filter in their own code, and an app written against the library would have shown a dropdown entry that never delivers a point.

**Creating a session.** `PenSessionFactory.Create(api)` builds the three framework-agnostic sessions and throws for the others, which need a UI element and are constructed directly (`new WpfStylusSession(element)` and so on; see [Stage 7](7-output.md)). `CreateDefault()` prefers `WintabDigitizer`, then `WintabSystem`, then `WmPointer`.

**Opening the Wintab context.** Both Wintab sessions start from `WintabSessionBase.GetDefaultSystemContext` (`WTInfoA(WTI_DEFSYSCTX)`), add `CXO.SYSTEM | CXO.MESSAGES`, and call `ConfigurePacketData`, which sets `lcPktData = PK.ALL`, `lcPktMode = PK.BUTTONS` (relative button mode, see [Stage 6](6-values.md)), `lcMoveMask = PK.ALL` and both button masks to `0xFFFFFFFF`. After `WTOpenA` they call `WTGetA` and log the context. The `Packet` struct in [`WintabStructs.cs`](https://github.com/TheSevenPens/WinPenKit/blob/main/WinPenKit/Wintab/WintabStructs.cs) declares `pkContext` as `IntPtr`.

- [`WintabSystemSession`](https://github.com/TheSevenPens/WinPenKit/blob/main/WinPenKit/Wintab/WintabSystemSession.cs) keeps the driver's output range and makes `lcOutExtY` negative.
- [`WintabDigitizerSession`](https://github.com/TheSevenPens/WinPenKit/blob/main/WinPenKit/Wintab/WintabDigitizerSession.cs) caches the default context's input and system ranges, then sets `lcOutOrg`/`lcOutExt` to `lcInOrg`/`lcInExt`. If that open fails, `OpenFallback` opens an ordinary screen-pixel context instead. The session still reports `Api == WintabDigitizer`, but `Capabilities` drops `HiRes` and `Conventions.RawUnits` changes from `TabletNative` to `ScreenPixels`. If the fallback also fails, the error message includes the driver's context counts from `WintabDiagnostics.ContextTable()`, reported as numbers only, because a high count does not mean the driver has run out.

**Capabilities say what the session supports.** From [`PenCapabilities`](https://github.com/TheSevenPens/WinPenKit/blob/main/WinPenKit/PenCapabilities.cs) and each session's `Capabilities` property:

| Session | Pressure | Tilt | Twist | ZHeight | Buttons | Eraser | HiRes | GlobalCapture | Proximity |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `WintabSystem` | yes | yes | yes | yes | yes | yes | no | yes | yes |
| `WintabDigitizer` | yes | yes | yes | yes | yes | yes | while the high-res context is open | yes | yes |
| `WmPointer`, `WinFormsPointer` | yes | yes | yes | no | yes | yes | while `GetPointerDeviceRects` succeeds | no | no |
| `WpfStylus`, `WinUiPointer`, `AvaloniaPointer` | yes | yes | yes | no | yes | yes | no | no | no |

The `Twist` flag means the backend reads twist from its API. A pen without a rotation sensor reports 0 on every backend, including Wintab, so the flag does not say that the pen has the sensor.

## Traps

1. **Opening a Wintab context without `CXO_SYSTEM`.** Symptom: `WTOpenA` succeeds and no packets ever arrive. Fix: OR `CXO_SYSTEM` into `lcOptions`.
2. **Basing the context on `WTI_DEFCONTEXT`.** Symptom: no packets on some Wacom driver versions. Fix: start from `WTI_DEFSYSCTX` for both modes.
3. **Declaring `pkContext` as a 4-byte type.** Symptom on x64: plausible numbers in the wrong fields, for example Y holding X and pressure holding Z. Fix: use a pointer-sized type.
4. **Leaving `lcPktData` at the driver default.** Symptom: fields written at wrong offsets. Fix: set it explicitly to the fields your struct declares.
5. **Offering `WmPointer` (the window-subclass session) in a WPF, WinUI, WinForms or Avalonia app.** Symptom: the dropdown entry produces nothing. Fix: build the list from the framework package's `GetAvailable()`.
6. **Assuming framework pen events work when the driver's Windows Ink checkbox is off.** Symptom: no pen data except through Wintab. Fix: offer Wintab as well, and tell users which driver setting each API needs.
7. **Reading Wintab and WM\_POINTER at the same time in one process.** Symptom: one path goes quiet, depending on the driver. Fix: run one session at a time; WinPenKit stops one before starting the next.
8. **Assuming the high-res context opened.** Symptom: whole-pixel positions from a session labelled "Wintab (high-res)". Fix: after `Start`, check `Capabilities.HasFlag(PenCapabilities.HiRes)` or `Conventions.RawUnits`.
9. **Expecting two tablet brands to work through Wintab at once.** Symptom: only the most recently installed vendor's tablet works. Fix: use WM\_POINTER for multi-brand setups.

## Further reading

- [Stage 0: the pipeline at a glance](README.md)
- [Stage 2: Delivery](2-delivery.md), for how each source's packets reach your code
- [Stage 4: Device units to desktop pixels](4-device-to-desktop.md), for the high-res mapping
- [Stage 7: The output contract](7-output.md), for sessions, capabilities and conventions
- [Build a Scribble app](../../build-a-scribble-app/README.md)
- [Thoughts on Wintab vs WM\_POINTER](../../misc/thoughts-on-wintab-vs-wm_pointer.md): an opinion piece. In summary: Wintab is stable and well understood, has wrappers for C#, Rust and Python, and is used by many projects, while published Windows Ink examples mostly cover inking rather than reading raw position, pressure and tilt. It links Wacom's [Wintab FAQ](https://developer-support.wacom.com/hc/en-us/articles/12844524637975-Wintab).
- [How Krita and Qt handle pen input](../../misc/krita-and-qt/README.md)
- WinPenKit: [STYLUS.md](https://github.com/TheSevenPens/WinPenKit/blob/main/Docs/STYLUS.md), [ARCHITECTURE.md](https://github.com/TheSevenPens/WinPenKit/blob/main/Docs/ARCHITECTURE.md)
