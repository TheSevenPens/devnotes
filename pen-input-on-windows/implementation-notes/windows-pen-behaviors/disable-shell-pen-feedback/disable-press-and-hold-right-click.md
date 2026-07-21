---
description: Prevent the Windows press-and-hold gesture for a single window.
---

# Disable press-and-hold right-click

## Disable press-and-hold right-click

A stationary pen or touch contact can trigger Windows press-and-hold. After about one second, Windows shows a ring. Continuing the hold sends a right-click.

This is a shell gesture. It can run even when the app reads input elsewhere. Windows still sees ordinary pointer input for the window.

Answer `WM_TABLET_QUERYSYSTEMGESTURESTATUS` with `TABLET_DISABLE_PRESSANDHOLD`. This suppresses the ring and right-click for that window.

{% hint style="warning" %}
Use this only where holding is your interaction. Keep press-and-hold elsewhere for normal pen right-click.
{% endhint %}

### Gesture-status flags

```
WM_TABLET_QUERYSYSTEMGESTURESTATUS = 0x02CC

// Return an OR-ed bitmask of gestures to disable.
TABLET_DISABLE_PRESSANDHOLD        0x00000001
TABLET_DISABLE_PENTAPFEEDBACK      0x00000008
TABLET_DISABLE_PENBARRELFEEDBACK   0x00000010
TABLET_DISABLE_TOUCHUIFORCEON      0x00000100
TABLET_DISABLE_TOUCHUIFORCEOFF     0x00000200
TABLET_DISABLE_TOUCHSWITCH         0x00008000
TABLET_DISABLE_FLICKS              0x00010000
TABLET_DISABLE_SMOOTHSCROLLING     0x00080000
TABLET_DISABLE_FLICKFALLBACKKEYS   0x00100000
TABLET_ENABLE_MULTITOUCHDATA       0x01000000 // Enables raw multitouch data.
```

Returning `0` enables all gestures. Install the hook when the window is created.

### Raw Win32

```c
case WM_TABLET_QUERYSYSTEMGESTURESTATUS:
    return TABLET_DISABLE_PRESSANDHOLD;
```

### WinForms

```csharp
protected override void WndProc(ref Message m)
{
    if (m.Msg == 0x02CC)
    {
        m.Result = (IntPtr)0x00000001;
        return;
    }
    base.WndProc(ref m);
}
```

### WPF

```csharp
protected override void OnSourceInitialized(EventArgs e)
{
    base.OnSourceInitialized(e);
    ((HwndSource)PresentationSource.FromVisual(this)).AddHook(Hook);
}

static IntPtr Hook(IntPtr h, int msg, IntPtr w, IntPtr l, ref bool handled)
{
    if (msg == 0x02CC)
    {
        handled = true;
        return (IntPtr)0x00000001;
    }
    return IntPtr.Zero;
}
```

### Avalonia

```csharp
using Avalonia.Win32;

Win32Properties.AddWndProcHookCallback(this, Hook); // Remove on close.

static IntPtr Hook(IntPtr h, uint msg, IntPtr w, IntPtr l, ref bool handled)
{
    if (msg == 0x02CC)
    {
        handled = true;
        return new IntPtr(0x00000001);
    }
    return IntPtr.Zero;
}
```

### Related behavior

Visual feedback and gestures use separate mechanisms. [Disable visual feedback](disable-pen-and-touch-feedback.md) when you only need to remove contact rings.

### Reference

* [`WM_TABLET_QUERYSYSTEMGESTURESTATUS`](https://learn.microsoft.com/windows/win32/tablet/wm-tablet-querysystemgesturestatus)
* [Tablet PC system gesture status flags](https://learn.microsoft.com/windows/win32/tablet/system-gesture-status)
