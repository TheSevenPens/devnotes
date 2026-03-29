# Framework Compatibility



**Wintab**&#x20;

* WinForms, WPF, WinUI3, Avalonia -> Works well! via P/Invoke or .NET wrapper for WinTab.
* Win32 - Works well. Just include the Wintab.h header file

**WM\_POINTER**

* &#x20;WinForms - Works but requires some effort. Use via IMessageFilter only (NativeWindow.AssignHandle crashes on Form HWNDs; subclassing conflicts with WinForms' internal NativeWindow)
* WPF - Yes (via WndProc / HwndSource)
* WinUI 3 - Not directly (WinUI wraps it)
* Avalonia - Possible (via platform interop)
* Win32 - Yes (native)

**WinUI PointerPoint**

* WinForms - no access. Cannot use PointerPoint.
* WPF - no access. Cannot use PointerPoint.
* WinUI 3 - Yes - native support for PointerPoint
* Avalonia - no access. Cannot use PointerPoint
* Raw Win32 - no access. Cannot use PointerPoint

**WPF StylusPoint**

* WinForms - no access. Cannot use StylusPoint.
* WPF - Yes (native)
* WINUI 3 - No access. Cannot use StylusPoint.
* Avalonia - No access. Cannot use StylusPoint.
* Raw Win32 - No access. Cannot use StylusPoint.

**RealTimeStylus**

* WinForms - YES (via COM interop)
* WPF - YES (via COM interop)
* WinUI 3 - Possible (COM)
* Avalonia - Possible (COM)
* Raw Win32 - Possible (COM)
