# Krita & Qt

## Overview

Krita on Windows supports using either WinTab or Windoes Ink

For more detail see:

* &#x20;[Krita pen API implementation notes](krita-pen-api-implementation-notes.md)
* [Qt pen api implementation notes](qt-pen-api-implementation-notes.md)&#x20;

### UX for Switching Pen APIs

(add screenshot)

Changing this setting requires the user to restart the Krita application.

### Krita supports tablets via Qt

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

#### Windows Pointer API (Windows Ink / WM\_POINTER)

* Modern default in Qt 6
* Uses `WM_POINTER*` messages
* Integrated with Windows OS features

#### WinTab API

* Legacy, driver-based API (`wintab32.dll`)
* Preferred for high-end tablets (e.g., Wacom)
* Often provides better pressure/tilt fidelity

### What Krita’s UI Actually Does

When the user selects **WinTab** in:

> _Settings → Configure Krita → Tablet Settings_

Krita does **NOT** switch APIs immediately.

Instead, it follows this pattern:

#### Step-by-step flow

1. **User selects WinTab**
2.  Krita saves a config value:

    ```
    useWin8PointerInput = false
    ```
3. **User restarts Krita**
4.  On startup, Krita reads config and computes:

    ```
    forceWinTab = !useWin8PointerInput
    ```
5.  Krita configures Qt’s Windows backend:

    ```cpp
    qtWindowsBackend->setWinTabEnabled(forceWinTab);
    ```

NOTE: This is why a restart is required.

### Why Restart Is Required

Qt chooses the tablet backend **during platform plugin initialization**.

That happens **BEFORE QApplication is fully running**.

* Qt cannot hot-swap WinTab ↔ Windows Ink.
* The decision must be made **at process startup**

### Qt6 vs Qt5

Qt6 is new for Krita (starting in Krita 6.0 in March 2026).&#x20;

The paths are slightly different for Qt6 and Qt6 with krita: See the [Implementation notes](../../implementation-notes/)

### QTabletEvent unified pen data

Regardless of backend, Qt emits a QTabletEvent.

This unifies:

* Pressure
* Tilt
* Position
* Device type

The caller (such as Krita) does **not know** which API is being used.

