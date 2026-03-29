# DPI and Pen Coordinates

## Overview

Pen coordinate handling on high-DPI Windows displays is one of the most common sources of bugs in drawing applications. Depending on how your aware your app is of DPI, the problem varies

| DPI Awareness         | What Win32 APIs return                 | What happens                                                 |
| --------------------- | -------------------------------------- | ------------------------------------------------------------ |
| DPI Unaware (default) | Virtualized coordinates (as if 96 DPI) | Wintab and Win32 coords don't match — pen drifts from stroke |
| System DPI Aware      | Primary monitor's DPI                  | Works on primary monitor, broken on others                   |
| Per-Monitor V2        | Physical pixels (real positions)       | Matches Wintab — correct on all monitors                     |

## Doing it the right way: Per-Monitor V2

Your app must be **Per-Monitor V2 DPI aware**. This ensures `ClientToScreen`, `ScreenToClient`, `PointFromScreen`, and similar APIs operate in the same coordinate space as Wintab.

More here: [Per-Monitor V2 DPI Awareness](per-monitor-v2-dpi-awareness.md)

### Native C++ apps

```cpp
// Call before creating any windows:
SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2);
```

### WinUI 3 unpackaged apps

Packaged WinUI 3 apps (MSIX) get Per-Monitor V2 automatically. Unpackaged apps (`WindowsPackageType=None`) need it in `app.manifest`:

```xml
<application xmlns="urn:schemas-microsoft-com:asm.v3">
  <windowsSettings>
    <dpiAwareness xmlns="http://schemas.microsoft.com/SMI/2016/WindowsSettings">PerMonitorV2</dpiAwareness>
    <dpiAware xmlns="http://schemas.microsoft.com/SMI/2005/WindowsSettings">true/pm</dpiAware>
  </windowsSettings>
</application>
```

Without this, the entire UI renders blurry (bitmap-scaled) and pen coordinates drift.

### .NET WinForms

.NET 10 WinForms sets Per-Monitor V2 automatically via `<ApplicationHighDpiMode>PerMonitorV2</ApplicationHighDpiMode>`. `Control.PointToClient()` handles DPI conversion automatically.

### WPF

.NET 10 WPF is Per-Monitor V2 by default. `PointFromScreen` handles DPI conversion.

### WinUI 3 Coordinate Conversion

WinUI 3 uses DIPs (device-independent pixels) for all XAML layout. Wintab uses physical screen pixels. To convert:

```
canvasDipX = (desktopPhysicalX - clientOriginPhysicalX) × (96 / DPI) - canvasPositionDipX
```

Important: `ClientToScreen` must be called from a Per-Monitor V2 thread context. In WinUI 3, use `SetThreadDpiAwarenessContext`:

```csharp
var old = SetThreadDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2);
try
{
    ClientToScreen(hwnd, ref clientOrigin);  // guaranteed physical pixels
    GetDpiForMonitor(hMon, 0, out dpiX, out dpiY);  // guaranteed real DPI
}
finally
{
    SetThreadDpiAwarenessContext(old);
}
```

### Common WinUI 3 DPI Symptoms

| Symptom                                                    | Likely cause                                                            |
| ---------------------------------------------------------- | ----------------------------------------------------------------------- |
| Pen position drifts from stroke as you move right/down     | App is not DPI-aware — `ScreenToClient` returns virtualized coordinates |
| UI is blurry                                               | WinUI 3 unpackaged app missing DPI manifest                             |
| Coordinates correct on primary monitor, wrong on secondary | System DPI Aware instead of Per-Monitor V2                              |
| WinUI 3 coordinates don't match Wintab                     | `ClientToScreen` called without Per-Monitor V2 thread context           |

