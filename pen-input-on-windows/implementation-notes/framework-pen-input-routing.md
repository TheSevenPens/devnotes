# Framework-Specific Pen Input Routing on Windows

Each UI framework intercepts pen input through its own path. Understanding this is critical when building a pen input abstraction or choosing how to receive pen data.

## The Core Problem

`WM_POINTER` messages are the modern Windows pen input path. They go to the window under the pointer. In a raw Win32 app, you can subclass the HWND and intercept them directly. But UI frameworks (WinUI 3, WPF, WinForms, Avalonia) have their own input stacks that process these messages before your code sees them.

## How Each Framework Handles Pen Input

| Framework | Input path | WM_POINTER subclassing works? | Native pen events |
|---|---|---|---|
| **Raw Win32** | Messages reach the HWND directly | Yes — `SetWindowSubclass` works | N/A — use WM_POINTER directly |
| **WinUI 3** | Routes through composition InputSite | No — messages never reach the HWND | `PointerMoved`/`PointerPressed` XAML events |
| **WPF** | Routes through Wisp/RealTimeStylus stack | No — pen input consumed before HWND | `StylusMove`/`StylusDown` events |
| **WinForms** | Processes WM_POINTER in Form's WndProc | Crashes with `NativeWindow.AssignHandle` | `IMessageFilter` intercepts messages before dispatch |
| **Avalonia** | Routes through its own pointer system | Not tested — likely consumed | `PointerMoved`/`PointerPressed` events |
| **egui (Rust)** | Uses winit, which uses raw Win32 | Yes — same as raw Win32 | N/A |

## Wintab Works Everywhere

Wintab sessions create their own hidden Win32 window on a dedicated background thread. The Wacom driver delivers `WT_PACKET` messages to that window regardless of what UI framework the app uses. The session is completely decoupled from the app's windowing model.

This is why Wintab is the universal fallback — it works in every framework without any framework-specific code.

**Important:** The hidden window must be a regular top-level window, not `HWND_MESSAGE`. The Wacom driver doesn't deliver `WT_PACKET` to message-only windows.

## WinUI 3 Details

WinUI 3 (Windows App SDK) routes pen input through its own composition layer (InputSite). `WM_POINTER` messages are not delivered to the top-level HWND. Even if you subclass the HWND, no pointer messages arrive.

To get pen data in WinUI 3:
- Use XAML `PointerMoved`/`PointerPressed` events on a UIElement
- `PointerPoint.Properties` provides pressure, tilt, eraser, barrel button

Coordinates are in DIPs (device-independent pixels), not physical screen pixels. You need the window's `ClientToScreen` offset and DPI scale factor to convert to desktop coordinates.

## WPF Details

WPF routes pen input through its Wisp/RealTimeStylus COM stack (in .NET 10, this is the default for stylus). `WM_POINTER` messages may be consumed before reaching the window proc.

To get pen data in WPF:
- Use `StylusMove`/`StylusDown`/`StylusUp` events on a UIElement
- `StylusEventArgs.GetStylusPoints(element)` provides pressure, tilt
- `StylusPoint.PressureFactor` is pre-normalized (0.0–1.0)
- Tilt via `GetPropertyValue(StylusPointProperties.XTiltOrientation)` — hundredths of degree

Check `e.StylusDevice.TabletDevice.Type == TabletDeviceType.Stylus` to filter pen vs touch.

## WinForms Details

WinForms processes WM_POINTER messages in its own message loop. Using `NativeWindow.AssignHandle` on a Form's HWND causes a crash (exit code -1) because WinForms internally creates its own `NativeWindow` for each Form, and a second `AssignHandle` on the same HWND conflicts with the internal window procedure ownership.

**The solution: `IMessageFilter`.** This is a WinForms API that intercepts ALL messages at the application message pump level, before they reach any window procedure:

```csharp
public class PointerFilter : IMessageFilter
{
    public bool PreFilterMessage(ref Message m)
    {
        if (m.Msg == 0x0245) // WM_POINTERUPDATE
        {
            uint pointerId = (uint)((long)m.WParam & 0xFFFF);
            // Call GetPointerPenInfo, process pen data...
        }
        return false; // Let WinForms also process the message.
    }
}

Application.AddMessageFilter(new PointerFilter());
```

## Avalonia Details

Avalonia routes pointer input through its own event system. On Windows, Avalonia uses the Win32 backend, but pointer events are processed internally.

To get pen data in Avalonia:
- Use `PointerMoved`/`PointerPressed` events on a Control
- `PointerEventArgs.GetCurrentPoint(element)` provides pen data
- `PointerPoint.Properties` has `Pressure`, `XTilt`, `YTilt`, `Twist`
- Check `point.Pointer.Type == PointerType.Pen` to filter pen vs mouse

Convert to screen coordinates via `TopLevel.PointToScreen()`.

## Key Takeaway

If you're building a pen input library that works across frameworks:
- **Wintab** is the universal backend — works everywhere via its own hidden window
- **WM_POINTER** only works in raw Win32 apps (and egui/winit)
- **Each framework needs its own session** using framework-native events for the non-Wintab path
