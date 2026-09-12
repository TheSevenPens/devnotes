# Pressure Quantization

Quantization coarsens a normalized pressure in `[0, 1]` to a chosen number of levels. It is the cheapest way to model what a lower-resolution pen feels like — an 8192-level pen can be made to behave like a 256-level one, which answers "would this brush still feel good on cheaper hardware?" without owning the cheaper hardware.

It is also easy to implement subtly wrong, and **the choice of rounding rule changes the feel of the brush far more than the level count does.** That is most of what this page is about.

Reference implementation: `Curves/Quantization.cs` in `PenDynamicsLab`.

## Where it belongs in the pipeline

**First** — before smoothing, before any response curve.

Nothing downstream can restore detail that has already been discarded, so it can only be first. Where a pipeline lets the user reorder its stages, this is the one stage that has no configurable order, and it is worth saying so in the UI rather than letting someone discover it.

## The strategy: N equal buckets, reached by ceiling

A level of `N` yields `N + 1` possible outputs — `0, 1/N, 2/N … 1` — where **zero is reachable only when the pen genuinely reports zero**. Above that there are exactly `N` equal-width buckets, each left-open and right-closed.

```csharp
public static double Apply(double x, int levels)
{
    if (levels <= 0) return x;          // passthrough

    x = Math.Clamp(x, 0, 1);
    if (x <= 0) return 0;               // only a real zero maps to zero

    double step = Math.Ceiling(x * levels - Epsilon);
    return Math.Clamp(step, 1, levels) / levels;
}
```

At `N = 4`:

| input pressure | output |
| -------------- | ------ |
| `0`            | `0.00` |
| `(0, 0.25]`    | `0.25` |
| `(0.25, 0.50]` | `0.50` |
| `(0.50, 0.75]` | `0.75` |
| `(0.75, 1.00]` | `1.00` |

```
  output
  1.00 ┤                                    ┌───────────●
       │                                    │            
  0.75 ┤                        ┌───────────●            
       │                        │                        
  0.50 ┤            ┌───────────●                        
       │            │                                    
  0.25 ┤┌───────────●                                    
       ││
  0.00 ●┘
       └┼───────────┼───────────┼───────────┼───────────┼
        0.00      0.25        0.50        0.75        1.00
                          input pressure
```

`●` marks the included endpoint of each bucket. Note the isolated point at the origin: **zero is its own case, not the bottom of the first bucket.** The step up from `0` to `0.25` happens at the very first nonzero input, not a quarter of the way along.

## Why ceiling rather than nearest or floor

All three are defensible in the abstract. Only one behaves well under a pen.

| rule | what it does to the range | consequence |
| ---- | ------------------------- | ----------- |
| **nearest** | the bottom `1/(2N)` of the range maps to zero | at low levels **a light touch makes no mark at all** — the brush has a dead zone that widens as levels drop |
| **floor** | the top bucket is a single point, `x = 1` exactly | **full pressure is unreachable** — you only get `1.0` at the pen's exact maximum, which never happens |
| **ceiling** | `N` equal nonzero buckets | what the level number promises |

Ceiling's cost is real and should be stated rather than hidden: at 4 levels, the lightest possible touch immediately produces 25% pressure. There is no fade-in.

That is the right trade against a dead zone, because of how the two failures *read*. A missing mark reads as broken input — the user presses and nothing happens, and concludes the pen or the app is faulty. An abrupt entry reads as a coarse pen, which is exactly the thing being modelled. One failure mode is a bug; the other is the feature working.

## The floating-point detail that will bite

```csharp
private const double Epsilon = 1e-9;
double step = Math.Ceiling(x * levels - Epsilon);
```

Without the epsilon, a value that should land exactly on a bucket edge but comes out as `3.0000000000000004` instead of `3.0` gets pushed a whole bucket up.

The symptom is nasty precisely because it is rare: quantization that is correct almost everywhere and off by one level at scattered inputs that look arbitrary. It will not reproduce on the values you choose by hand.

At 8192 levels a bucket is `0.0001` wide, so `1e-9` cannot swallow a real one — it is five orders of magnitude below the smallest meaningful difference.

## Suggested level set

```csharp
[0, 8192, 4096, 2048, 1024, 512, 256, 128, 64, 32, 16, 8, 4, 2]
```

The upper end mirrors real tablet pressure resolutions, which is what makes the setting legible: picking 1024 on an 8192-level pen shows what *that pen* would feel like, rather than an abstract number of steps.

The bottom three are below anything real hardware does. They exist because that is where the effect becomes unmistakable on screen — useful for confirming the stage is working at all, and for demonstrating it to someone else.

## Open question: tilt and twist

Whether quantization should apply to tilt and twist as well is unresolved. Those have their own hardware resolutions and the same argument applies.

They are angular, though, and **twist wraps at 360°**. The bucket arithmetic above is not the same function on a circle, and reusing it naively would be wrong at the wrap point — the bucket spanning 359°–0° is not left-open and right-closed in any consistent direction. Anyone implementing this should treat it as a separate problem rather than a parameter change.

## See also

- [Position Smoothing](position-smoothing.md) — the same pipeline, on the path rather than the pressure
