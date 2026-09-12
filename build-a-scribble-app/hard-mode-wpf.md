# Build a Scribble app: WPF (hard mode)

> **Status: outline.** Headings and intent only. Tracked in [#8](https://github.com/TheSevenPens/devnotes/issues/8).

Assumes one of the canonical entry points is done. **All three trap classes appear here at once**, which makes WPF a poor place to start and the best place to learn what goes wrong.

Reference implementation: `Scribble.Wpf` in WinPenKit.

---

## 1. What changes from the canonical path

*Intent: name the single new variable up front. Everything hard about this page follows from it.*

- WPF lays out in DIPs, not pixels
- Three consequences, one per section below
- The library is already proven by the canonical path, so any failure here is necessarily coordinate-model

## 2. Trap one: the conversion that lies

*Intent: the headline of the entire guide set. A framework method with a floating-point signature that truncates.*

- `Visual.PointFromScreen` / `PointToScreen` take and return `Point` — two `double`
- They route through Win32 `ClientToScreen` / `ScreenToClient`, which take an integer `POINT`
- The measurement: 4.11° in, 17.51° out, 3014 of 3014 points on whole device pixels
- **Why the obvious check misses it:** `701 / 1.75 = 400.571` — an integer input still produces a decimal readout downstream, so a healthy-looking position display proves nothing
- `WpfCoordinates.GetTransform`, and why its only Win32 call is for the client origin
- **Verify:** `--replay` reports `L3.conversion-lossless` passing

## 3. Trap two: a surface sized in logical units

*Intent: the bug class that survives perfect coordinates.*

- `ActualWidth`/`ActualHeight` are DIPs; a bitmap sized from them is magnified to fit
- At 1.75× that is a canvas drawn at 57% of the display's resolution
- `WriteableBitmap` declared at `96 * scale`, and what goes wrong when declared at 96
- `_skCanvas.Scale(scale)` so drawing code keeps working in DIPs
- **Verify:** `L1.surface-physical`

## 4. Trap three: a surface between pixels

*Intent: the subtlest of the three, and the one that reads as a brush-engine problem.*

- WPF does not round layout to device pixels by default
- A canvas below a text-sized ribbon lands on a fractional pixel; WPF resamples all of it to draw it there
- The real instance: `0.00` horizontally, **`0.64` vertically** — the blur was one-dimensional
- Why a check that scanned across a near-vertical stroke reported it clean
- `UseLayoutRounding` as the fix; `BitmapScalingMode="NearestNeighbor"` as a guard, **not** a fix
- **Verify:** `L1.surface-alignment`

## 5. WPF's own stylus stack

*Intent: a second, independent instance of trap one, in the opposite direction.*

- `GetStylusPoints` returns good sub-pixel DIPs
- `PointToScreen` on the way out destroys them before they leave the session
- Why its resolution still trails a Wintab digitizer context even once correct — 5.32° against 2.69°, which is the stack, not a defect

## 6. Handing it to a person

- Same boundary as everywhere else
- If it looks wrong: [Diagnosing a bad stroke](diagnosing-a-bad-stroke.md)

---

## To write

- [ ] This page carries the most measurements; attribute each to a real run
- [ ] Section 2 is the single most valuable passage in the guide set — it deserves the most care
- [ ] Decide whether to walk the reader into each trap deliberately or warn first. Walking in is more memorable and more annoying; pick one and be consistent
