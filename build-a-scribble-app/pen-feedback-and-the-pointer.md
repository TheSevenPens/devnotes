# Build a Scribble app: pen feedback, gestures and the pointer

## Overview

A canvas that draws correctly can still show things the application did not draw. Windows adds a ring, a right click and a circle around a pen, and replaces the arrow with its own pointer. None of it is a stroke fault, none of it is covered by the checks on [Diagnosing a bad stroke](diagnosing-a-bad-stroke.md), and a person at the screen is the only way to see it.

This page covers what Windows adds, how a window tells Windows it does not want it, how to show that the answer is being given, and what was found about when each thing appears. Read it after the canvas draws. The mechanism is explained once, in [Windows pen behaviors](../pen-input-on-windows/windows-pen-behaviors/README.md); this page is how it applies to a Scribble app.

> **What was and was not checked.** Everything observed here comes from one machine (Windows 11, build 10.0.26300) and one tablet. The circle and the answer to Windows' question were observed in PenDynamicsLab, an Avalonia application. The Scribble apps answer the same question; the answer was checked without a pen in WPF, WinForms and Avalonia, and the other five apps were not built and run on that machine. Each claim below says which kind of evidence it rests on.

## 1. What Windows adds

| what you see | when | switched off by |
| --- | --- | --- |
| a ring, then a right click | the pen is held still, then lifted (press and hold) | `TABLET_DISABLE_PRESSANDHOLD` (`0x1`) |
| a small circle at the pen | a barrel button goes down | `TABLET_DISABLE_PENBARRELFEEDBACK` (`0x10`) |
| a wave | the pen lifts (pen up) | `TABLET_DISABLE_PENTAPFEEDBACK` (`0x8`) |

The values and the descriptions are from Microsoft's page for `WM_TABLET_QUERYSYSTEMGESTURESTATUS`. A window that does not answer receives all three.

A drawing surface wants none of them: a held pen is part of a stroke, not a request for a menu, and a circle under the pen covers the ink. Only the `0x10` flag has been seen to change anything on the test machine. The other two are documented and not yet tested.

## 2. Answer Windows' question

Windows asks each window which system gestures it wants by sending `WM_TABLET_QUERYSYSTEMGESTURESTATUS` (`0x02CC`). The window answers with a mask of the gestures to switch off. The message arrives through `SendMessageTimeout`, so answer in the window procedure and do nothing else there.

**Windows sent the query on every pen contact**, whether or not a button was pressed (observed in PenDynamicsLab: a count in the title bar rose on every touch). Install the answer when the window is created.

Native:

```c
// 0x02CC; tpcshrd.h defines the three flags
#define GESTURES_OFF (0x1 | 0x8 | 0x10)   // press and hold, tap wave, button circle

case 0x02CC:
    return GESTURES_OFF;
```

WinForms:

```csharp
protected override void WndProc(ref Message m)
{
    if (m.Msg == 0x02CC)
    {
        m.Result = (IntPtr)0x19;   // 0x1 | 0x8 | 0x10
        return;
    }
    base.WndProc(ref m);
}
```

Where each Scribble app answers, and what was checked:

| app | where | checked |
| --- | --- | --- |
| Scribble.Wpf | `HwndSource` hook | built; `--selftest` and `--replay` pass |
| Scribble.WinForms | `WndProc` override | built; `--selftest` and `--replay` pass |
| Scribble.Avalonia | `Win32Properties.AddWndProcHookCallback` (in `Avalonia.Controls` in Avalonia 12) | built; `--selftest` and `--replay` pass |
| Scribble.WinUI | `SetWindowSubclass` on the window handle | the subclass code ran in a separate test program; the app was not built |
| Scribble.Win32 | its window procedure | compiled with another compiler; not run |
| Scribble.Rust | `SetWindowSubclass` through FFI | the crate compiles; the subclass was tested on a real window; the app was not linked or run |
| Scribble.WinUINative | `SetWindowSubclass` | not compiled |
| Scribble.Qt | `nativeEvent` | not compiled |

The code for each is in the [WinPenKit repository](https://github.com/TheSevenPens/WinPenKit); `Docs/SCRIBBLE-APPS.md` has the section "Pen feedback and gestures".

**Keep a baseline.** The Scribble apps read `WINPENKIT_TABLET_GESTURE_FLAGS`, a hexadecimal mask. `0` answers "disable nothing", which is Windows' default; `10` answers only the circle. Look at what Windows draws at `0` first. If nothing appears there, there is nothing to switch off, and a run with the default answer proves nothing.

## 3. Show that the answer is being given

Two things report it, and neither needs a pen.

**The title bar** carries a count: `| gesture queries 12, answer 0x19`. The count rises on every pen contact. A count that stays at zero while the pen touches the canvas means Windows is not asking this window, so the answer is not reaching it. Check that the answer is installed on the window that receives the pen.

**`L0.gesture-query`** in `--selftest` sends the query to the window the way Windows does and checks the answer:

```
[PASS] L0.gesture-query          answered 0x19, expected 0x19
```

With the answer removed:

```
[FAIL] L0.gesture-query          answered 0x0, expected 0x19; the TabletGestures hook was not reached  <- Windows will draw its press-and-hold ring and a circle on a pen button press
```

The check proves the window answers. It does not prove that Windows will then skip the feedback. Windows' own Pen and Touch settings, and the way the pen reaches Windows (section 5), decide that. On the test machine press and hold was enabled for pen and touch; the settings were read and never changed.

This check adds one to the level 0 count. The counts on the other pages (for example "all six L0 and L1 checks") were written before it existed and describe the checks those pages build; this check is not part of them.

## 4. What a person checks

Run each action twice, once at the baseline answer (`0`) and once at the default (`0x19`). Write down what appears.

| action | what to look for |
| --- | --- |
| hold the pen still on the canvas for several seconds, then lift | a ring, then a context menu |
| press a barrel button while the pen hovers | a circle under the pen |
| press a barrel button while the pen touches the canvas | a circle under the pen |
| lift the pen | a wave |
| any of the above with the eraser end | the same four things |

A thing that appears at `0` and not at the default is a thing the answer switched off. A thing that appears at both is not switched off by this window's answer: look at the Pen and Touch settings and at the pen path.

## 5. When the circle appears

Observed in PenDynamicsLab, on one machine, with the barrel button pressed:

| how the pen reached Windows | answer `0` | answer `0x10` |
| --- | --- | --- |
| a virtual HID pen digitizer (a device Windows lists as a pen) | circle | no circle |
| a pen injected with `InjectSyntheticPointerInput` | no circle | no circle |

The query count rose on every pen contact in both.

So **which feedback appears depends on how the pen reaches Windows, not only on the application.** A test run with an injected pen can show no circle while a pen delivered by a driver does. Test with the path your users will have. The reading that the circle is feedback for a real pen device fits both results and has not been tested on a vendor driver; it is an inference.

The record of what was tried is TheSevenPens/devnotes#28.

## 6. The pointer

### Cursor numbers

A `PenPoint` carries a cursor number. `13` is the pen tip and `14` is the eraser, the values observed from Wacom drivers (`PenCursorType`). The pointer-based sessions write them. Wintab passes the driver's own number through, so on a tablet that numbers its eraser differently `IsEraser` is false on Wintab. Qt reports a pointer type, `Pen` or `Eraser`, and no number.

**Show the number, and name only the two known values.** The Scribble apps show `13 (pen)` and `14 (eraser)`, and any other number bare. A readout that says only "Eraser" cannot show that the driver numbered it something else, and a name guessed for an unknown number reads as a measurement.

### The hover pointer

While a pen is in range as a Windows pen pointer, Windows shows its own pen hover pointer, a small diamond, in place of the arrow. It was seen with an injected pen in PenDynamicsLab. It is what Windows does for a pen pointer, not a fault in the application, and no stroke check detects it.

An application can set its own cursor over its window. [Hide the cursor during a pen hold](../pen-input-on-windows/windows-pen-behaviors/disable-press-and-hold-right-click/hide-the-cursor-during-a-pen-hold.md) describes how, including that Windows can show the cursor again during a hold. The Scribble apps do not do this, and it has not been tried in them.

## 7. What no check covers

- **Whether Windows draws anything at all** depends on the Pen and Touch settings and on how the pen arrives. The checks above show only that the window answers.
- **Touch.** This page was checked with a pen only. Touch contacts were not tested.
- **`0x1` and `0x8`.** The ring and right click for press and hold, and the wave, were not observed to change on the test machine, with or without the answer.
- **Other machines, other Windows builds and other tablets.**

## Sources

- Microsoft: [`WM_TABLET_QUERYSYSTEMGESTURESTATUS`](https://learn.microsoft.com/windows/win32/tablet/wm-tablet-querysystemgesturestatus-message) and [System events and mouse messages](https://learn.microsoft.com/windows/win32/tablet/system-events-and-mouse-messages).
- [Disable press-and-hold right-click](../pen-input-on-windows/windows-pen-behaviors/disable-press-and-hold-right-click/README.md) and [Disable pen and touch feedback](../pen-input-on-windows/windows-pen-behaviors/disable-pen-and-touch-feedback.md), for the mechanism and the other route, `SetWindowFeedbackSetting`.
- WinPenKit pull request 148 (the Scribble apps) and PenDynamicsLab pull request 93.
