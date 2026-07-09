# Disabling Windows Shell Pen/Touch Feedback (and Gestures) Per Window

Windows draws its own pen/touch feedback *on top of* your app — the ripple/contact ring on every tap,
the press-and-hold ring — and runs shell gestures like **press-and-hold → right-click**. For a
full-screen canvas, a calibration overlay, a custom-gesture UI, or just a clean drawing-tablet app, you
usually want these gone. There are **two independent mechanisms**, and the single biggest time-saver is
knowing which is which.

## Two mechanisms — don't conflate them

| What you see / experience | Mechanism | Turn it off with |
|---|---|---|
| Ripple / contact ring on every **tap**; barrel & right-tap flashes | **Visual feedback** (cosmetic) | `SetWindowFeedbackSetting` per `FEEDBACK_TYPE` |
| Press-and-hold **ring** animation | **Visual feedback** (cosmetic) | `SetWindowFeedbackSetting(FEEDBACK_*_PRESSANDHOLD, FALSE)` |
| Press-and-hold **right-click** (the behaviour) | **System gesture** | answer `WM_TABLET_QUERYSYSTEMGESTURESTATUS` with `TABLET_DISABLE_PRESSANDHOLD` |
| **Cursor reappears** partway through a hold | side-effect of the gesture dwell | re-hide the cursor (§3) |

The trap: `SetWindowFeedbackSetting` removes the **animation only** — the gesture still fires.
`WM_TABLET_QUERYSYSTEMGESTURESTATUS` removes the **behaviour**. Two levers, two jobs. All of this is
**per-window** (an HWND) — no registry / OS-wide change, no effect on other apps.

---

## 1. Tap / contact feedback rings (pure cosmetic)

The ripple Windows draws where you tap with a pen or finger (and the barrel/right-tap flashes). It's
purely visual, so `SetWindowFeedbackSetting` alone kills it. **Safe to apply app-wide** — it only
suppresses visuals, so gestures (including pen **right-click**, which you may rely on for context menus)
still work.

```csharp
[DllImport("user32.dll")]
static extern bool SetWindowFeedbackSetting(IntPtr hwnd, uint feedback, uint flags, uint size, ref int config);

// FEEDBACK_TYPE (winuser.h)
const uint FEEDBACK_TOUCH_CONTACTVISUALIZATION = 1;  // the touch contact circle
const uint FEEDBACK_PEN_BARRELVISUALIZATION    = 2;
const uint FEEDBACK_PEN_TAP                     = 3;  // pen tap ripple
const uint FEEDBACK_PEN_DOUBLETAP              = 4;
const uint FEEDBACK_PEN_PRESSANDHOLD           = 5;  // press-and-hold *ring* (visual only)
const uint FEEDBACK_PEN_RIGHTTAP               = 6;
const uint FEEDBACK_TOUCH_TAP                  = 7;  // touch tap ripple
const uint FEEDBACK_TOUCH_DOUBLETAP            = 8;
const uint FEEDBACK_TOUCH_PRESSANDHOLD         = 9;
const uint FEEDBACK_TOUCH_RIGHTTAP             = 10;
const uint FEEDBACK_GESTURE_PRESSANDTAP        = 11;

void DisableAllFeedback(IntPtr hwnd)
{
    int off = 0; // BOOL FALSE
    for (uint fb = 1; fb <= 11; fb++)
        SetWindowFeedbackSetting(hwnd, fb, 0, sizeof(int), ref off);
}
```

Call it once the HWND exists (after the window is shown). Get the HWND however your framework exposes it
(WinForms `Handle`, WPF `HwndSource`, Avalonia `TryGetPlatformHandle().Handle`).

---

## 2. Press-and-hold → right-click (visual **and** behaviour)

### Symptom

The user rests the pen (or a finger) on one spot and holds; after ~1 s an animated **ring** appears, the
cursor re-shows, and if they keep holding it fires a **right-click** (context menu / `WM_RBUTTONDOWN`).
It shows up the moment you design any interaction around *holding still* — dwell-to-activate, a
calibration target averaged over a hold, a radial menu, etc.

### Why it happens

`Press and hold` is a **Windows shell gesture**. Any top-level window that receives pen/touch **pointer
input** is fed through the shell's gesture recognizer, and a stationary contact past the dwell time is a
right-click. It's the user's *Pen & Windows Ink* / legacy *Pen and Touch → Press and hold* setting — so
it's not your app misbehaving, and it fires even when you read the pen through *another* path (WinTab, a
driver's debug stream, raw HID), as long as the pen *also* generates ordinary OS pointer input on your
window (any Windows Ink / `WM_POINTER` scenario). Don't tell the user to change the global setting — fix
it per-window.

### Fix — answer `WM_TABLET_QUERYSYSTEMGESTURESTATUS`

Windows sends `WM_TABLET_QUERYSYSTEMGESTURESTATUS` (`0x02CC`) to ask which system gestures a window wants;
return a bitmask of `TABLET_DISABLE_*` flags for those you want **off**. `TABLET_DISABLE_PRESSANDHOLD`
suppresses the ring, the right-click, and (mostly) the cursor re-assertion, **for this window only**.

```
WM_TABLET_QUERYSYSTEMGESTURESTATUS = 0x02CC

// return value: OR together the gestures to DISABLE
TABLET_DISABLE_PRESSANDHOLD        0x00000001  // press-and-hold → right-click (the usual one)
TABLET_DISABLE_PENTAPFEEDBACK      0x00000008
TABLET_DISABLE_PENBARRELFEEDBACK   0x00000010
TABLET_DISABLE_TOUCHUIFORCEON      0x00000100
TABLET_DISABLE_TOUCHUIFORCEOFF     0x00000200
TABLET_DISABLE_TOUCHSWITCH         0x00008000
TABLET_DISABLE_FLICKS              0x00010000  // navigation flicks
TABLET_DISABLE_SMOOTHSCROLLING     0x00080000
TABLET_DISABLE_FLICKFALLBACKKEYS   0x00100000
TABLET_ENABLE_MULTITOUCHDATA       0x01000000  // (enable, not disable — opt into raw multitouch)
```

> Scope this to windows where *holding is your interaction* (a calibration overlay, a canvas) — **not
> app-wide** — because press-and-hold is a legitimate pen right-click everywhere else.

**Raw Win32**

```c
case WM_TABLET_QUERYSYSTEMGESTURESTATUS:
    return TABLET_DISABLE_PRESSANDHOLD;
```

**WinForms**

```csharp
protected override void WndProc(ref Message m)
{
    if (m.Msg == 0x02CC) { m.Result = (IntPtr)0x00000001; return; }
    base.WndProc(ref m);
}
```

**WPF**

```csharp
protected override void OnSourceInitialized(EventArgs e)
{
    base.OnSourceInitialized(e);
    ((HwndSource)PresentationSource.FromVisual(this)).AddHook(Hook);
}
static IntPtr Hook(IntPtr h, int msg, IntPtr w, IntPtr l, ref bool handled)
{
    if (msg == 0x02CC) { handled = true; return (IntPtr)0x00000001; }
    return IntPtr.Zero;
}
```

**Avalonia** (the Win32 backend exposes a WndProc hook)

```csharp
using Avalonia.Win32;
Win32Properties.AddWndProcHookCallback(this, Hook);   // remove on close

static IntPtr Hook(IntPtr h, uint msg, IntPtr w, IntPtr l, ref bool handled)
{
    if (msg == 0x02CC) { handled = true; return new IntPtr(0x00000001); }
    return IntPtr.Zero;
}
```

---

## 3. The cursor reappears at the dwell (the sneaky half)

Even after disabling the gesture, the **mouse cursor may pop back in** partway through a long hold (right
at the ~1 s press-and-hold dwell). Same interaction, different half:

- At the dwell, Windows treats the (gesture-disabled) stationary contact as ordinary **mouse-emulated**
  input and **re-asserts the mouse cursor**.
- Because the pen is held *still*, **no `WM_MOUSEMOVE`/`WM_SETCURSOR` follows** — so a cursor you hid by
  setting the window's cursor is never re-applied, and it **sticks visible**. (A window-cursor "hide" is
  only re-applied on the next `WM_SETCURSOR`, which a motionless pen never triggers.)

Fixes, increasing completeness:

1. **`SetWindowFeedbackSetting(FEEDBACK_PEN_PRESSANDHOLD, FALSE)`** — helps with the feedback, but on its
   own did **not** stop the cursor re-assertion in practice.
2. **Re-hide the cursor during the hold** — `SetCursor(NULL)` on a timer (e.g. per animation frame while
   holding). Simple and effective, but leaves a possible **sub-frame flicker**: Windows shows it, your
   next tick hides it, so it can blink for a frame or two.
3. **Handle `WM_SETCURSOR`** and set a null cursor (`SetCursor(NULL)`, return `TRUE`) — the zero-flicker
   version: you answer *every* time Windows asks what cursor to draw, so there's never a frame with the
   arrow. Prefer this if the flicker matters.

`SetCursor(NULL)` hides the cursor for the calling thread while the pointer is over a window that thread
owns — fine for a foreground full-screen overlay. Scope it to *while holding* so normal cursor behaviour
(and clickable chrome) returns otherwise.

---

## Gotchas (all of the above)

- **Per-window.** Everything here targets one HWND. Child windows, popups, dialogs, and separate overlays
  each need it applied. (A shared `DisableFeedback(hwnd)` helper called from each window's "opened" hook
  is the clean way.)
- **Hook early.** `WM_TABLET_QUERYSYSTEMGESTURESTATUS` can arrive as soon as pen input first reaches the
  window — install the hook when the window is created / first shown.
- **Feedback ≠ gesture.** Disabling `FEEDBACK_*` removes visuals only; the gesture still runs. That's why
  disabling feedback app-wide is safe (right-click keeps working) but doesn't stop press-and-hold's
  *behaviour*.
- **Return value is a bitmask** for the gesture message — OR the flags; returning `0` explicitly *enables*
  everything.
- **Touch vs pen:** `TABLET_DISABLE_PRESSANDHOLD` and the `FEEDBACK_TOUCH_*` / `FEEDBACK_PEN_*` families
  cover both; pick the ones you need.
- **Overrides the user's setting** for your window — you don't need "Press and hold" off system-wide.
- Disabling the shell's handling doesn't touch *your* input path — the pen still does the thing you
  actually wanted (the tap, the hold); you've only stopped the shell from decorating/claiming it.

## References

- [`WM_TABLET_QUERYSYSTEMGESTURESTATUS`](https://learn.microsoft.com/windows/win32/tablet/wm-tablet-querysystemgesturestatus) — Microsoft Learn
- [Tablet PC system gesture status flags (`TABLET_DISABLE_*`)](https://learn.microsoft.com/windows/win32/tablet/system-gesture-status) — Microsoft Learn
- [`SetWindowFeedbackSetting`](https://learn.microsoft.com/windows/win32/api/winuser/nf-winuser-setwindowfeedbacksetting) and [`FEEDBACK_TYPE`](https://learn.microsoft.com/windows/win32/api/winuser/ne-winuser-feedback_type) — Microsoft Learn
