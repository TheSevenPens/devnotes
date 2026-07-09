# Disabling the Press-and-Hold (Right-Click) Gesture on a Pen Window

A poorly-known but common problem: when your app *wants* the user to hold the pen still on a spot,
Windows steals that gesture for its own **press-and-hold → right-click**, drawing an animated ring at
the contact point and re-showing the cursor. This note explains why it happens and the per-window way to
turn it off.

## Symptom

The user rests the pen (or a finger) on one spot and holds. After a moment:

- an animated **ring / halo** appears at the contact point (the "press and hold" affordance), and
- the **cursor re-appears** (even if you'd hidden it), and
- if they keep holding, Windows fires a **right-click** (context menu / `WM_RBUTTONDOWN`).

It shows up the instant you design any interaction around *holding the pen still* — dwell-to-activate,
hold-to-confirm, a calibration target you average over a hold, a radial menu, a paint tool that arms on
dwell, etc.

## Why it happens

`Press and hold` is a **Windows shell gesture**, not something your app opts into. Any top-level window
that receives pen or touch **pointer input** is fed through the shell's gesture recognizer, and a
stationary contact held past the system dwell time is interpreted as a right-click. It's governed by the
user's *Pen & Windows Ink* / legacy *Pen and Touch → Press and hold* setting, so:

- It is **not** your app misbehaving — the OS is reacting to real pen/touch input landing on your window.
- It fires even when you read the pen through some *other* path (WinTab, a driver's debug stream, raw
  HID). As long as the pen also generates ordinary OS pointer input on your window — which it does in any
  Windows Ink / `WM_POINTER` scenario — the shell sees the contact and runs the gesture.
- Telling the user to change the global setting is a bad fix: it's OS-wide, per-user, and not your call.

## The fix — opt out per window

A window can tell Windows exactly which system gestures it wants by answering
**`WM_TABLET_QUERYSYSTEMGESTURESTATUS`** (`0x02CC`). Windows sends this message to query gesture status;
return a bitmask of `TABLET_DISABLE_*` flags for the gestures you want **off**. Returning
`TABLET_DISABLE_PRESSANDHOLD` suppresses the ring, the right-click, **and** the cursor re-assertion — for
**this window only**. No registry edit, no OS-wide change, no effect on other apps.

```
WM_TABLET_QUERYSYSTEMGESTURESTATUS = 0x02CC

// return value: OR together the gestures to DISABLE
TABLET_DISABLE_PRESSANDHOLD        0x00000001  // press-and-hold → right-click (the one you usually want)
TABLET_DISABLE_PENTAPFEEDBACK      0x00000008  // the little "tap" star burst
TABLET_DISABLE_PENBARRELFEEDBACK   0x00000010  // barrel-button feedback
TABLET_DISABLE_TOUCHUIFORCEON      0x00000100
TABLET_DISABLE_TOUCHUIFORCEOFF     0x00000200
TABLET_DISABLE_TOUCHSWITCH         0x00008000
TABLET_DISABLE_FLICKS              0x00010000  // navigation flicks
TABLET_DISABLE_SMOOTHSCROLLING     0x00080000
TABLET_DISABLE_FLICKFALLBACKKEYS   0x00100000
TABLET_ENABLE_MULTITOUCHDATA       0x01000000  // (enable, not disable — opt into raw multitouch)
```

For a full-screen canvas / overlay you often want at least `PRESSANDHOLD`, and frequently also `FLICKS`
and the tap/barrel feedback, so nothing the shell draws interferes with your own rendering.

### Raw Win32 (window procedure)

```c
case WM_TABLET_QUERYSYSTEMGESTURESTATUS:
    return TABLET_DISABLE_PRESSANDHOLD;   // (OR in more flags as needed)
```

### WinForms

```csharp
protected override void WndProc(ref Message m)
{
    const int WM_TABLET_QUERYSYSTEMGESTURESTATUS = 0x02CC;
    if (m.Msg == WM_TABLET_QUERYSYSTEMGESTURESTATUS)
    {
        m.Result = (IntPtr)0x00000001; // TABLET_DISABLE_PRESSANDHOLD
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

private static IntPtr Hook(IntPtr hwnd, int msg, IntPtr w, IntPtr l, ref bool handled)
{
    if (msg == 0x02CC) { handled = true; return (IntPtr)0x00000001; }
    return IntPtr.Zero;
}
```

### Avalonia (the backend exposes a Win32 WndProc hook)

```csharp
using Avalonia.Win32;

// once the window is open:
Win32Properties.AddWndProcHookCallback(this, WndProcHook);   // remove on close

private static IntPtr WndProcHook(IntPtr hWnd, uint msg, IntPtr w, IntPtr l, ref bool handled)
{
    if (msg == 0x02CC) { handled = true; return new IntPtr(0x00000001); }
    return IntPtr.Zero;
}
```

## Alternative / complement — `SetWindowFeedbackSetting`

`SetWindowFeedbackSetting(hwnd, FEEDBACK_TYPE, 0, sizeof(BOOL), &FALSE)` turns off the **visual**
feedback for a specific interaction on a window — e.g. `FEEDBACK_PEN_PRESSANDHOLD` (5) and
`FEEDBACK_TOUCH_PRESSANDHOLD` (9) hide the ring animation. Useful, but note the distinction:

- `SetWindowFeedbackSetting` suppresses the **animation** only; the **gesture itself** (the right-click)
  can still fire.
- `WM_TABLET_QUERYSYSTEMGESTURESTATUS` + `TABLET_DISABLE_PRESSANDHOLD` disables the **gesture** (and with
  it the animation and the cursor re-assertion).

If your only complaint is the ring, either works. If you also don't want the stray right-click (and you
want the cursor to stay as you set it), use the gesture message — it's the complete fix. Belt-and-suspenders
is fine: do both.

## Gotchas

- **Hook early.** The query can arrive as soon as pen input first reaches the window. Install the WndProc
  hook when the window is created / first shown, before the user can put the pen down on it.
- **Per-window.** It applies to the HWND you answered on. Child windows, popups, and separate overlay
  windows each need their own hook.
- **Overrides the user setting per window** — you don't need "Press and hold" turned off system-wide; the
  message wins for your window regardless.
- **Return value is a bitmask**, not a boolean — OR the flags you want. Returning `0` explicitly *enables*
  all gestures (rarely what you want if you handled the message at all).
- **Touch vs pen:** `TABLET_DISABLE_PRESSANDHOLD` covers both pen and touch press-and-hold. Touch has
  additional right-tap/two-finger behaviors if you need to chase those.
- Don't forget to still let the pen do the thing you *did* want (the hold). Disabling the gesture doesn't
  affect your own input path — it only stops the shell from claiming the hold.

## References

- [`WM_TABLET_QUERYSYSTEMGESTURESTATUS`](https://learn.microsoft.com/windows/win32/tablet/wm-tablet-querysystemgesturestatus) — Microsoft Learn
- [Tablet PC system gesture status flags (`TABLET_DISABLE_*`)](https://learn.microsoft.com/windows/win32/tablet/system-gesture-status) — Microsoft Learn
- [`SetWindowFeedbackSetting`](https://learn.microsoft.com/windows/win32/api/winuser/nf-winuser-setwindowfeedbacksetting) — Microsoft Learn
