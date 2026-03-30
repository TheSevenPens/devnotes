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

## WM\_POINTER inside Qt

* The Windows event dispatcher path in `qwindowscontext.cpp` includes `qwindowspointerhandler.h`,&#x20;
* Routes `PointerEvent` / `NonClientPointerEvent` to `QWindowsPointerHandler::translatePointerEvent(...)`.&#x20;
* Mouse events go through the same pointer handler’s mouse translation path.
