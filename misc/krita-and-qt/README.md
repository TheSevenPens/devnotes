# Krita & Qt

## Overview

Krita on Windows supports using either WinTab or Windoes Ink

For more detail see:

* &#x20;[Krita pen API implementation notes](krita-pen-api-implementation-notes.md)
* [Qt pen api implementation notes](qt-pen-api-implementation-notes.md)&#x20;

### UX for Switching Pen APIs

(add screenshot)

Changing this setting requires the user to restart the Krita application.

### Qt does all the tablet work for Krita

The KritaUX would make you think that Krita has some specific knowledge about the APIs used. This used to be the case. But in modern version of Krita all the handling for pen input comes from Qt. The primary interface that Krita is interacting with QTabletEvent.

Krita does **not directly implement WinTab or Windows Ink**. Krita delegates all tablet input handling to Qt, and only decides _which backend Qt should use_.

```
[ Tablet Driver ]
       ↓
(WinTab OR Windows Ink / WM_POINTER)
       ↓
[ Qt Windows Platform Plugin ]
       ↓
QTabletEvent
       ↓
[ Krita Application Code ]
```

### Krita versions vs Qt versions

See: [https://krita.org/en/release-notes/krita-5-3-release-notes/](https://krita.org/en/release-notes/krita-5-3-release-notes/)

Krita has been using Qt5 for a long time. In March 2026, Krita started moving toward Qt6.

Krita6 is the first version of Krita that uses Qt6.&#x20;

### QTablet event input backends

On Windows, Qt supports two mutually exclusive tablet input paths:

* WM\_POINTER (the default)
* WinTab

See: [WinTab vs WM\_POINTER](../../pen-input-on-windows/wintab-vs-wm_pointer.md)

To consume tablet data simply use QTabletEvent: See [QTabletEvent](qtabletevent.md) which abstracts away the pen API.

### How Krita’s UI switches between APIs

What happens:

1. **User selects WinTab in Krita UI**
2. Krita saves a config value
3. **User restarts Krita**
4. On startup, Krita reads config and&#x20;
5. Krita configures Qt’s Windows backend based on the config

### Why Krita restart Is required when switching

Qt chooses the tablet backend **during platform plugin initialization** (specifically we are talking about the Windows platform plugin)

Initialization happens **BEFORE QApplication is fully running**.

* Qt cannot hot-swap WinTab ↔ Windows Ink.
* The WM\_POINTER/WinTab decision must be made **at process startup**

### Qt6 vs Qt5

Qt6 is new for Krita (starting in Krita 6.0 in March 2026).&#x20;

The paths are slightly different for Qt6 and Qt6 with krita: See the [Implementation notes](../../implementation-notes/)

### Runtime detection of pen api

Callera such as Krita does **not know** which API is being used at dynamically runtime. They may of course remember how they configured Qt to start.



