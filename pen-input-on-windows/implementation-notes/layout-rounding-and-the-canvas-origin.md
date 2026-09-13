# Layout rounding and the canvas origin

A drawing surface placed below a toolbar starts wherever that toolbar ends. In a framework that
lays out in logical units, that position is a whole number of logical units — and at a
fractional display scale, a whole number of logical units is not a whole number of device
pixels.

```
130 logical units x 2.25 = 292.5 device pixels
```

Half a pixel. The framework then resamples the entire surface to draw it between pixel rows,
softening every edge at once, while the coordinates and the resolution both still measure
correct. That is the first cost, and it is the one people expect.

The second cost is worse, and is the reason this note exists.

## Snapping a permanent half is a coin flip

The obvious repair is to snap the origin to the device grid:

```rust
let snapped = (raw * ppp).round() / ppp;
```

This is correct advice and it is not enough. If the offset lands on exactly `.5` **every frame**,
then every snap is resolving a tie — and a tie is decided by whichever way the floating-point
arithmetic happened to fall, not by the rounding rule.

Measured in `Scribble.Rust` on 12 Sep 2026. The ribbon asked for exactly 130 points, so
`raw * ppp` landed on `.5` in every frame of every run. Instrumenting two consecutive frames of
the same run:

```
frame 1   raw*ppp = 650.5000  ->  651  ->  289.333344
frame 2   raw*ppp = 673.4999  ->  673  ->  299.111115     (673.5 would give 674 -> 299.555556)
```

`f32` is not precise enough to put both on the same side of the tie, so one frame snapped up and
the next snapped down. The canvas moved a pixel between two frames in which nothing had moved.

That surfaced as an acceptance check failing **about one run in eight**, reporting a 22px window
move where the window had moved 23. The check blamed a cached origin, because that was the fault
it had been written to catch. The origin was fine. The arithmetic was not.

An intermittent failure is worse than a consistent one: it teaches whoever sees it to re-run
rather than to look.

## The fix is to remove the tie, not to settle it

Size the toolbar so the surface below it starts on a whole device pixel. Then no rounding
decision is made at all.

```
grow the toolbar to the next height h where h x scale is a whole number
```

At 2.25 that means a multiple of 4 logical units; at 1.5, a multiple of 2; at 2.0, any integer.
Grow rather than shrink, or the toolbar clips its own contents. Recompute it when the scale
changes, because a window dragged to another display takes a different answer with it.

Keep the snap as well, with a small epsilon so a value a ten-thousandth either side of `.5`
resolves the same way. It is insurance against a margin this calculation did not anticipate,
not the cure — and the distinction is worth a comment, so nobody later deletes the height
calculation and keeps the snap.

## Which frameworks do this for you

Measured on 12 Sep 2026 at 2.25x, by shifting each sample's toolbar by one logical unit and
reading the canvas origin back out of `--selftest`. A framework that rounds keeps the origin on
a whole **device** pixel, which after the shift is a *fractional* number of logical units — that
mismatch is the signature.

| framework | rounds layout to device pixels? | how it shows |
| --- | --- | --- |
| Win32, WinForms | not applicable | they lay out in device pixels already |
| WPF | opt in, `UseLayoutRounding="True"` | set explicitly on the window |
| Avalonia | **yes, by default** | origin 678px = 301.33 DIP — whole device, fractional logical |
| WinUI 3 | **yes, by default** | origin 730px = 324.44 effective px — same signature |
| Qt Widgets | **no** | a 211-point toolbar put the origin at y=475.25px |
| egui | **no** | needs the snap above, by hand |

So the two frameworks people most often worry about, Avalonia and WinUI, handle it themselves.
The two that do not are the two with no layout-rounding facility at all.

## Two symptoms from one cause

The same half pixel was found in two frameworks within hours, and presented differently in each:

- **Qt Widgets** — a toolbar that wanted 211 logical units put the canvas origin at `y=475.25`.
  Caught immediately by a surface-alignment check, because the origin was *visibly* fractional.
- **egui** — a toolbar of exactly 130 points put the origin at a permanent `.5`, which a snap
  then hid behind a tie. The alignment check passed every time. Only a second check, one that
  moved the window and measured whether the origin followed, ever saw it, and then only
  sometimes.

The second is the one to watch for. A surface-alignment check reports the origin *after*
snapping, so a correct-looking whole number can be the output of a coin flip.

## What to check

1. Is the toolbar's height, times the display scale, a whole number? If not, fix it there.
2. Does the canvas origin report a whole device pixel — and does it report the **same** whole
   device pixel on two consecutive frames with nothing moving?
3. Does a check that moves the window and measures whether the origin follows it agree with the
   distance the window actually moved? That is the check that catches a tie; an alignment check
   alone cannot.

## See also

- [DPI and pen coordinates](dpi-and-pen-coordinates.md)
- [Per-Monitor V2 DPI awareness](per-monitor-v2-dpi-awareness.md)
- [Framework deltas](../../build-a-scribble-app/framework-deltas.md), for the per-framework
  layout units and where each gets its scale
