# Eraser detection

| API                | Eraser detection                    |
| ------------------ | ----------------------------------- |
| Wintab             | Via cursor type (`pkCursor`)        |
| WM\_POINTER        | `IS_POINTER_INRANGE_WPARAM` + flags |
| WinUI PointerPoint | `Properties.IsEraser`               |
| WPF StylusPoint    | `StylusDevice.Inverted`             |
| RealTimeStylus     | Via cursor type                     |
