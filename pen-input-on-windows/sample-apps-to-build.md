# Sample apps for the pen-input gotchas (to build)

Most of the hard problems in these notes are **OS-level behaviors** whose fixes are subtle and
**window-level** (a WndProc message, a feedback setting, a DPI awareness context). Diagnosing them
*inside* a real application — a driver UI, a paint app, a calibration overlay — is slow and conflates
concerns: you're fighting the app's own input plumbing, layout, and framework at the same time as the OS
behavior.

The efficient approach is a set of **minimal, single-purpose sample apps** — one per gotcha — that
reproduce the symptom in isolation and let us **A/B candidate fixes** with a toggle, then bake the
verified answer back into the corresponding note. Iterate in the sample, not in production.

## What each sample should be

- **Reproduces the symptom out of the box** (no fix applied) so the behavior is obvious.
- **Toggles for each candidate fix** (checkboxes / buttons / command-line flags), so fixes can be turned
  on independently and combined — the point is to see *exactly* which lever does what.
- **A short README**: symptom → cause → each fix tried and its verified result (works / partial / no
  effect), with a link to the matching implementation note.
- **Per-framework where the fix differs** (raw Win32, WinForms, WPF, WinUI 3, Avalonia) — the *concept*
  is one thing, the *hook point* differs per framework and that's where people get stuck.
- **Verified across input types + configs**: pen and touch; single vs multi-monitor; 100% vs scaled DPI;
  Windows Ink vs WinTab where relevant.

## Backlog (seed from the implementation notes)

- **Tap / contact feedback rings** — the ripple the shell draws on every pen/touch tap. Pure cosmetic;
  `SetWindowFeedbackSetting` per `FEEDBACK_TYPE`. ([note](implementation-notes/disable-shell-pen-feedback.md))
- **Press-and-hold gesture** — the ring + right-click on a stationary contact.
  `WM_TABLET_QUERYSYSTEMGESTURESTATUS` → `TABLET_DISABLE_PRESSANDHOLD`.
  ([note](implementation-notes/disable-shell-pen-feedback.md))
- **Cursor reappears during a still hold** — the dwell's "other half"; no mouse-move to re-apply a hidden
  cursor. Compare `SetWindowFeedbackSetting`, `SetCursor(NULL)` on a timer, and handling `WM_SETCURSOR`
  (the zero-flicker one). ([note](implementation-notes/disable-shell-pen-feedback.md))
- **Hiding the cursor over a full-screen pen window** for *all* input types, without breaking clickable
  chrome.
- **DPI & pen coordinate mapping** — Per-Monitor V2, `ClientToScreen` from the right awareness context.
  ([note](implementation-notes/dpi-and-pen-coordinates.md), [note](implementation-notes/per-monitor-v2-dpi-awareness.md))
- **WM_POINTER coalescing** — retrieving the full input history vs the single current point.
  ([note](implementation-notes/wm-pointer-coalescing.md))
- **WinTab vs Windows Ink coexistence** — both active, driver conflict, which wins.
  ([note](implementation-notes/wintab-vs-windows-ink-driver-conflict.md))
- **Pressure normalization** — raw range vs pre-normalized 0..1 across tablets.
- **Tilt representations** — azimuth/altitude vs tiltX/tiltY round-trips.
  ([note](implementation-notes/tilt-representations.md))
- **Flicks / other shell gestures** — the rest of the `TABLET_DISABLE_*` flags.

## Feedback loop

Each sample is the source of truth for its note: when a sample proves which fix works (and which don't),
update the note's "fixes tried → result" with the verified outcome. The samples are where we experiment;
the notes are the distilled conclusion.

## Location

TBD — a dedicated `pen-input-samples` repo (or a `samples/` folder here), one subfolder per gotcha, each
building to a tiny runnable exe.
