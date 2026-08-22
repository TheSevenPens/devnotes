# Cross-framework support

WinPenKit library is split into spearate libraries. Some are framework specific libraries because of unique ways pen input is routed in those frameworks.

* `PenSession.dll` — framework-agnostic (Wintab + WmPointer)
* `PenSession.WinUI.dll` — WinUI 3 extension (WinUI PointerPoint)
* `PenSession.Wpf.dll` — WPF extension (WPF Stylus)
* `PenSession.Avalonia.dll` — Avalonia extension (Avalonia Pointer)
* `PenSession.WinForms.dll` — WinForms extension (WinForms Pointer via IMessageFilter)

For example, if you want to use WinPenKit with a WinForm application, you'll need to use both `PenSession.dll` and `PenSession.WinForms.dll` .
