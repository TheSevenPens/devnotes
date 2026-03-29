# Framework Compatibility

## Framework Compatibility

| API                | WinForms                                                                                                                              | WPF                                | WinUI 3                            | Avalonia                           | Raw Win32    |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------- | ---------------------------------- | ---------------------------------- | ------------ |
| Wintab             | Yes (via P/Invoke or .NET wrapper)                                                                                                    | Yes (via P/Invoke or .NET wrapper) | Yes (via P/Invoke or .NET wrapper) | Yes (via P/Invoke or .NET wrapper) | Yes (native) |
| WM\_POINTER        | Via IMessageFilter only (NativeWindow.AssignHandle crashes on Form HWNDs; subclassing conflicts with WinForms' internal NativeWindow) | Yes (via WndProc / HwndSource)     | Not directly (WinUI wraps it)      | Possible (via platform interop)    | Yes (native) |
| WinUI PointerPoint | No                                                                                                                                    | No                                 | Yes (native)                       | No                                 | No           |
| WPF StylusPoint    | No                                                                                                                                    | Yes (native)                       | No                                 | No                                 | No           |
| RealTimeStylus     | Yes (COM interop)                                                                                                                     | Yes (COM interop)                  | Possible (COM)                     | Possible (COM)                     | Yes (COM)    |

##
