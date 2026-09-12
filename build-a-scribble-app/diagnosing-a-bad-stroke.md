# Diagnosing a bad stroke

> **Status: outline.** Headings and intent only. Tracked in [#8](https://github.com/TheSevenPens/devnotes/issues/8).

Framework-agnostic. The stroke looks wrong — this page decides *which* wrong, before any code is changed.

This is the part of the guide set that is hard to get elsewhere. Building a canvas is well covered by every framework's own documentation; telling a quantized path apart from a magnified surface apart from a resampled one is not.

---

## 1. Run the checks before forming a theory

*Intent: most causes are already machine-detectable. Theorising first wastes the cheapest evidence available.*

- `--selftest` then `--replay`; the first failure is the root cause by construction
- What a clean 9/9 does and does not rule out
- Only continue past this section if everything passes and the stroke still looks wrong

## 2. Name the symptom precisely

*Intent: the four symptoms point at four different causes, and the words are usually used interchangeably.*

| symptom | looks like | usually means |
| --- | --- | --- |
| **bumpy / faceted** | flat segments, small kinks, worst on slow curves | quantized coordinates |
| **blocky** | hard stair-steps at a consistent size | a magnified surface, unfiltered |
| **soft / blurry** | every edge uniformly hazy | a resampled surface |
| **lumpy** | width varies where it should not | the pressure path, not the position path |

*To write: an image for each, from the real bugs.*

## 3. The decision tree

*Intent: the load-bearing section. Each branch ends at a specific check with a specific number, not at a hunch.*

- Is the surface physical-resolution? → `L1.surface-physical`
- Is it on a whole device pixel? → `L1.surface-alignment`
- Do the coordinates arrive sub-pixel? → `L2.recording-subpixel`, and what it cannot tell you
- Does the conversion preserve them? → `L3.conversion-snap`, `L3.conversion-lossless`
- Is it the pressure path instead? → replay with fixed pressure and see if it persists
- Is it the API by construction? → Wintab system mode is quantized by design; switch to the digitizer context

## 4. Measuring by hand, when the flags are not enough

*Intent: for a reader whose app is not a Scribble sample.*

- Turn angle between consecutive segments — the function, and reference values for a lattice (`atan(1/5)` = 11.31°, `atan(1/3)` = 18.43°, `atan(1/1)` = 45°)
- The snap test
- The lossless assertion, and why it needs no threshold: a conversion is a translation and a uniform scale, so it preserves angles exactly

## 5. Measurements that lie

*Intent: hard-won, and the reason this page exists at all. Every entry cost a wrong conclusion.*

| looks like verification | why it is not |
| --- | --- |
| decimals in a scaled readout | `701 / 1.75 = 400.571` — an integer input still produces decimals |
| an image-based roughness metric | dominated by stroke steepness, not quantization; gave a false negative *and* caused a correct hypothesis to be withdrawn |
| scanning across a near-vertical stroke | measures the axis with no error; reported a vertical-only blur as clean |
| a screenshot that looks fine | one apparent reproduction came from an overlapping window and a click below the virtual desktop |
| a readout at `:F0` | cannot represent the quantity being tested |
| a self-test that has only ever passed | not yet a test — inject the bug and confirm it fails |

## 6. What only a person can tell you

*Intent: close the loop honestly.*

- The questions worth asking, and what each answer localizes
- Why "it looks smooth" is not equivalent to "the pipeline is lossless" — and why the second is the one worth asserting

---

## To write

- [ ] Section 2 needs real images. They exist in the investigation history
- [ ] Section 3 should be a diagram, not prose
- [ ] Section 5 is the most reusable thing here and should probably be linked from the implementation notes too
