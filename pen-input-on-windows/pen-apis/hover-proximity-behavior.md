# Hover / Proximity Behavior

## Hover / Proximity Behavior

APIs differ in how they report the pen being near the tablet but not touching the surface. This matters for cursor preview, brush ghosting, and eraser detection.

| API                | Proximity detection                              | Hover data                                                        | Notes                                                                                                                                                                                 |
| ------------------ | ------------------------------------------------ | ----------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Wintab             | `WT_PROXIMITY` message; `pkStatus` proximity bit | Full pen data during hover (position, tilt, buttons, cursor type) | Eraser detection happens on hover (cursor type changes before contact). Proximity bit in `pkStatus` is set when pen _leaves_, not when it enters. Packets stop when pen leaves range. |
| WM\_POINTER        | `IS_POINTER_INRANGE_WPARAM` flag                 | `WM_POINTERUPDATE` with `INRANGE` but not `INCONTACT`             | Pen data available during hover. `WM_POINTERLEAVE` when pen exits range.                                                                                                              |
| WinUI PointerPoint | `PointerEntered` / `PointerExited` events        | `IsInContact` property distinguishes hover from press             | Natural XAML event model. Hover data includes pressure=0, tilt, position.                                                                                                             |
| WPF StylusPoint    | `StylusInAirMove` event                          | Position and tilt during in-air movement                          | `StylusDevice.InAir` property. Less data than contact events.                                                                                                                         |
| RealTimeStylus     | `IStylusPlugin::InAirPackets`                    | Position and tilt during hover                                    | Separate callback from `Packets` (contact).                                                                                                                                           |

**Key differences:**

* Wintab provides full pen data (including cursor type for eraser detection) during hover, but proximity tracking is quirky — the `pkStatus` proximity bit signals _leaving_, and packets simply stop when the pen is out of range. Time-based timeout is more reliable than flag-based detection.
* WM\_POINTER has cleaner hover semantics (`INRANGE` + `INCONTACT` flags) but less pen data (no Z height, no barrel pressure).
* Eraser detection timing differs: Wintab reports cursor type change on hover (before contact), while WM\_POINTER reports eraser state in pen flags per-event.
