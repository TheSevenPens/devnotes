# Build a Scribble app

> **Status: outlines.** The structure below is settled; the content is not written yet. Tracked in [#8](https://github.com/TheSevenPens/devnotes/issues/8).

A guided path to building a working pen-input drawing application on Windows using [WinPenKit](https://github.com/TheSevenPens/WinPenKit), aimed equally at a person and at an AI agent working on their behalf.

## What makes this different from a tutorial

**The reader may have no eyes.** Every stroke-quality bug found while building the six Scribble samples was found by a person looking at a stroke and saying it looked bumpy. An agent following a guide cannot do that, and neither can CI.

So diagnostics are **step one of the build**, not a troubleshooting appendix. The app is built to report its own state in text from the first page, because text is the only channel an agent has. Every guide here reaches a working canvas only after it can already tell you whether that canvas is correct.

**The guides are testable.** The acceptance criteria are executable: `--selftest` and `--replay` in WinPenKit verify the environment, the drawing surface and the coordinate conversion with no tablet and no person. A guide that produces an app failing those checks is a guide with a bug in it.

## Pick an entry point

Two, either sufficient on its own. They build the same app with the same diagnostics and the same acceptance checklist.

| | [Native / C++](canonical-native.md) | [WinForms](canonical-winforms.md) |
| --- | --- | --- |
| **Best for** | understanding the pipeline | getting to a working app fastest |
| **Coordinates** | you write the conversion yourself | the framework offers one (and it is wrong) |
| **Setup cost** | Visual Studio C++ workload | `dotnet new` |
| **What you give up** | time | seeing the raw pipeline |

The C++ path is canonical because **nothing is hidden**: you type the `POINT` struct yourself, so the central trap of pen input is self-evident rather than asserted. The WinForms path exists because a working app today beats a deeper model next week, and it links to the concept page for the parts it wraps.

Then [WPF](hard-mode-wpf.md), which is hard mode — the only framework where all three trap classes appear at once — followed by [short deltas](framework-deltas.md) for Avalonia, WinUI and Rust.

## Why this order

**Each step introduces exactly one new variable.**

```
C++          the pen APIs and the raw coordinate pipeline.  Pixels throughout.
WinForms     new library surface, same coordinate model.    Pixels throughout.
WPF          coordinate model changes to DIPs, and layout rounding
             and surface scaling arrive with it.
```

That is not only pedagogy, it is diagnostic isolation. Go straight from C++ to WPF and a bad stroke has two possible causes — misusing the library, or botching the DIP maths. With WinForms in between the library is already proven, so a WPF failure is necessarily coordinate-model.

It also teaches the single most important lesson three times, with the concealment increasing one notch each time:

| step | the type | how hidden |
| --- | --- | --- |
| C++ | `POINT { LONG x, y }` | not hidden at all — you write the conversion |
| WinForms | `System.Drawing.Point { int X, Y }` | still obviously integer, now behind a method |
| WPF | `System.Windows.Point { double X, Y }` | **looks safe, is not** |

By the time the signature actively lies, the reader already knows what to suspect.

## The pages

- **[Native / C++](canonical-native.md)** — canonical entry point, nothing hidden
- **[WinForms](canonical-winforms.md)** — canonical entry point, fastest to working
- **[WPF](hard-mode-wpf.md)** — hard mode: truncation, DIP-sized surfaces, fractional alignment
- **[Framework deltas](framework-deltas.md)** — Avalonia, WinUI, Rust
- **[Diagnosing a bad stroke](diagnosing-a-bad-stroke.md)** — the decision tree, framework-agnostic

Background lives elsewhere and is linked rather than repeated — chiefly [Framework Coordinate Conversion](../pen-input-on-windows/implementation-notes/framework-coordinate-conversion.md), which carries the rule every one of these pages depends on.

## What no guide can give you

Stated here so a green acceptance run is never mistaken for a finished app:

- **Wintab needs a tablet.** Synthetic pen injection does not reach the driver.
- **The session is not covered by replay.** A recording holds what the session produced, so replaying it tests everything downstream and nothing inside.
- **Whether a stroke feels right is not machine-checkable.** Deliberately not automated.
