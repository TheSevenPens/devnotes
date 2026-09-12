# Qt pen api implementation notes

## Overview

The key Qt pieces are:

* `QNativeInterface::Private::QWindowsApplication`&#x20;
  * Declares `isWinTabEnabled()`&#x20;
  * calls `setWinTabEnabled(bool)`. ([Code Browser](https://codebrowser.dev/qt6/qtbase/src/gui/kernel/qguiapplication_p.h.html?utm_source=chatgpt.com))
* The Windows platform plugin
  * &#x20;`QWindowsApplication::setWinTabEnabled()` is implemented by asking `QWindowsContext` to either `initTablet()` or `disposeTablet()`.
* `QWindowsContext::initTablet()`&#x20;
  * creates `QWindowsTabletSupport`;
  * `disposeTablet()` destroys it.

For WM\_POINTER:

```
WM_POINTER 
  -> QWindowsPointerHandler
  -> QWindowSystemInterface
  -> QTabletEvent / Qt input events
```

while while for WinTab:

```
WinTab
  -> QWindowsTabletSupport
  -> QWindowSystemInterface
  -> QTabletEvent / Qt input events
```

## WinTab inside Qt

The WinTab implementation lives in:

* `src/plugins/platforms/windows/qwindowstabletsupport.cpp`
* plus the bundled WinTab headers mentioned by Qt’s attribution page: `src/3rdparty/wintab/pktdef.h` and `wintab.h`. ([Qt Documentation](https://doc.qt.io/qt-6/qtgui-attribution-wintab.html?utm_source=chatgpt.com))

What happens:

1. Loads `wintab32.dll`
2. Creates a hidden dummy window
3. Opens a WinTab context with `WTOpenW`
4. Receives `WT_PROXIMITY` and `WT_PACKET`
5. Converts packet data into Qt tablet events via `QWindowSystemInterface::handleTabletEvent(...)`

## Qt always uses the high-resolution (tablet-native) context

This is the single most consequential thing Qt does with WinTab, and it is easy to miss because
there is no setting for it: **Qt configures its WinTab context for tablet-native resolution
unconditionally.** An application built on Qt cannot ask for the low-resolution behaviour, and
one built without Qt does not get the high-resolution behaviour unless it asks.

From `src/plugins/platforms/windows/qwindowstabletsupport.cpp` (checked against the `dev` branch
of qtbase):

```cpp
QWindowsTabletSupport::m_winTab32DLL.wTInfo(WTI_DEFSYSCTX, 0, &lcMine);
lcMine.lcOptions |= CXO_MESSAGES | CXO_CSRMESSAGES;
lcMine.lcOutOrgX = 0;
lcMine.lcOutExtX = lcMine.lcInExtX;
lcMine.lcOutOrgY = 0;
lcMine.lcOutExtY = -lcMine.lcInExtY;
```

Note what this is and is not:

* It is **not** a different context type. Qt starts from `WTI_DEFSYSCTX`, the same system context
  template most code starts from - and the one that is [more reliable than
  `WTI_DEFCONTEXT`](../../pen-input-on-windows/implementation-notes/wintab-gotchas.md).
* The only change is **`lcOutExt` overridden to `lcInExt`** - the tablet's own input extents
  rather than the screen-pixel output range the template arrives with.
* `lcOutExtY` is negated, which is Qt's way of handling the bottom-left tablet origin against the
  top-left screen origin.

So "high-resolution mode" is four assignments on an ordinary context, not an exotic feature.

### Qt maps to the desktop itself, in floating point

Having asked for tablet-native coordinates, Qt has to do the screen mapping that the driver would
otherwise have done. It does it in `qreal`, and returns a `QPointF`:

```cpp
inline QPointF QWindowsTabletDeviceData::scaleCoordinates(int coordX, int coordY,
                                                          const QRect &targetArea) const
{
    const qreal x = /* (coordX - minX) * |targetWidth| / |maxX - minX| + targetX */;
    const qreal y = /* (coordY - minY) * |targetHeight| / |maxY - minY| + targetY */;
    return {x, y};
}
```

The return type is the point. Had Qt mapped through integers, overriding `lcOutExt` would have
bought nothing - the precision would have been discarded one step later.

### What this means for Krita

Krita [delegates all tablet input to Qt](README.md), so Krita inherits this. Consequences worth
stating plainly:

* **Krita's "WinTab" setting is the high-resolution context.** There is no lower-precision WinTab
  mode in Krita, and no preference that selects one.
* Krita's brush smoothing settings are therefore **not** what makes its strokes smooth at the
  pixel level. Krita with smoothing set to **None** - which draws plain straight lines between
  consecutive samples, `paintLine(previousPaintInformation, info)` - still produces clean edges,
  because its input is sub-pixel to begin with.
* Anyone comparing their own application's stroke quality against Krita's is, without knowing it,
  comparing against tablet-native input.

### Why the difference is visible

Screen-pixel output is not a small loss. A typical tablet reports something like 52885 x 29835
units of input extent; mapped to a 7680 x 3600 virtual desktop, that is roughly a **7x reduction**
before the application sees anything.

The symptom is not blur - it is angularity. Measured on one recorded stroke, taking the same
sub-pixel input and quantizing it to whole pixels:

| coordinates | median turn between consecutive segments | p90 | max |
| ----------- | --------------------------------------- | --- | --- |
| sub-pixel (as reported) | 1.50 deg | 5.10 | 9.83 |
| quantized to whole pixels | 11.31 deg | 26.57 | 45.00 |

Those numbers are not arbitrary. A tablet reports steps of roughly 2 px, and a 2 px step on an
integer grid can only point in a handful of directions: 11.31 deg is `atan(1/5)`, and its
neighbours are `atan(1/3)` = 18.43 and 45. The path stops following the pen and starts zigzagging
between the directions available to it. On a constant-width stroke this reads as small periodic
bumps along both edges, worst on diagonals - and because it has nothing to do with pressure, it
survives flattening the pressure curve, which is a useful way to confirm it.

Rounding instead of truncating does not help. The grid is the problem, not the rounding rule.

### Measuring it yourself

Edge roughness measured off a rendered image is a poor diagnostic - a per-column edge position has
a large second difference wherever the stroke runs near-vertical, and that geometry term swamps
the roughness term. Measure the **input path** instead:

1. Capture the raw samples, before any conversion.
2. Compute the unit direction of each segment.
3. Take the angle between consecutive directions.

A smooth hand movement gives a median of a degree or two. Anything near 11 degrees on a device
reporting ~2 px steps means the coordinates have been through an integer somewhere.

### Checklist for a non-Qt application

1. Override `lcOutOrg`/`lcOutExt` to `lcInOrg`/`lcInExt` when opening the context.
2. Cache the system context's `InOrg/InExt -> SysOrg/SysExt` mapping and convert through it -
   see [Wintab
   gotchas](../../pen-input-on-windows/implementation-notes/wintab-gotchas.md), which covers the
   `ScaleAxis` conversion and the Y negation.
3. **Keep the result in floating point all the way to the canvas.** This is the step that is
   easiest to get wrong after doing the hard part correctly: a single conversion through an
   integer screen-coordinate type discards exactly the precision that was just obtained. On
   Windows, watch for API surfaces that take integer point types.

## WM\_POINTER inside Qt

* The Windows event dispatcher path in `qwindowscontext.cpp` includes `qwindowspointerhandler.h`,&#x20;
* Routes `PointerEvent` / `NonClientPointerEvent` to `QWindowsPointerHandler::translatePointerEvent(...)`.&#x20;
* Mouse events go through the same pointer handler’s mouse translation path.
