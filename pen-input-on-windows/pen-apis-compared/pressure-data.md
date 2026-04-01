# Pressure Data

## Overview

| API                | Pressure type                        | Range                                                   | Normalization         |
| ------------------ | ------------------------------------ | ------------------------------------------------------- | --------------------- |
| Wintab             | `pkNormalPressure` (uint)            | 0 to device-specific max (query via `GetMaxPressure()`) | App divides by max    |
| WM\_POINTER        | `POINTER_PEN_INFO.pressure` (uint32) | 0 to 1024                                               | App divides by 1024.0 |
| WinUI PointerPoint | `Properties.Pressure` (float)        | 0.0 to 1.0                                              | Pre-normalized        |
| WPF StylusPoint    | `PressureFactor` (float)             | 0.0 to 1.0                                              | Pre-normalized        |
| RealTimeStylus     | `PACKET_PROPERTY.pkNormalPressure`   | Device-specific                                         | App normalizes        |

## Wintab: pkNormalPressure

Note: "Normal" in Wintab's `pkNormalPressure` does **not** mean "normalized." It means **normal force** — the pressure applied perpendicular (normal) to the tablet surface, as opposed to `pkTangentPressure` which measures tangential (sideways) force from an airbrush finger wheel. The value is a raw integer that must be divided by `GetMaxPressure()` to normalize.
