# Wintab Gotchas

Hard-won lessons from implementing Wintab pen input. These are the pitfalls that aren't obvious from the Wintab 1.4 specification.

## 1. CXO_SYSTEM is required for packet delivery

The Wacom driver requires `CXO_SYSTEM` in the context options for `WT_PACKET` messages to be delivered. Without it, `WTOpenA` succeeds and returns a valid context handle — but no packets ever arrive. This is not documented in the Wintab spec.

## 2. Use WTI_DEFSYSCTX, not WTI_DEFCONTEXT

`WTI_DEFCONTEXT` (digitizer context) may not deliver packets on some Wacom driver versions. Always use `WTI_DEFSYSCTX` (system context) as the base for both system and digitizer modes.

## 3. Hidden window must not be HWND_MESSAGE

The Wacom driver doesn't deliver `WT_PACKET` to message-only windows (created with `HWND_MESSAGE` as parent). Use a regular hidden top-level window:

```cpp
// WRONG:
CreateWindowEx(0, cls, L"", 0, 0,0,0,0, HWND_MESSAGE, ...);

// CORRECT:
CreateWindowEx(0, cls, L"", WS_OVERLAPPED, 0,0,0,0, nullptr, ...);
```

## 4. Y-axis is inverted

Wintab tablet origin is bottom-left (Y increases upward). Screen origin is top-left (Y increases downward). Negate `OutExtY` for system mode, or negate `SysExtY` in the mapping cache for digitizer mode.

## 5. Read back context after opening

The Wacom driver may modify context values during `WTOpenA`. Always call `WTGetA` after opening to read back the actual values the driver applied.

## 6. HCTX is pointer-sized

The `pkContext` field in the `PACKET` struct is `HCTX`, which is a `HANDLE` — 8 bytes on x64, 4 bytes on x86. Using a fixed 4-byte type (`uint`, `DWORD`) causes every subsequent field to read from the wrong offset. The data appears correct (you get numbers) but the fields are silently shifted: Y contains X's value, Pressure contains Z's value, etc.

```csharp
// WRONG on x64:
public uint pkContext;    // 4 bytes

// CORRECT:
public IntPtr pkContext;  // 8 bytes on x64, 4 on x86
```

## 7. lcPktData must match your PACKET struct

The default system context may not include all packet fields your `PACKET` struct expects. If `lcPktData` doesn't match your struct layout, the driver writes fields at wrong offsets. Always set it explicitly:

```cpp
lc.lcPktData  = PK_PKTBITS_ALL;  // 0x1FFF
lc.lcPktMode  = 0;
lc.lcMoveMask = PK_PKTBITS_ALL;
```

## 8. Multi-monitor mapping is driver-controlled

Setting `OutExtX/Y` to canvas dimensions breaks on multi-monitor setups. The Wacom driver clips the output range to the mapped monitor's fraction of the virtual desktop. Use the system context output range (screen coordinates) or tablet-native with ScaleAxis conversion.

## 9. Digitizer hi-res: override OutExt to tablet-native

For tablet-native resolution (~5080 LPI vs ~200 DPI screen):
1. Override `OutOrg/OutExt` to `InOrg/InExt` (tablet-native range)
2. Cache the system context's `InOrg/InExt → SysOrg/SysExt` mapping
3. Convert via `ScaleAxis` through the cached mapping
4. Negate `SysExtY` for Y-axis inversion

## 10. Wintab/WM_POINTER driver conflict

Some tablet drivers suppress WM_POINTER pen events once Wintab32.dll is loaded or a Wintab context has been opened. In practice, switching between Wintab and WM_POINTER sessions works when sessions are cleanly stopped/started, but this is driver-dependent.

## 11. Button encoding is relative, not bitmask

Wintab encodes button events as `(action << 16) | buttonNumber`:
- Action: 0=none, 1=released, 2=pressed
- Button: 0=tip, 1=barrel1, 2=barrel2, 3=barrel3

This is NOT a bitmask — you can't AND it to check button state.

## 12. Eraser detection is via cursor type, not buttons

Eraser is detected by cursor type changing from 13 (pen) to 14 (eraser) in `pkCursor`. This happens on hover, before the pen touches the surface. It's not encoded in the button state.
