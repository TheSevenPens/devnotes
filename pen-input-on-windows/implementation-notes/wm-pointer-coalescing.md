# WM\_POINTER Event Coalescing

Windows may coelesce WM\_POINTER events into a single message and thus produce visible quality loss in drawing apps.&#x20;

## The Problem

When the UI thread is busy (rendering, layout, etc.), Windows coalesces multiple `WM_POINTERUPDATE` messages into one. The most recent position is delivered and intermediate positions are lost.

**Symptoms:** Strokes appear as straight-line segments between widely spaced points — the classic "polygon" appearance instead of smooth curves. This is often in apps with heavier render loops (e.g., Electron) and less visible in apps with lightweight message pumps (e.g., raw Win32/GDI).

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

## Important usage note: `count > 1`, not `count > 0`&#x20;

When `GetPointerPenInfoHistory` returns `count == 1`, the data may differ from what `GetPointerPenInfo` returns for the same event.&#x20;

What I found: Using `count > 0` could break WM\_POINTER completely in some apps — pen data silently stops arriving. Always fall through to `GetPointerPenInfo` for single events.

This was discovered through debugging: using `count > 0` caused a Win32 scribble app to silently lose all WM\_POINTER data. The `count == 1` history path consumed events without producing usable output. The fix is simple but the failure mode is silent — no errors, just no data.

## Some UI frameworks handle it automatically

WinUI 3, WPF, WinForms, and Avalonia decoalesce pointer events internally before delivering them to app event handlers. Only raw Win32 `WM_POINTER` subclassing requires explicit history retrieval.

## Wintab Is Not Affected

This coelescing does NOT affect WinTab.

Wintab delivers packets on a dedicated background thread at 200+ Hz. The UI thread's busyness doesn't affect Wintab's packet delivery rate. This is one of the main reasons production drawing apps (Photoshop, Krita, Clip Studio Paint) prefer Wintab.
