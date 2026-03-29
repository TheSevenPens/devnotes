# Per-Monitor V2 DPI Awareness

## Per-Monitor V2 DPI Awareness

The term "Per-Monitor V2" is central to understanding coordinate handling in pen input applications on Windows. Here's what it means and why it matters.

### The DPI awareness spectrum

To learn what "Per-Monitor V2" means and how it fits into the full DPI awareness model, read Microsoft's [High DPI Desktop Application Development on Windows](https://learn.microsoft.com/en-us/windows/win32/hidpi/high-dpi-desktop-application-development-on-windows). The summary below covers what's relevant to pen input.

Windows applications declare how they handle high-DPI displays. The level affects what coordinates Win32 APIs return:

| DPI Awareness Level  | Introduced             | What happens                                                                                                                                                         |
| -------------------- | ---------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **DPI Unaware**      | (default before Vista) | Windows lies to the app — all APIs return values as if the display is 96 DPI. Windows bitmap-scales the app's output to the actual DPI, causing blurriness.          |
| **System DPI Aware** | Windows Vista          | The app knows the primary monitor's DPI at startup. Renders crisply on the primary monitor but is bitmap-scaled on other monitors with different DPIs.               |
| **Per-Monitor V1**   | Windows 8.1            | The app receives `WM_DPICHANGED` when moved between monitors and can re-render. But many Win32 APIs (dialog sizing, non-client area) still use the wrong DPI.        |
| **Per-Monitor V2**   | Windows 10 1703        | The full solution. All Win32 APIs respect the current monitor's DPI. Non-client area (title bar, scrollbars) scales automatically. Child window DPI works correctly. |

### What Per-Monitor V2 means for pen input

When your process is Per-Monitor V2 aware:

* **`ClientToScreen` / `ScreenToClient`** return **physical screen pixels** — the real hardware pixel positions
* **`GetDpiForMonitor`** returns the **real DPI** (e.g., 216 for 225% scaling)
* **Wintab `pkX/pkY`** are also in **physical screen pixels** — Wintab always bypasses DPI virtualization

This means Wintab coordinates and Win32 coordinates are in the same space — you can subtract them directly. If the app were DPI Unaware, `ClientToScreen` would return virtualized (scaled-down) values while Wintab still returns physical pixels, causing a coordinate mismatch that grows with distance from the screen origin.

### How each framework sets DPI awareness

| Framework            | Default DPI Awareness | How it's set                                                           |
| -------------------- | --------------------- | ---------------------------------------------------------------------- |
| **.NET 10 WinForms** | Per-Monitor V2        | Automatic via `<HighDpiMode>PerMonitorV2</HighDpiMode>` in the project |
| **WinUI 3**          | Per-Monitor V2        | Set by the Windows App SDK at startup                                  |
| **WPF (.NET 10)**    | Per-Monitor V2        | Automatic in .NET 10; earlier versions need app manifest               |
| **Raw Win32**        | DPI Unaware           | Must declare in app manifest or call `SetProcessDpiAwarenessContext`   |

### `SetThreadDpiAwarenessContext` — controlling the coordinate space

Even in a Per-Monitor V2 process, individual threads can explicitly set their DPI awareness context. This controls which coordinate space Win32 APIs operate in. WinUI 3 apps can use this to ensure `ClientToScreen` and `GetDpiForMonitor` return physical pixel values:

```csharp
var old = SetThreadDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2);
try
{
    ClientToScreen(hwnd, ref clientOrigin);  // guaranteed physical pixels
    GetDpiForMonitor(hMon, 0, out dpiX, out dpiY);  // guaranteed real DPI
}
finally
{
    SetThreadDpiAwarenessContext(old);  // restore previous context
}
```

The context handle values:

| Handle                                       | Value | Meaning                                         |
| -------------------------------------------- | ----- | ----------------------------------------------- |
| `DPI_AWARENESS_CONTEXT_UNAWARE`              | -1    | DPI unaware — APIs return virtualized values    |
| `DPI_AWARENESS_CONTEXT_SYSTEM_AWARE`         | -2    | System DPI aware                                |
| `DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE`    | -3    | Per-Monitor V1                                  |
| `DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2` | -4    | Per-Monitor V2 — recommended for pen input apps |
| `DPI_AWARENESS_CONTEXT_UNAWARE_GDISCALED`    | -5    | DPI unaware with improved GDI scaling           |

### Why WinForms doesn't need this

In WinForms (.NET 10), the process is already Per-Monitor V2 from startup. `Control.PointToClient()` internally calls `ScreenToClient` which returns physical-pixel-based logical coordinates automatically. No thread context switching is needed — `PointToClient` handles everything in one call.

In WinUI 3, the situation is more complex because the XAML layout engine uses DIPs (not physical pixels), and the thread's DPI context may vary. The explicit `SetThreadDpiAwarenessContext` call ensures consistency between `ClientToScreen` (physical pixels) and Wintab `pkX/pkY` (also physical pixels).
