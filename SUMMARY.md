# Table of contents

* [Developer Notes](README.md)

## Pen Input on Windows

* [Overview](pen-input-on-windows/pen-input/README.md)
  * [Challenges developing pen-aware applications](pen-input-on-windows/pen-input/challenges-developing-pen-aware-applications.md)
* [Windows Pen API Landscape](pen-input-on-windows/windows-pen-api-landscape.md "API Landscape")
* [Pen APIs compared](pen-input-on-windows/pen-apis-compared/README.md)
  * [Z position](pen-input-on-windows/pen-apis-compared/z-position.md)
  * [Pressure Data](pen-input-on-windows/pen-apis-compared/pressure-data.md)
  * [Coordinate Precision](pen-input-on-windows/pen-apis-compared/coordinate-precision.md)
  * [Pen buttons](pen-input-on-windows/pen-apis-compared/pen-buttons.md)
  * [Barrel pressure](pen-input-on-windows/pen-apis-compared/barrel-pressure.md)
  * [Eraser detection](pen-input-on-windows/pen-apis-compared/eraser-detection.md)
  * [Framework Compatibility](pen-input-on-windows/pen-apis-compared/framework-compatibility.md)
  * [Hover / Proximity Behavior](pen-input-on-windows/pen-apis-compared/hover-proximity-behavior.md)
  * [Pen Orientation Data](pen-input-on-windows/pen-apis-compared/pen-orientation-data.md)

***

* [Implementation notes](implementation-notes/README.md)
  * [Latency Implications](implementation-notes/latency-implications.md)
  * [Wintab vs Windows Ink Driver Conflict](implementation-notes/wintab-vs-windows-ink-driver-conflict.md)
  * [Known Quirks and Gotchas](implementation-notes/known-quirks-and-gotchas.md)
  * [DPI and Pen Coordinates](implementation-notes/dpi-and-pen-coordinates.md)
  * [Per-Monitor V2 DPI Awareness](implementation-notes/per-monitor-v2-dpi-awareness.md)
  * [WM\_POINTER Event Coalescing](implementation-notes/wm_pointer-event-coalescing.md)
  * [WM\_POINTER Coalescing](implementation-notes/wm-pointer-coalescing.md)
  * [WM\_POINTER Input Routing](implementation-notes/framework-pen-input-routing.md)
  * [Wintab Gotchas](implementation-notes/wintab-gotchas.md)
* [APIs by scenario](apis-by-scenario.md)
* [Unifying Pen APIs with PenSession](unifying-pen-apis-with-pensession/README.md "PenSession")
  * [PenSession Tilt handling](unifying-pen-apis-with-pensession/pensession-tilt-handling.md "Tilt handling")
  * [Framework input routing](unifying-pen-apis-with-pensession/framework-input-routing.md)

## Rendering

* [Rendering for Pen Apps](rendering/rendering-for-pen-apps.md)

## MISC

* [References](misc/references.md)
