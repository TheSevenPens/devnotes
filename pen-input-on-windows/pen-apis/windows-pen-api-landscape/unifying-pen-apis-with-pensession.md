# Unifying Pen APIs with PenSession

The `PenSession` library provides a unified `IPenSession` interface across four backends, with runtime switching via a dropdown — no restart required. See [FUTURES\_UNIFIED\_SESSION.md](../../../pen-input/apis/FUTURES_UNIFIED_SESSION.md) for the full design.

### Framework specificity

Not all APIs work in all app types. The key factor is how input reaches the session:

| API                             | Input mechanism                                   | Framework compatibility                                                                                                              |
| ------------------------------- | ------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| **Wintab (System & Digitizer)** | Own hidden window on background thread            | **Any app** — Win32, WinUI 3, WPF, WinForms                                                                                          |
| **WM\_POINTER**                 | Subclasses the app's HWND                         | **Raw Win32 only** — WinUI 3, WPF, and WinForms intercept pen input before it reaches the HWND or conflict with HWND ownership       |
| **WinUI PointerPoint**          | XAML `PointerMoved` events                        | **WinUI 3 only** — requires XAML UIElement                                                                                           |
| **WPF Stylus**                  | WPF `StylusMove`/`StylusDown` events              | **WPF only** — uses WPF's Wisp/RTS input stack                                                                                       |
| **Avalonia Pointer**            | Avalonia `PointerMoved`/`PointerPressed` events   | **Avalonia only** — uses Avalonia's pointer system                                                                                   |
| **WinForms Pointer**            | `IMessageFilter` intercepts `WM_POINTER` messages | **WinForms only** — `NativeWindow.AssignHandle` on Form HWNDs crashes; `IMessageFilter` intercepts at the message pump level instead |

This is why the library is split into packages:

* `PenSession.dll` — framework-agnostic (Wintab + WmPointer)
* `PenSession.WinUI.dll` — WinUI 3 extension (WinUI PointerPoint)
* `PenSession.Wpf.dll` — WPF extension (WPF Stylus)
* `PenSession.Avalonia.dll` — Avalonia extension (Avalonia Pointer)
* `PenSession.WinForms.dll` — WinForms extension (WinForms Pointer via IMessageFilter)

### What's covered in the design doc

* The `IPenSession` interface and `PenPoint` normalization contract
* Polling vs event-driven delivery models (polling everywhere — validated)
* Bidirectional tilt conversion (Azimuth/Altitude ↔ TiltX/TiltY, all in tenths of degree)
* Session factory with API discovery
* Framework-specific vs framework-agnostic session types
* Complete WinUI 3 integration guide
* Comparison with Qt's `QTabletEvent` and Krita's API switching
