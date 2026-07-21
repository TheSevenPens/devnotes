# Sample apps to test Windows pen behaviors

Most of the hard problems in these notes are **OS-level behaviors** whose fixes are subtle and **window-level** (a WndProc message, a feedback setting, a DPI awareness context). Diagnosing them _inside_ a real application — a driver UI, a paint app, a calibration overlay — is slow and conflates concerns: you're fighting the app's own input plumbing, layout, and framework at the same time as the OS behavior.

The efficient approach is a set of **minimal, single-purpose sample apps** — one per gotcha — that reproduce the symptom in isolation and let us **A/B candidate fixes**, then bake the verified answer back into the corresponding note. Iterate in the sample, not in production.

{% hint style="success" %}
**These now exist:** [github.com/TheSevenPens/WindowsPenBehaviors](https://github.com/TheSevenPens/WindowsPenBehaviors).
Sample `01-core-pen-behaviors` covers the three core behaviors below, built in both
**raw Win32 (C)** — the ground-truth reference — and **.NET WinForms**. Each opens a
**RAW** and a **FIXED** window side by side and shows a live
[settings readout](windows-pen-touch-settings.md).
{% endhint %}

## What each sample should be

* **Reproduces the symptom out of the box** (no fix applied) so the behavior is obvious.
* **Shows the problem and the solution together.** A live toggle is ideal _when a fix is runtime-reversible_ — but several of these fixes are **latched per-window and cannot be un-applied at runtime** (see [Lessons learned](#lessons-learned)). For those, use **two windows born in different states** (RAW vs FIXED) compared side by side, not a toggle.
* **Reports the baseline.** Show the [global settings + device state](windows-pen-touch-settings.md) on-screen, so a missing symptom is self-explaining (setting off / indirect device) rather than a false "pass".
* **A short README**: symptom → cause → each fix tried and its verified result (works / partial / no effect), with a link to the matching implementation note.
* **Per-framework where the fix differs** (raw Win32, WinForms, WPF, WinUI 3, Avalonia) — the _concept_ is one thing, the _hook point_ differs per framework and that's where people get stuck.
* **Verified across input types + configs**: pen and touch; single vs multi-monitor; 100% vs scaled DPI; Windows Ink vs WinTab where relevant. Note that an **indirect pen device may not drive the shell behaviors at all** — verify on a direct-touch device.

## Backlog (seed from the implementation notes)

* ✅ **Tap / contact feedback rings** — the ripple the shell draws on every pen/touch tap. Pure cosmetic; `SetWindowFeedbackSetting` per `FEEDBACK_TYPE`. _(sample 01)_ ([note](disable-shell-pen-feedback.md))
* ✅ **Press-and-hold gesture** — the ring + right-click on a stationary contact. `WM_TABLET_QUERYSYSTEMGESTURESTATUS` → `TABLET_DISABLE_PRESSANDHOLD`. _(sample 01)_ ([note](disable-shell-pen-feedback.md))
* ✅ **Cursor reappears during a still hold** — the dwell's "other half"; no mouse-move to re-apply a hidden cursor. Compare `SetWindowFeedbackSetting`, `SetCursor(NULL)` on a timer, and handling `WM_SETCURSOR` (the zero-flicker one). _(sample 01)_ ([note](disable-shell-pen-feedback.md))
* **Hiding the cursor over a full-screen pen window** for _all_ input types, without breaking clickable chrome.
* **DPI & pen coordinate mapping** — Per-Monitor V2, `ClientToScreen` from the right awareness context. ([note](../dpi-and-pen-coordinates.md), [note](../per-monitor-v2-dpi-awareness.md))
* **WM\_POINTER coalescing** — retrieving the full input history vs the single current point. ([note](../wm-pointer-coalescing.md))
* **WinTab vs Windows Ink coexistence** — both active, driver conflict, which wins. ([note](../wintab-vs-windows-ink-driver-conflict.md))
* **Pressure normalization** — raw range vs pre-normalized 0..1 across tablets.
* **Tilt representations** — azimuth/altitude vs tiltX/tiltY round-trips. ([note](../tilt-representations.md))
* **Flicks / other shell gestures** — the rest of the `TABLET_DISABLE_*` flags.

## Lessons learned

From building sample 01. These shaped the design and are worth carrying into the rest.

* **Some fixes are not runtime-reversible.** Windows queries `WM_TABLET_QUERYSYSTEMGESTURESTATUS` **once, early, and caches it** — after it has seen `TABLET_DISABLE_PRESSANDHOLD`, clearing the flag does not re-enable the gesture. A per-fix "off" toggle silently keeps acting fixed. The reliable demo is a window **born without the fix** (RAW) next to one born with it (FIXED); the stickiness only comes from apply-then-unapply.
* **The symptom depends on settings _and_ device.** All the visualization settings can be ON and you still see nothing because the pen is an `ExternalPen` (indirect tablet / WinTab / OpenTabletDriver) that never drives the Ink shell. Read and display the baseline. → [Windows pen & touch settings](windows-pen-touch-settings.md).
* **Unicode window ⇒ Unicode `DefWindowProc`.** A `RegisterClassW` window that falls through to `DefWindowProcA` (i.e. compiled without `UNICODE`) reads its own wide title as ANSI and truncates it at the first `\0` — the title `"Windows…"` becomes just `"W"`. Define `UNICODE`/`_UNICODE`, or call `DefWindowProcW` explicitly.
* **Compile wide string literals as UTF-8.** MSVC reads source in the system ANSI codepage by default, mangling `—`/`→`/`•` in `L"…"` literals (`â€"`). Build with `/utf-8`.
* **DPI is not optional.** Under Per-Monitor V2 the client is physical pixels; a hard-coded pixel font is tiny at 200 %+. Scale text/layout by `GetDpiForWindow` (win32) / `DeviceDpi` (WinForms) and handle `WM_DPICHANGED`.
* **Per-framework hook points** (same native fixes, different attach point): win32 `WndProc` in the class + `SetProcessDpiAwarenessContext`; WinForms `override WndProc(ref Message)` + `this.Handle` + `Application.SetHighDpiMode(PerMonitorV2)` (and `<AllowUnsafeBlocks>` for `[LibraryImport]`).

## Feedback loop

Each sample is the source of truth for its note: when a sample proves which fix works (and which don't), update the note's "fixes tried → result" with the verified outcome. The samples are where we experiment; the notes are the distilled conclusion.

## Location

[**github.com/TheSevenPens/WindowsPenBehaviors**](https://github.com/TheSevenPens/WindowsPenBehaviors) — one folder per sample under `samples/`, and within each, one subfolder per framework (`win32/`, `winforms/`, …), each building to a tiny runnable exe.
