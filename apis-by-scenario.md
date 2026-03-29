# APIs by scenario

Depending on what you are trying to accomplish and which UX framework different APIs may be the right choice for you.

| Scenario                             | Recommended API                       | Why                                          |
| ------------------------------------ | ------------------------------------- | -------------------------------------------- |
| Maximum tablet precision for drawing | Wintab Digitizer Hi-Res               | Only API that preserves full tablet LPI      |
| Simple pen input, modern app         | WinUI PointerPoint or WPF StylusPoint | Built into the framework, no dependencies    |
| Cross-framework pen input library    | Wintab (via .NET wrapper)             | Works in all .NET UI frameworks via P/Invoke |
| Touch + pen discrimination           | WM\_POINTER                           | Designed for multi-input-type scenarios      |
| Airbrush / barrel pressure           | Wintab                                | Only API exposing tangential pressure        |
| Pen height above tablet              | Wintab                                | Only API exposing Z axis                     |
| Full tilt as azimuth/altitude        | Wintab or RealTimeStylus              | Other APIs only provide X/Y tilt             |

