---
description: Control visual feedback, press-and-hold, and cursor behavior per window.
---

# Disabling Shell Pen/Touch Feedback & Gestures

## Shell pen and touch behavior

Windows uses separate mechanisms for feedback, gestures, and cursor state. Configure each behavior per window handle (`HWND`).

| Experience                                | Mechanism            | Control                              |
| ----------------------------------------- | -------------------- | ------------------------------------ |
| Tap ripple, contact ring, or barrel flash | Visual feedback      | `SetWindowFeedbackSetting`           |
| Press-and-hold ring animation             | Visual feedback      | `FEEDBACK_*_PRESSANDHOLD`            |
| Press-and-hold right-click                | System gesture       | `WM_TABLET_QUERYSYSTEMGESTURESTATUS` |
| Cursor reappears during a hold            | Mouse-emulated input | `WM_SETCURSOR`                       |

### Choose the needed control

* [Disable pen and touch feedback](disable-pen-and-touch-feedback.md) for cosmetic contact rings and flashes.
* [Disable press-and-hold right-click](disable-press-and-hold-right-click.md) for a window that owns hold interactions.
* [Hide the cursor during a pen hold](hide-the-cursor-during-a-pen-hold.md) when the cursor reappears during a stationary hold.

### Shared guidance

* **Feedback is not a gesture.** Disabling `FEEDBACK_*` removes visuals only.
* **Apply settings per window.** Popups, dialogs, and overlays need separate configuration.
* **Install gesture hooks early.** The system can query the window on its first pen input.
* **Respect normal interaction.** Restrict gesture and cursor changes to the relevant canvas or overlay.
