# Additional Pen Data

### Additional Pen Data

| API                | Z (height)           | Barrel pressure      | Eraser detection                    | Multiple pen buttons                    |
| ------------------ | -------------------- | -------------------- | ----------------------------------- | --------------------------------------- |
| Wintab             | `pkZ`                | `pkTangentPressure`  | Via cursor type (`pkCursor`)        | `pkButtons` bitmask                     |
| WM\_POINTER        | Not available        | Not available        | `IS_POINTER_INRANGE_WPARAM` + flags | Button flags in `POINTER_INFO`          |
| WinUI PointerPoint | Not directly         | Not available        | `Properties.IsEraser`               | `Properties.IsBarrelButtonPressed` etc. |
| WPF StylusPoint    | Not directly         | Not available        | `StylusDevice.Inverted`             | Via StylusButton collection             |
| RealTimeStylus     | Via PACKET\_PROPERTY | Via PACKET\_PROPERTY | Via cursor type                     | Via PACKET\_PROPERTY                    |

##
