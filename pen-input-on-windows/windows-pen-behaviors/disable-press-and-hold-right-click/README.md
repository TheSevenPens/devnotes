---
description: Prevent the Windows press-and-hold gesture and the pen feedback rings for a single window.
---

# Disable press-and-hold right-click

## Disable press-and-hold right-click

A stationary pen or touch contact can trigger Windows press-and-hold. Windows shows a ring while the contact is held. Lifting the pen after the ring has appeared sends a right-click. Holding on until the ring goes away turns it back into an ordinary tap (Microsoft calls this hold-through).

That description is Microsoft's, written for the original Tablet PC. The behavior on current Windows has not been re-checked here.

Windows asks each window which system gestures it wants. It sends `WM_TABLET_QUERYSYSTEMGESTURESTATUS`. A window that does not answer receives all of them. Answer with a mask of the gestures to switch off.

{% hint style="warning" %}
Use this only where holding is your interaction. Keep press-and-hold elsewhere for normal pen right-click.
{% endhint %}

### Gesture-status flags

```
WM_TABLET_QUERYSYSTEMGESTURESTATUS = 0x02CC   // WM_TABLET_DEFBASE (0x02C0) + 12

// Return an OR-ed bitmask of gestures to disable.
TABLET_DISABLE_PRESSANDHOLD        0x00000001 // press and hold (right-click) gesture
TABLET_DISABLE_PENTAPFEEDBACK      0x00000008 // UI feedback on pen up (waves)
TABLET_DISABLE_PENBARRELFEEDBACK   0x00000010 // UI feedback on pen button down (circle)
TABLET_DISABLE_TOUCHUIFORCEON      0x00000100
TABLET_DISABLE_TOUCHUIFORCEOFF     0x00000200
TABLET_DISABLE_TOUCHSWITCH         0x00008000
TABLET_DISABLE_FLICKS              0x00010000
TABLET_ENABLE_FLICKSONCONTEXT      0x00020000
TABLET_ENABLE_FLICKLEARNINGMODE    0x00040000
TABLET_DISABLE_SMOOTHSCROLLING     0x00080000
TABLET_DISABLE_FLICKFALLBACKKEYS   0x00100000
TABLET_ENABLE_MULTITOUCHDATA       0x01000000 // Enables raw multitouch data.
```

The names, values and the three comments on the first lines are from Microsoft's `WM_TABLET_QUERYSYSTEMGESTURESTATUS` page (`tpcshrd.h`).

Returning `0` disables nothing. That is the default, and a window that never answers gets the same result. Install the hook when the window is created.

The answer can differ by position. `lParam` holds the screen coordinates of the contact (`GET_X_LPARAM` and `GET_Y_LPARAM`), so a window can disable a gesture for a region only.

{% hint style="info" %}
Windows sends the query with `SendMessageTimeout`. Answer immediately and do nothing else in the handler. Microsoft also notes that disabling press-and-hold makes mouse clicks respond faster, because Windows otherwise waits to tell a click from the start of a hold.
{% endhint %}

### The circle that appears when a pen button is pressed

A small white ring can appear under the pen when a barrel button is pressed. It is not the press-and-hold ring: it appears on the button press, not on a held contact.

Flag `0x10`, `TABLET_DISABLE_PENBARRELFEEDBACK`, is the one that removes it. Microsoft's example labels it "disables UI feedback on pen button down (circle)", and the feedback enum describes `FEEDBACK_PEN_BARRELVISUALIZATION` as "feedback for a pen barrel-button event".

Tested once, on Windows 11 (10.0.26300) with a Wacom tablet presented to Windows as a virtual HID pen digitizer, in an Avalonia 12.1.2 window:

* Windows sent the query on every pen contact, whether or not a button was pressed.
* Answering `0` (disable nothing): the circle appeared when a button was pressed.
* Answering `0x10` alone: no circle.
* The same window with a pen injected through `InjectSyntheticPointerInput`: no circle, even when answering `0`.

The last result suggests the circle belongs to input from a real pen device. This test does not establish that.

### Raw Win32

```c
case WM_TABLET_QUERYSYSTEMGESTURESTATUS:
    return TABLET_DISABLE_PRESSANDHOLD | TABLET_DISABLE_PENTAPFEEDBACK | TABLET_DISABLE_PENBARRELFEEDBACK;
```

### WinForms

```csharp
protected override void WndProc(ref Message m)
{
    if (m.Msg == 0x02CC)
    {
        m.Result = (IntPtr)0x00000019; // press and hold, tap wave, button circle
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
        return (IntPtr)0x00000019; // press and hold, tap wave, button circle
    }
    return IntPtr.Zero;
}
```

### Avalonia

```csharp
using Avalonia.Controls; // Win32Properties lives here in Avalonia 12 (checked in 12.1.2)

Win32Properties.AddWndProcHookCallback(this, Hook); // Remove on close.

static IntPtr Hook(IntPtr h, uint msg, IntPtr w, IntPtr l, ref bool handled)
{
    if (msg == 0x02CC)
    {
        handled = true;
        return new IntPtr(0x00000019); // press and hold, tap wave, button circle
    }
    return IntPtr.Zero;
}
```

In earlier Avalonia versions the namespace may differ. That was not checked.

### Setting it as a window property

Microsoft's example for disabling these for a whole window does not use the message. It sets a window property to the same mask:

```c
ATOM atom = GlobalAddAtom(L"MicrosoftTabletPenServiceProperty");
SetProp(hwnd, L"MicrosoftTabletPenServiceProperty", (HANDLE)(ULONG_PTR)mask);
GlobalDeleteAtom(atom);
```

This is useful where a framework does not let you reach the window procedure. It has not been tested here.

### What has been checked

| Claim | Status |
| --- | --- |
| Message value, flag names, values and the comments on `0x1`, `0x8`, `0x10` | Microsoft's documentation |
| `FEEDBACK_TYPE` values, `SetWindowFeedbackSetting` signature | Microsoft's documentation |
| Avalonia 12.1.2 hook class, namespace and callback signature | Read from the assembly, then compiled and run |
| Query arrives on every pen contact | Tested once (see above) |
| `0x10` removes the barrel-button circle | Tested once (see above) |
| `0x1` ends the press-and-hold ring and right-click; `0x8` removes the tap wave | Not tested |
| Raw Win32, WinForms and WPF snippets; the `SetProp` route | Not compiled or run |

### Used in the Scribble apps

The Scribble apps answer this message and show how often Windows asks in the title bar. [Build a Scribble app: pen feedback, gestures and the pointer](../../../build-a-scribble-app/pen-feedback-and-the-pointer.md) lists where each app answers it, the self-test check, and what was found about when the circle appears.

### Related behavior

Visual feedback has two routes. The flags above (`0x8` and `0x10`) are one. [Disable visual feedback](../disable-pen-and-touch-feedback.md) describes the other, `SetWindowFeedbackSetting`, which works per feedback type.

### Reference

* [`WM_TABLET_QUERYSYSTEMGESTURESTATUS`](https://learn.microsoft.com/windows/win32/tablet/wm-tablet-querysystemgesturestatus-message)
* [System events and mouse messages](https://learn.microsoft.com/windows/win32/tablet/system-events-and-mouse-messages)
* [`FEEDBACK_TYPE`](https://learn.microsoft.com/windows/win32/api/winuser/ne-winuser-feedback_type)
