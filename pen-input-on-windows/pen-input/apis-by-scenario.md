# APIs by scenario

| Scenario                             | Recommended API                       | Why                                          |
| ------------------------------------ | ------------------------------------- | -------------------------------------------- |
| Maximum tablet precision for drawing | Wintab using Digitizer context        | Only API that preserves full tablet LPI      |
| Simple pen input, modern app         | WinUI PointerPoint or WPF StylusPoint | Built into the framework, no dependencies    |
| Cross-framework pen input library    | Wintab (via .NET wrapper)             | Works in all .NET UI frameworks via P/Invoke |
| Touch + pen discrimination           | WM\_POINTER                           | Designed for multi-input-type scenarios      |
| Airbrush / barrel pressure           | Wintab                                | Only API exposing tangential pressure        |
| Pen height above tablet              | Wintab                                | Only API exposing Z axis                     |

