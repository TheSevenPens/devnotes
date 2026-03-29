# Rendering Approaches for Pen/Drawing Apps

Choosing the right rendering approach is critical for drawing application performance. This article compares options across Windows UI frameworks.

## The Key Decision: Retained vs Bitmap-Backed

**Retained mode** (XAML Line elements, SVG paths): Each stroke segment becomes an object in the framework's visual tree. Simple to implement, but performance degrades as stroke count grows — layout and rendering slow down with thousands of elements.

**Bitmap-backed** (draw to an offscreen buffer, display as image): Strokes are rasterized directly to a pixel buffer. Performance is constant regardless of stroke count. This is what production drawing apps use.

## Bitmap-Backed Rendering Options

| Renderer | Type | Frameworks | Binary size | Notes |
|---|---|---|---|---|
| **SkiaSharp** | CPU (can use GPU) | .NET (WinUI, WPF, WinForms, Avalonia) | ~8 MB | Cross-platform, consistent. The practical default for .NET drawing apps. |
| **tiny-skia** | CPU only | Rust | ~200 KB | Pure Rust, no C/C++ deps. Subset of Skia's CPU path. |
| **Win2D** | GPU | WinUI 3 | ~3 MB | Microsoft's Direct2D wrapper. GPU-accelerated but WinUI-only. |
| **GDI** | CPU | Win32 | 0 (built-in) | Fast for simple strokes. No anti-aliasing without GDI+. |
| **Direct2D** | GPU | Win32, WPF (via D3DImage) | 0 (built-in) | Best performance. More setup complexity. |
| **Blend2D** | CPU (SIMD) | C/C++ | ~1-2 MB | SIMD-optimized, often faster than Skia's CPU path. |

## The SkiaSharp Pattern (Recommended for .NET)

All managed drawing apps can use the same rendering approach:

1. `SKBitmap` — create at canvas pixel dimensions
2. `SKCanvas.DrawLine()` — draw stroke segments with round caps and anti-aliasing
3. Pixel-copy to framework's `WriteableBitmap`
4. Display via `Image` control

The pixel-copy step varies by framework:

| Framework | Copy method |
|---|---|
| WinUI 3 | `IBuffer.AsStream()` (from `System.Runtime.InteropServices.WindowsRuntime`) |
| WPF | `Buffer.MemoryCopy` to `WriteableBitmap.BackBuffer` |
| WinForms | `Buffer.MemoryCopy` via `Bitmap.LockBits` |
| Avalonia | `Buffer.MemoryCopy` to `WriteableBitmap.Lock()` framebuffer |

### WinUI 3 IBuffer Note

In WinUI 3 with CsWinRT 2.x (.NET 10 + Windows App SDK 1.7+), the old `[ComImport]`-based `IBufferByteAccess` COM pattern does not work — CsWinRT projects WinRT objects as `IInspectable` and don't support legacy QueryInterface casts. Use `IBuffer.AsStream()` instead.

## Performance Comparison

From testing across frameworks:

| App | Renderer | Smoothness |
|---|---|---|
| Win32/GDI (BitBlt) | GDI | Smoothest — direct blit, no framework overhead |
| WinUI 3 (SkiaSharp) | SKBitmap → WriteableBitmap | Smooth |
| Avalonia (SkiaSharp) | SKBitmap → WriteableBitmap | Smooth |
| WinForms (SkiaSharp) | SKBitmap → Bitmap | Smooth |
| WPF (SkiaSharp) | SKBitmap → WriteableBitmap | Slight stutter |
| egui/Rust (tiny-skia) | Pixmap → egui texture | Smooth |

WPF has the most rendering overhead due to its compositor layer between the WriteableBitmap and the display.

## Further Optimization Options

- **Dirty-region copying** — only copy the bounding box of new strokes to the WriteableBitmap
- **SkiaSharp native controls** — `SKElement` (WPF) or `SKXamlCanvas` (WinUI) bypass WriteableBitmap entirely
- **`CompositionTarget.Rendering`** (WPF) — frame-synchronized timer instead of `DispatcherTimer`
- **Direct2D interop** (WPF) — GPU-accelerated via `D3DImage`, no pixel copying
