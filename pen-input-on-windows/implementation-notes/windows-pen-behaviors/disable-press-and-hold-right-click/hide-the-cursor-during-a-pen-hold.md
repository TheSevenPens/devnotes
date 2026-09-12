---
description: Keep the cursor hidden while a pen or touch contact remains stationary.
---

# Hide the cursor during a pen hold

## Hide the cursor during a hold

Windows can re-show the cursor during a long hold. This often occurs at the press-and-hold dwell time. It can happen after disabling the gesture.

Windows treats the stationary contact as mouse-emulated input. A motionless pen produces no later `WM_MOUSEMOVE` or `WM_SETCURSOR`. A cursor hidden by window settings may remain visible.

### Choose an approach

1. Disable `FEEDBACK_PEN_PRESSANDHOLD`. This removes feedback but may not stop Windows from showing the cursor again.
2. Call `SetCursor(NULL)` during the hold. A timer can re-hide it each animation frame. This can show a brief flicker.
3. Handle `WM_SETCURSOR`. Set the null cursor and return `TRUE`. This prevents the visible frame.

Use the third approach when flicker matters.

```c
case WM_SETCURSOR:
    if (holding) {
        SetCursor(NULL);
        return TRUE;
    }
    break;
```

`SetCursor(NULL)` hides the cursor for the calling thread. It applies while the pointer is over a window owned by that thread.

Scope this behavior to the hold. Restore normal cursor behavior afterward. This works well for a foreground full-screen overlay. It should not hide cursor feedback over normal controls.

### Related behavior

* [Disable visual feedback](../disable-pen-and-touch-feedback.md)
* [Disable press-and-hold right-click](./)
