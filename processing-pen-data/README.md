# Processing pen data

What happens to pen data between reading it from an API and drawing it. None of this is Windows-specific — it applies to any platform, and the reference implementations here happen to be C#.

Two stages, on the two halves of a pen sample:

- **[Pressure Quantization](pressure-quantization.md)** — coarsening pressure to a fixed number of levels, to model what a lower-resolution pen feels like. The rounding rule matters more than the level count.
- **[Position Smoothing](position-smoothing.md)** — interpolation and smoothing of the path, which are different operations addressing different defects. Includes what Krita does, and a measurement showing that on quantized input, mild smoothing is *more* accurate than the raw data.

Both stages are worth keeping distinct from the input layer. A defect that looks like it belongs here is often a coordinate problem upstream — see [Framework Coordinate Conversion](../pen-input-on-windows/implementation-notes/framework-coordinate-conversion.md) before reaching for a filter.
