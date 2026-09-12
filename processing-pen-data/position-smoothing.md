# Position Smoothing

Smoothing the **path** a pen draws, as distinct from smoothing its pressure. The trade-off is always the same one — lag against smoothness — and the options are more varied than "add an EMA".

## Interpolation and smoothing are different operations

This is the framing most discussions get wrong, and getting it right determines which tool you reach for.

| | what it does | what it costs | what it fixes |
| --- | --- | --- | --- |
| **Interpolation** | passes exactly through the input points, curving between them | no displacement; at most one sample of lag to compute a tangent | **faceting** |
| **Smoothing** | moves the points | displacement, and usually lag | **jitter** |

They address different defects, and they compose. Krita ships both.

The practical consequence, measured below: interpolation barely improves *accuracy*, because it passes through the same wrong points. Averaging barely improves *faceting*. Reaching for one when you needed the other produces a change that looks like it did nothing.

## What Krita does

Krita's freehand tool has four modes (`SmoothingType` in `kis_smoothing_options.h`, plus `PIXEL_PERFECT`). The default is **`SIMPLE_SMOOTHING`** — `KisConfig::lineSmoothingType` returns `1` when unconfigured, and the enum starts at `NO_SMOOTHING = 0`. Krita does *not* ship with smoothing off.

### 1. `NO_SMOOTHING` — straight lines

```cpp
paintLine(previousPaintInformation, info);
```

Each sample joined to the last with a straight segment.

Worth knowing that this still looks good in Krita, because Qt feeds it sub-pixel coordinates from a tablet-native WinTab context — see [Qt pen api implementation notes](../misc/krita-and-qt/qt-pen-api-implementation-notes.md). Faceting only becomes visible when the samples are sparse or **quantized**, which is the situation a screen-coordinate API puts you in. If straight lines look bad in your app and fine in Krita, suspect your coordinates before your renderer.

### 2. `SIMPLE_SMOOTHING` (UI: "Basic") — Bezier interpolation, the default

Computes a tangent from the sample velocity, then paints a Bezier segment rather than a line:

```cpp
previousTangent = (info.pos() - previousPaintInformation.pos())
                / max(1.0, info.currentTime() - previousPaintInformation.currentTime());

paintBezierSegment(olderPaintInformation, previousPaintInformation,
                   previousTangent, newTangent);
```

It paints the segment between the **older** and **previous** points — one sample behind, because the tangent at `previous` needs `current` to exist.

```
                       needs this point
                              ↓
   o————————o————————o————————o
   older  previous  current
     └────────┘
     paints this segment, curved using tangents at both ends
```

That one sample is the entire latency cost. There is **no positional displacement at all** — the curve still passes through every input point. For a default, that is a very good trade, and it is why this is Krita's default rather than any of the averaging modes.

### 3. `WEIGHTED_SMOOTHING` — Gaussian over a distance window

A weighted average over recent points, with the weight falling off as a Gaussian in **accumulated distance** rather than in sample count:

```cpp
weight = gaussianWeight * exp(-distanceSum * distanceSum / (2 * gaussianWeight2))
```

Two details worth stealing:

**The window is speed-dependent, and inverted from the naive instinct.**

```cpp
smoothness = (1 - speed) * smoothnessDistanceMax + speed * smoothnessDistanceMin
```

Fast strokes get *less* smoothing, slow ones more. That is correct: slow strokes are where hand tremor dominates and where lag is imperceptible; fast strokes are where lag is felt and where tremor is irrelevant.

**The quoted distance is the visible window, not a raw sigma.** The distance is divided by 3 to make it a three-sigma range, so a "smoothness distance" of 30px means the window visibly extends about 30px — which is what a user adjusting the slider expects it to mean.

It also tapers at stroke end: `pressureGrad *= tailAggressiveness * (1.0 - nextInfo.pressure())`.

### 4. `STABILIZER` — uniform average over a queue, with a dead zone

```cpp
sampleSize = max(3, round(effectiveSmoothnessDistance(drawingSpeed)));
newInfo = getStabilizedPaintInfo(stabilizerDeque, sampledInfo);   // uniform mean
```

The queue is **pre-filled with copies of the first sample**, so the stroke does not start displaced — otherwise the average would drag the first several points toward wherever the queue happened to be initialized.

The optional **delay** is a dead zone of radius `R` around the last painted position:

```cpp
if (!(dx > R)) { canPaint = false; }
```

Below `R`, nothing is painted at all. This produces the visible "the line catches up to the cursor" behaviour. It is a *feature* for inking — it makes slow deliberate curves come out clean — and it is the mode to reach for when the user is tracing rather than sketching.

## Other techniques

### Centred moving average

A symmetric window, which makes it **zero-lag in position** at the cost of needing `n/2` future samples.

```
filtered[i] = mean(raw[i - n/2 .. i + n/2])
```

If you can afford two samples of lookahead, this dominates EMA on both axes at once — see the table below, where a centred 5-sample average was more than twice as accurate as raw input while displacing the path by 0.13px, and the same smoothness from an EMA cost 5.6px of displacement.

### EMA and the one-euro filter

```
filtered = filtered + (raw - filtered) * (1 - alpha)
```

Causal, so no lookahead is required — but **it can only smooth by falling behind**, and the lag scales with the strength. There is no setting at which it is both smooth and prompt.

The [one-euro filter](https://gery.casiez.net/1euro/) is the refinement worth knowing: adapt `alpha` to speed, so it smooths hard when slow and tracks tightly when fast. Same instinct as Krita's speed-dependent window, different mechanism.

### Catmull-Rom, and why centripetal

Interpolation through the points, like Krita's Bezier mode but with a standard parameterisation.

**Centripetal** is the variant to recommend. Uniform Catmull-Rom produces cusps and self-intersections when samples bunch up — and a stationary pen bunches samples constantly, since the tablet keeps reporting while the hand rests. The failure is not an edge case; it is what happens every time someone pauses mid-stroke.

### Curve fitting: Ramer-Douglas-Peucker, then fit

Simplify the polyline to a tolerance, then fit Beziers to the survivors. Used for vector output and "pixel perfect" style modes.

Higher latency, and a different goal: it produces the *smallest description* of the stroke rather than the most faithful one. Worth being explicit about that when choosing it, because those two goals diverge.

### Predictive / negative-lag

Extrapolate ahead to hide latency, then correct.

Mostly worth a warning. Overshoot at direction changes is very visible, and the correction is itself a visible artefact — the line reaches past the corner and then snaps back. Hiding latency this way trades a defect users tolerate for one they notice.

## The result that should change your defaults

**On quantized input, mild smoothing is more accurate than the raw data, not less.**

Taking a sub-pixel hi-res stroke as ground truth, quantizing it to the pixel grid to simulate a screen-coordinate API, then measuring how far each treatment lands from where the pen actually was:

| treatment | RMS error | p95 | max |
| --------- | --------- | --- | --- |
| quantized, drawn raw | 0.279 px | 0.502 | 0.678 |
| + Catmull-Rom interpolation | 0.251 px | 0.467 | 0.678 |
| + moving average 3 | 0.160 px | 0.314 | 0.452 |
| **+ moving average 5** | **0.130 px** | 0.248 | 0.452 |
| + EMA 0.5 | 0.165 px | 0.313 | 0.555 |

Quantization error is zero-mean noise, and averaging cancels noise. Drawing the raw quantized points **preserves an error you could have removed.**

This cuts against the usual instinct that smoothing is a distortion you accept in exchange for a smoother look. On quantized input it is not a trade at all — you get both.

Two corollaries:

- **Interpolation barely improves accuracy** (0.279 → 0.251) because it passes through the same wrong points, and **averaging barely improves faceting**. Two different defects, two different tools. Applying the wrong one looks like applying nothing.
- **The precondition matters.** On genuinely sub-pixel input there is nothing to recover, and no smoothing is warranted *for accuracy* — only for taste. Which means the right default depends on which API you are reading from, not on user preference alone.

## Guidance

**Default to interpolation, not averaging.** One sample of lag, no displacement, fixes the defect most people are actually looking at. This is Krita's choice and it is the right one.

**Make the strength speed-dependent if you expose averaging at all.** More smoothing when slow, less when fast — Krita's weighting or a one-euro filter. A fixed strength is wrong at one end of the speed range or the other.

**Prefer a centred window over an EMA when you can afford lookahead.** It wins on both accuracy and displacement; the EMA's only advantage is needing no future samples.

**Consider smoothing harder on quantized input than on sub-pixel input** — and know which one you have. If you are reading screen coordinates from a system-coordinate API, averaging is recovering real information. If you have a digitizer context delivering sub-pixel positions, it is only taste.

**Fix the coordinates first.** Smoothing to recover quantization error is worth doing when quantization is unavoidable. It is a poor substitute for not quantizing in the first place — and quantization is often being introduced by the application itself, in a coordinate conversion, rather than by the API. See [Framework Coordinate Conversion](../pen-input-on-windows/implementation-notes/framework-coordinate-conversion.md).

## See also

- [Pressure Quantization](pressure-quantization.md) — the same pipeline, on pressure rather than the path
- [Krita pen api implementation notes](../misc/krita-and-qt/krita-pen-api-implementation-notes.md)
- [Latency implications](../pen-input-on-windows/implementation-notes/latency-implications.md)
