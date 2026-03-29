# Wintab and Windows Ink Coexistence

Tablet drivers and applications each have their own way of exposing and consuming pen input APIs. Understanding how both sides work is essential when building apps that support multiple input paths.

## How Tablet Drivers Expose APIs

Tablet drivers always support Wintab — this cannot be turned off. Windows Ink (WM_POINTER) support is optional and controlled by a driver setting.

At any given time, a tablet driver is in one of two states:

| Driver setting | APIs available |
|---|---|
| Windows Ink **enabled** (default) | Wintab + Windows Ink (WM_POINTER) |
| Windows Ink **disabled** | Wintab only |

All modern tablet drivers (Wacom, Huion, XP-Pen) default to Windows Ink enabled. The setting is typically exposed as a checkbox labeled "Windows Ink" or "Enable Windows Ink" in the driver's configuration UI.

When Windows Ink is disabled, applications that depend on WM_POINTER or framework pointer events (WinUI PointerMoved, WPF StylusMove, etc.) will not receive pen data. Only Wintab-based input will work.

## How Applications Consume APIs

Applications typically treat the choice as mutually exclusive — they use either Wintab or Windows Ink, not both simultaneously. Most present this as a simple binary setting in their preferences.

Some applications offer more granular choices:

- **Krita** — lets users choose between "Wintab" and "Windows 8+ Pointer Input"
- **Some apps** distinguish between Wintab System context and Wintab Digitizer context (without using that terminology)
- **Advanced apps** may let users pick between WM_POINTER directly or a framework layer built on top of it

In practice, running both Wintab and WM_POINTER simultaneously in the same process is unreliable:

- When a Wintab context is open, some drivers stop delivering WM_POINTER pen events
- When Windows Ink is the active path, the driver may not load `wintab32.dll` or may deliver incomplete Wintab data
- The behavior is driver-dependent and varies across driver versions

## Changing the Driver Setting

The Windows Ink toggle in the tablet driver can be changed at any time without restarting the driver. However, running applications may need to be restarted because they initialized against the previous API state.

## Changing the App Setting

When switching input APIs in an application, a restart is strongly recommended — even for apps that claim it isn't needed. Most applications behave unpredictably if the input API changes mid-session because:

- Driver-level plumbing is set up at process startup
- Framework input stacks (WPF's Wisp, WinUI's composition layer) initialize once
- Cached state (context handles, function pointers, message routing) may become invalid

This is why apps like Krita require a restart when switching between Wintab and Windows Ink.

**Note:** The [WinPenSession](https://github.com/TheSevenPens/WinPenSession) SDK was designed to support runtime API switching without a restart. This works because each session is an independent object with its own lifecycle — stopping one and starting another is a clean operation. However, the underlying driver behavior still applies: if the driver suppresses one API when the other is active, switching may not produce data until the process is restarted.
