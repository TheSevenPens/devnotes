# How Krita & Qt handles pen input

## Overview

Krita on Windows supports either WinTab or Windows Ink.

For more detail see:

* [Krita pen API implementation notes](krita-pen-api-implementation-notes.md)
* [Qt pen API implementation notes](qt-pen-api-implementation-notes.md)

## UX for Switching Pen APIs

(add screenshot)

Changing this setting requires the user to restart Krita.

## Qt handles all the pen API work for Krita

The Krita UX makes it seem like Krita has specific knowledge about the APIs in use. This used to be the case. But in modern versions of Krita, all pen input handling is done by Qt. Krita just interacts with QTabletEvent.

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

Krita does **not directly implement WinTab or Windows Ink**. Krita delegates all tablet input handling to Qt, and only configures which API to use when the Qt application starts.

One consequence is worth calling out, because it is invisible from Krita's UI: **Qt always opens
its WinTab context at tablet-native (high) resolution**, so Krita's "WinTab" setting is the
high-resolution context and there is no lower-precision option. This is also why Krita's strokes
look clean with brush smoothing set to **None** — the smoothing settings are not what is doing
that work. See [Qt always uses the high-resolution
context](qt-pen-api-implementation-notes.md#qt-always-uses-the-high-resolution-tablet-native-context).

## Krita versions vs Qt versions

See: [https://krita.org/en/release-notes/krita-5-3-release-notes/](https://krita.org/en/release-notes/krita-5-3-release-notes/)

Krita has been using Qt5 for a long time. In March 2026, Krita started moving toward Qt6.

Krita 6 is the first version of Krita that uses Qt6.

## QTabletEvent input backends

On Windows, Qt supports two mutually exclusive tablet input paths:

* WM\_POINTER (the default)
* WinTab

See: [WinTab vs WM\_POINTER](../../pen-input-on-windows/pen-input/wintab-vs-wm_pointer.md)

To consume tablet data, use QTabletEvent. See [QTabletEvent](qtabletevent.md), which abstracts away the pen API.

## How Krita’s UI switches between APIs

What happens:

1. **User selects WinTab in Krita UI**
2. Krita saves a config value
3. **User restarts Krita**
4. On startup, Krita reads the config
5. Krita configures Qt’s Windows backend based on the config

## Why a Krita restart is required when switching

Qt chooses the tablet backend **during platform plugin initialization**. Specifically, this happens in the Windows platform plugin.

Initialization happens **BEFORE QApplication is fully running**.

* Qt cannot hot-swap WinTab ↔ Windows Ink.
* The WM\_POINTER/WinTab decision must be made **at process startup**.

## Qt6 vs Qt5

Qt6 is new for Krita (starting in Krita 6.0 in March 2026).

The paths are slightly different for Qt5 and Qt6 in Krita. See the [Implementation notes](../../pen-input-on-windows/implementation-notes/).

## Runtime detection of pen API

Callers such as Krita do **not know** which API is being used at runtime. They may, of course, remember how they configured Qt to start.
