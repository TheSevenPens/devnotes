# Additional Pen Data

### Additional Pen Data

| API                | Barrel pressure      | Multiple pen buttons                    |
| ------------------ | -------------------- | --------------------------------------- |
| Wintab             | `pkTangentPressure`  | `pkButtons` bitmask                     |
| WM\_POINTER        | Not available        | Button flags in `POINTER_INFO`          |
| WinUI PointerPoint | Not available        | `Properties.IsBarrelButtonPressed` etc. |
| WPF StylusPoint    | Not available        | Via StylusButton collection             |
| RealTimeStylus     | Via PACKET\_PROPERTY | Via PACKET\_PROPERTY                    |

##
