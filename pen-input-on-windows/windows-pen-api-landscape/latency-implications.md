# Latency Implications

## Latency Implications

The threading model affects pen-to-pixel latency:

| API                | Delivery thread          | Typical frequency   | Latency characteristics                                                                                     |
| ------------------ | ------------------------ | ------------------- | ----------------------------------------------------------------------------------------------------------- |
| Wintab             | Background thread        | 200+ Hz             | Lowest latency to capture. App polls on render timer (adds up to one frame). Total: \~4-20ms.               |
| WM\_POINTER        | UI thread (message pump) | \~120-240 Hz        | Tied to message pump processing. If UI thread is busy (rendering, layout), messages queue. Total: \~4-30ms. |
| WinUI PointerPoint | UI thread (XAML events)  | Same as WM\_POINTER | Additional XAML event dispatch overhead on top of WM\_POINTER.                                              |
| RealTimeStylus     | Configurable             | Up to 240+ Hz       | Sync plugins run on pen thread (lowest possible latency). Async plugins run on UI thread.                   |

**For paint apps:** The latency difference between Wintab's background thread and WM\_POINTER's UI thread is rarely perceptible (both are well under one frame at 60fps). The bigger practical concern is that WM\_POINTER events can be delayed if the UI thread is doing heavy work (complex layout, large canvas redraw), while Wintab's background thread captures independently. This is why production paint apps (Photoshop, Krita, Clip Studio) historically prefer Wintab — not for raw latency but for capture reliability under load.
