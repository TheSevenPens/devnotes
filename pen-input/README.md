# Pen Input on Windows

Everything you need to know about receiving pen/stylus input in Windows applications — from raw Wintab packets to framework-specific XAML events.

## APIs

* [Windows Pen API Landscape](apis/windows-pen-api-landscape.md) — Comprehensive comparison of all Windows pen input APIs (Wintab, WM_POINTER, WinUI, WPF, RealTimeStylus)

## Frameworks

* [Framework-Specific Pen Input Routing](frameworks/framework-pen-input-routing.md) — Why WM_POINTER doesn't work in WinUI/WPF/WinForms/Avalonia, and what to use instead
* [Rendering Approaches for Pen Apps](frameworks/rendering-for-pen-apps.md) — Bitmap-backed vs retained mode, SkiaSharp pattern, framework comparison

## Gotchas

* [DPI Awareness and Pen Coordinates](gotchas/dpi-and-pen-coordinates.md) — The #1 source of pen coordinate bugs
* [WM_POINTER Event Coalescing](gotchas/wm-pointer-coalescing.md) — Why strokes look like polygons and how to fix it
* [Wintab Gotchas](gotchas/wintab-gotchas.md) — 12 hard-won lessons from implementing Wintab
