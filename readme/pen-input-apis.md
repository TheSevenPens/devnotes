# Pen input APIs

## **Windows**

* Basically this comes down to two choices:
  * WinTab
  * WM\_POINTER
* See [Pen Input on Windows](pen-input-apis.md) for more details.

## Linux

* GTK - [GdkDevice](https://developer.gnome.org/gdk3/stable/GdkDevice.html#gdk-device-get-axis-value)
* Qt - [QTabletEvent](https://doc.qt.io/qt-5/qtabletevent.html)

## macOS

* [NSEvent](https://developer.apple.com/documentation/appkit/nsevent/1534543-pressure?language=objc)
* [PencilKit](https://developer.apple.com/documentation/pencilkit/pkstrokepoint)

## Web

* [PointerEvent](https://developer.mozilla.org/en-US/docs/Web/API/PointerEvent)
* [HID Explorer](https://nondebug.github.io/webhid-explorer/)
