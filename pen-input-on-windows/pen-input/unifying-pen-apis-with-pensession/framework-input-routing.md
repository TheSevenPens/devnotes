# Cross-framework support

### Overview

WinPenKit library is split into packages. Some are framework specific because of unique ways pen input is routed in those frameworks.

* `PenSession.dll` — framework-agnostic (Wintab + WmPointer)
* `PenSession.WinUI.dll` — WinUI 3 extension (WinUI PointerPoint)
* `PenSession.Wpf.dll` — WPF extension (WPF Stylus)
* `PenSession.Avalonia.dll` — Avalonia extension (Avalonia Pointer)
* `PenSession.WinForms.dll` — WinForms extension (WinForms Pointer via IMessageFilter)

### Framework specificity

Not all APIs work in all app types. The key factor is how input reaches the session. This is why the WinPenKit library is split into packages:

| API                             | Input mechanism                                   | Framework compatibility                                                                                                              |
| ------------------------------- | ------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| **Wintab (System & Digitizer)** | Own hidden window on background thread            | **Any app** — Win32, WinUI 3, WPF, WinForms                                                                                          |
| **WM\_POINTER**                 | Subclasses the app's HWND                         | **Raw Win32 only** — WinUI 3, WPF, and WinForms intercept pen input before it reaches the HWND or conflict with HWND ownership       |
| **WinUI PointerPoint**          | XAML `PointerMoved` events                        | **WinUI 3 only** — requires XAML UIElement                                                                                           |
| **WPF Stylus**                  | WPF `StylusMove`/`StylusDown` events              | **WPF only** — uses WPF's Wisp/RTS input stack                                                                                       |
| **Avalonia Pointer**            | Avalonia `PointerMoved`/`PointerPressed` events   | **Avalonia only** — uses Avalonia's pointer system                                                                                   |
| **WinForms Pointer**            | `IMessageFilter` intercepts `WM_POINTER` messages | **WinForms only** — `NativeWindow.AssignHandle` on Form HWNDs crashes; `IMessageFilter` intercepts at the message pump level instead |
