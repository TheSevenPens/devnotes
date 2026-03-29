# References

### Wintab

* [Wacom Wintab Basics](https://developer-docs.wacom.com/docs/icbt/windows/wintab/wintab-basics/) — context types, coordinate mapping, packet fields
* [Wacom Wintab Reference](https://developer-docs.wacom.com/docs/icbt/windows/wintab/wintab-reference/) — full API reference (WTOpen, WTInfo, WTGet, context fields, packet structures)
* [Wintab Specification 1.4](https://developer-docs.wacom.com/docs/icbt/windows/wintab/wintab-spec/) — the original specification document defining context mapping, axis scaling, and coordinate spaces

### WM\_POINTER

* [Pointer Input Messages and Notifications](https://learn.microsoft.com/en-us/windows/win32/inputmsg/messages-and-notifications-portal) — WM\_POINTER message family
* [POINTER\_PEN\_INFO structure](https://learn.microsoft.com/en-us/windows/win32/api/winuser/ns-winuser-pointer_pen_info) — pen-specific fields (pressure, tilt, rotation)
* [Pointer Input API overview](https://learn.microsoft.com/en-us/windows/win32/inputmsg/about-the-pointer-input-stack) — architecture, pointer types, DPI behavior

### Windows Ink / WinUI 3

* [PointerPoint class](https://learn.microsoft.com/en-us/windows/windows-app-sdk/api/winrt/microsoft.ui.input.pointerpoint) — WinUI 3 pointer input
* [PointerPointProperties](https://learn.microsoft.com/en-us/windows/windows-app-sdk/api/winrt/microsoft.ui.input.pointerpointproperties) — pressure, tilt, eraser, buttons
* [InkCanvas (WinUI 3)](https://learn.microsoft.com/en-us/windows/windows-app-sdk/api/winrt/microsoft.ui.xaml.controls.inkcanvas) — built-in ink rendering control

### Windows Ink / WPF

* [StylusPoint class](https://learn.microsoft.com/en-us/dotnet/api/system.windows.input.styluspoint) — WPF stylus data
* [InkCanvas (WPF)](https://learn.microsoft.com/en-us/dotnet/api/system.windows.controls.inkcanvas) — WPF ink rendering control
* [Stylus Input overview](https://learn.microsoft.com/en-us/dotnet/desktop/wpf/advanced/the-ink-object-model-windows-forms-and-com-versus-wpf) — WPF vs WinForms ink models

### RealTimeStylus

* [RealTimeStylus overview](https://learn.microsoft.com/en-us/windows/win32/tablet/realtimestylus-reference) — COM API for low-latency pen input
* [StylusInput API](https://learn.microsoft.com/en-us/windows/win32/tablet/stylusinput-api-reference) — plugin model, sync vs async

### Windows DPI and Multi-Monitor

* [GetSystemMetrics (virtual screen)](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-getsystemmetrics) — SM\_XVIRTUALSCREEN, SM\_CXVIRTUALSCREEN for multi-monitor coordinate spaces
* [SetThreadDpiAwarenessContext](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setthreaddpiawarenesscontext) — per-thread DPI awareness switching
* [GetDpiForMonitor](https://learn.microsoft.com/en-us/windows/win32/api/shellscalingapi/nf-shellscalingapi-getdpiformonitor) — real monitor DPI query
* [High DPI Desktop Application Development](https://learn.microsoft.com/en-us/windows/win32/hidpi/high-dpi-desktop-application-development-on-windows) — comprehensive DPI awareness guide
