# WM\_POINTER Event Coalescing

## WM\_POINTER Event Coalescing

When the UI thread is busy (rendering, layout, GPU texture upload), Windows coalesces multiple `WM_POINTERUPDATE` messages into a single message. The most recent position is delivered normally, but intermediate positions are lost unless the app explicitly requests them via `GetPointerPenInfoHistory`.

**Symptoms:** Strokes appear as straight-line segments between widely spaced points — the classic "polygon" appearance instead of smooth curves. This is especially visible in apps with heavier render loops (e.g., egui/wgpu in Scribble.Rust) and less visible in apps with lightweight message pumps (e.g., GDI in Scribble.Win32).

**The fix:** Use `GetPointerPenInfoHistory` to recover coalesced events, but **only when `count > 1`** (actual coalescing occurred). For single events, use the normal `GetPointerPenInfo` path. The history API returns subtly different data for `count == 1` on some driver/OS combinations, causing silent data loss.

```cpp
// Only use history for WM_POINTERUPDATE with actual coalescing.
if (msg == WM_POINTERUPDATE) {
    POINTER_PEN_INFO history[64];
    UINT32 count = 64;
    if (GetPointerPenInfoHistory(pointerId, &count, history) && count > 1) {
        for (int i = count - 1; i >= 0; i--)  // oldest first
            process_point(history[i]);
        return;
    }
}

// Single point (most common case, DOWN/UP, or non-coalesced UPDATE).
POINTER_PEN_INFO pen_info = {};
GetPointerPenInfo(pointerId, &pen_info);
process_point(pen_info);
```

**Critical: `count > 1`, not `count > 0`.** This was discovered through debugging — using `count > 0` caused Scribble.Win32 to silently lose all WM\_POINTER data. The `count == 1` case from history differs from `GetPointerPenInfo` in ways that break the data path. Always fall through to `GetPointerPenInfo` for single events.

**PenSession's WmPointerSession handles this automatically.** The C++ implementation uses `GetPointerPenInfoHistory` for coalesced events with a fallback to single-point `GetPointerPenInfo`.

**Why managed framework sessions aren't affected:** WinUI 3, WPF, and Avalonia decoalesce pointer events internally before delivering them to app event handlers. Their native input stacks (XAML composition layer, Wisp/RTS, Avalonia's pointer system) handle history recovery transparently. Only raw Win32 `WM_POINTER` subclassing requires explicit history retrieval.
