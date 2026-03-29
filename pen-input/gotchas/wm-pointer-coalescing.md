# WM_POINTER Event Coalescing

When using `WM_POINTER` for pen input on Windows, the OS may coalesce multiple pointer events into a single message. This causes visible quality loss in drawing applications.

## The Problem

When the UI thread is busy (rendering, GPU texture upload, layout), Windows coalesces multiple `WM_POINTERUPDATE` messages into one. The most recent position is delivered, but intermediate positions are lost.

**Symptoms:** Strokes appear as straight-line segments between widely spaced points — the classic "polygon" appearance instead of smooth curves. This is especially visible in apps with heavier render loops (e.g., egui/wgpu, Electron) and less visible in apps with lightweight message pumps (e.g., raw Win32/GDI).

## The Fix

Use `GetPointerPenInfoHistory` to recover all coalesced events from each message:

```cpp
if (msg == WM_POINTERUPDATE) {
    POINTER_PEN_INFO history[64];
    UINT32 count = 64;
    if (GetPointerPenInfoHistory(pointerId, &count, history) && count > 1) {
        for (int i = count - 1; i >= 0; i--)  // oldest first
            process_point(history[i]);
        return;
    }
}

// Single point (non-coalesced, or DOWN/UP).
POINTER_PEN_INFO pen_info = {};
GetPointerPenInfo(pointerId, &pen_info);
process_point(pen_info);
```

## Critical: `count > 1`, not `count > 0`

When `GetPointerPenInfoHistory` returns `count == 1`, the data may differ from what `GetPointerPenInfo` returns for the same event. Using `count > 0` was found to break WM_POINTER completely in some apps — pen data silently stops arriving. Always fall through to `GetPointerPenInfo` for single events.

## Framework-Specific Sessions Are Not Affected

WinUI 3, WPF, WinForms, and Avalonia decoalesce pointer events internally before delivering them to app event handlers. Their native input stacks handle history recovery transparently. Only raw Win32 `WM_POINTER` subclassing requires explicit history retrieval.

## Wintab Is Not Affected

Wintab delivers packets on a dedicated background thread at 200+ Hz. The UI thread's busyness doesn't affect Wintab's packet delivery rate. This is one of the main reasons production drawing apps (Photoshop, Krita, Clip Studio Paint) prefer Wintab.
