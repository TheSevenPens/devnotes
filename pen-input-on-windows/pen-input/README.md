# Overview

If you're developing a windows application that deals with pen input the overall choice is an issues you'll need to face are challenging.

In this section I'll try to capture everything I've learned as I've implemented various pen-aware applications.

The motivation for getting this documentation together comes from the challenges I discovered: [Challenges developing pen-aware applications on windows](challenges-developing-pen-aware-applications.md)



## APIs

* [Windows Pen API Landscape](windows-pen-api-landscape.md) — Comprehensive comparison of all Windows pen input APIs (Wintab, WM\_POINTER, WinUI, WPF, RealTimeStylus)

## Frameworks

* [Framework-Specific Pen Input Routing](../implementation-notes/framework-pen-input-routing.md) — Why WM\_POINTER doesn't work in WinUI/WPF/WinForms/Avalonia, and what to use instead
* [Rendering Approaches for Pen Apps](../../rendering-for-pen-apps.md) — Bitmap-backed vs retained mode, SkiaSharp pattern, framework comparison

## Gotchas

* [DPI Awareness and Pen Coordinates](../implementation-notes/dpi-and-pen-coordinates.md) — The #1 source of pen coordinate bugs
* [WM\_POINTER Event Coalescing](../implementation-notes/wm-pointer-coalescing.md) — Why strokes look like polygons and how to fix it
* [Wintab Gotchas](../implementation-notes/wintab-gotchas.md) — 12 hard-won lessons from implementing Wintab

