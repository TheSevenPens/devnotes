---
description: >-
  The system-wide settings and device facts that decide whether these pen
  behaviors happen at all — read them before concluding a fix "works".
---

# Windows pen & touch settings

## Overview

The per-window fixes in this section (feedback, press-and-hold, cursor) assume the
behavior is actually happening. But whether Windows produces it at all depends on
two things **outside your window**:

1. **Global visualization settings** — system-wide toggles for pen/touch feedback.
2. **The input device** — a direct-touch pen/screen and an indirect tablet do not
   drive the Windows Ink shell the same way.

If a setting is off, or the pen is an indirect device, you can see **no symptom to
fix** — and mistake "the shell never produced it" for "my fix worked". A test app
should read and display these live so the baseline is visible.

## Settings that gate the behaviors

Read them with `SystemParametersInfo` (the `SPI_GET…` actions). Each writes its
value into `pvParam`.

| Setting | `SPI_GET…` action | Governs |
| ------- | ----------------- | ------- |
| Contact visualization | `SPI_GETCONTACTVISUALIZATION` `0x2018` | touch contact rings |
| Gesture visualization | `SPI_GETGESTUREVISUALIZATION` `0x201A` | gesture visuals; bit `0x08` = press-and-hold |
| Pen visualization | `SPI_GETPENVISUALIZATION` `0x201E` | pen tap / press feedback |
| Pen arbitration | `SPI_GETPENARBITRATIONTYPE` `0x2020` | pen/touch arbitration mode |

Value constants (`winuser.h`):

```
CONTACTVISUALIZATION_OFF  0x0000   ON 0x0001   PRESENTATIONMODE 0x0002
GESTUREVISUALIZATION_ON   0x001F   // bitmask: TAP 0x01 DOUBLETAP 0x02
                                   //          PRESSANDTAP 0x04 PRESSANDHOLD 0x08 RIGHTTAP 0x10
PENVISUALIZATION_ON       0x0023   OFF 0x0000
```

```c
uint32_t contact = 0, gesture = 0, pen = 0, arb = 0;
SystemParametersInfoW(SPI_GETCONTACTVISUALIZATION, 0, &contact, 0);
SystemParametersInfoW(SPI_GETGESTUREVISUALIZATION, 0, &gesture, 0);
SystemParametersInfoW(SPI_GETPENVISUALIZATION,     0, &pen,     0);
SystemParametersInfoW(SPI_GETPENARBITRATIONTYPE,   0, &arb,     0);
// press-and-hold visual is enabled when (gesture & GESTUREVISUALIZATION_PRESSANDHOLD)
```

## The device matters: `SM_DIGITIZER`

`GetSystemMetrics(SM_DIGITIZER)` returns a bitmask of the digitizers present;
`SM_MAXIMUMTOUCHES` gives the touch-point count.

| Flag | Meaning |
| ---- | ------- |
| `NID_INTEGRATED_TOUCH` `0x01` | touch built into the display |
| `NID_EXTERNAL_TOUCH` `0x02` | external touch digitizer |
| `NID_INTEGRATED_PEN` `0x04` | pen built into the display (direct) |
| `NID_EXTERNAL_PEN` `0x08` | external pen digitizer (often indirect) |
| `NID_MULTI_INPUT` `0x40` | multiple inputs supported |
| `NID_READY` `0x80` | a digitizer is ready |

{% hint style="warning" %}
**An `ExternalPen` (indirect tablet, or a pen routed through WinTab /
OpenTabletDriver) frequently does _not_ drive the Windows Ink shell feedback and
press-and-hold** the way a direct-touch pen/screen does — **even with every
visualization setting ON**. On such a device you draw fine (pointer input arrives)
but see no contact ring and no press-and-hold gesture. So "RAW shows no rings" can
mean _the device never drove the shell_, not _the fix worked_. **Verify these fixes
on a direct-touch device** (a touchscreen, or a pen display in its native pointer
mode).
{% endhint %}

## Where users change these

* **Settings → Bluetooth & devices → Pen & Windows Ink** — visual effects toggles
  (these back the `SPI_*VISUALIZATION` values above).
* **Legacy "Pen and Touch" control panel** (`control main.cpl`, or run
  `control.exe /name Microsoft.PenAndTouch`) — the **"Press and hold for
  right-clicking"** enable lives here, separate from the visualization settings.
  Backing store: `HKCU\Software\Microsoft\Wisp\Pen\SysEventParameters`
  (`HoldMode`, `HoldTime`, `RightMaskEnable`, …).

## Why this matters for testing

Because the presence of a symptom depends on settings _and_ device, a test app
should read and show these values on-screen. Then a missing symptom is
self-explaining: either a visualization is `OFF`, or the digitizer is an
`ExternalPen` that isn't driving the shell — rather than a silent false "pass".
The [sample apps](sample-apps-to-build.md) render this readout in every window.

## References

* [`SystemParametersInfo`](https://learn.microsoft.com/windows/win32/api/winuser/nf-winuser-systemparametersinfow)
* [`GetSystemMetrics`](https://learn.microsoft.com/windows/win32/api/winuser/nf-winuser-getsystemmetrics) — see `SM_DIGITIZER`, `SM_MAXIMUMTOUCHES`
* [Pen visualization / gesture visualization SPI constants](https://learn.microsoft.com/windows/win32/api/winuser/nf-winuser-systemparametersinfoa)
