# Disabling feedback & gestures

## Overview

Windows uses separate mechanisms for feedback, gestures, and cursor state. Configure each behavior per window handle (`HWND`).

| Experience                                | Control                              |
| ----------------------------------------- | ------------------------------------ |
| Tap ripple, contact ring, or barrel flash | `SetWindowFeedbackSetting`           |
| Press-and-hold ring animation             | `FEEDBACK_*_PRESSANDHOLD`            |
| Press-and-hold right-click                | `WM_TABLET_QUERYSYSTEMGESTURESTATUS` |
| Cursor reappears during a hold            | `WM_SETCURSOR`                       |

### Choose the needed control

* [Disable pen and touch feedback](disable-pen-and-touch-feedback.md) for cosmetic contact rings and flashes.
* [Disable press-and-hold right-click](disable-press-and-hold-right-click/) for a window that owns hold interactions.
* [Hide the cursor during a pen hold](disable-press-and-hold-right-click/hide-the-cursor-during-a-pen-hold.md) when the cursor reappears during a stationary hold.

### Shared guidance

* **Feedback is not a gesture.** Disabling `FEEDBACK_*` removes visuals only.
* **Apply settings per window.** Popups, dialogs, and overlays need separate configuration.
* **Install gesture hooks early.** The system can query the window on its first pen input.
* **Respect normal interaction.** Restrict gesture and cursor changes to the relevant canvas or overlay.
