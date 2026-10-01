---
description: Suppress visual contact feedback for a single window.
---

# Disable pen and touch feedback

## Disable visual feedback

Windows can draw a ripple at each pen or touch contact. It can also show barrel and right-tap flashes. This feedback is cosmetic.

Use `SetWindowFeedbackSetting` for each `FEEDBACK_TYPE`. This affects one window only. Gestures, including pen right-click, continue to work.

```csharp
[DllImport("user32.dll")]
static extern bool SetWindowFeedbackSetting(
    IntPtr hwnd, uint feedback, uint flags, uint size, ref int config);

// FEEDBACK_TYPE (winuser.h)
const uint FEEDBACK_TOUCH_CONTACTVISUALIZATION = 1;
const uint FEEDBACK_PEN_BARRELVISUALIZATION    = 2;
const uint FEEDBACK_PEN_TAP                     = 3;
const uint FEEDBACK_PEN_DOUBLETAP               = 4;
const uint FEEDBACK_PEN_PRESSANDHOLD            = 5;
const uint FEEDBACK_PEN_RIGHTTAP                = 6;
const uint FEEDBACK_TOUCH_TAP                   = 7;
const uint FEEDBACK_TOUCH_DOUBLETAP             = 8;
const uint FEEDBACK_TOUCH_PRESSANDHOLD          = 9;
const uint FEEDBACK_TOUCH_RIGHTTAP              = 10;
const uint FEEDBACK_GESTURE_PRESSANDTAP         = 11;

void DisableAllFeedback(IntPtr hwnd)
{
    int off = 0; // BOOL FALSE
    for (uint feedback = 1; feedback <= 11; feedback++)
        SetWindowFeedbackSetting(hwnd, feedback, 0, sizeof(int), ref off);
}
```

Call this after the window exists. Obtain the window handle through your framework:

* WinForms: `Handle`
* WPF: `HwndSource`
* Avalonia: `TryGetPlatformHandle().Handle`

{% hint style="info" %}
You can apply visual-feedback suppression app-wide. It does not disable press-and-hold right-click.
{% endhint %}

### Related behavior

* [Disable press-and-hold right-click](disable-press-and-hold-right-click/)
* [Hide the cursor during a hold](disable-press-and-hold-right-click/hide-the-cursor-during-a-pen-hold.md)

### References

* [`SetWindowFeedbackSetting`](https://learn.microsoft.com/windows/win32/api/winuser/nf-winuser-setwindowfeedbacksetting)
* [`FEEDBACK_TYPE`](https://learn.microsoft.com/windows/win32/api/winuser/ne-winuser-feedback_type)
