# Stage 6: Values: pressure, tilt, buttons and eraser

This stage turns everything except position into numbers with one meaning: pressure on one scale, tilt in one unit and both representations, buttons as held or not held, and the eraser as a yes or no. When it is done badly, stroke width bulges and pinches (the **Lumpy** symptom), a brush tilts the wrong way or by the wrong amount, a barrel button lights up for every tip stroke, or the eraser end draws ink.

## In short

- Normalize pressure by dividing by `session.MaxPressure`, and treat that maximum as a range, not as the number of levels the pen resolves.
- Divide Wintab azimuth, altitude and twist by 10 to get degrees; WinPenKit's `PenPoint` already holds degrees, with both tilt representations filled.
- On Wintab, `pkButtons` in relative mode is one press or release event per packet, so keep button state between packets with `PenButtonTracker`.
- Wintab cursor numbers are assigned by the device (14 is the eraser on the Wacom devices observed), so do not hard-code them for other vendors.
- Check `PenCapabilities` before reading `Z` or `Status`, which only Wintab fills. `IsInProximity` is true on every point the pointer backends deliver; only Wintab reports a point with it false, when the pen leaves.
- Every backend sets the `Twist` flag, and a pen without a rotation sensor reports 0 on every backend.

## The problem

Every API reports these values in its own type, range and encoding, and several of them report a number whose meaning you cannot tell from the number alone. A Wintab maximum pressure of 32767 is a range, not a level count. A Wintab `pkButtons` value is an event, not a state. A Wintab cursor number of 14 means "eraser" only on the devices where it was observed. A pointer backend's `Status` of 0 means "not reported", not "out of range".

## How the APIs differ here

### Pressure

| API | Field | Type | Range | Normalization |
| --- | --- | --- | --- | --- |
| Wintab | `pkNormalPressure` | `uint` | 0 to the device maximum, `WTInfoA(WTI_DEVICES, DVC_NPRESSURE).axMax` | divide by that maximum |
| WM\_POINTER | `POINTER_PEN_INFO.pressure`, valid when `penMask` has `PEN_MASK_PRESSURE` | `UINT32` | 0 to 1024 | divide by 1024.0 |
| WinUI 3 | `PointerPointProperties.Pressure` | `float` | 0.0 to 1.0 | already normalized |
| WPF | `StylusPoint.PressureFactor` | `float` | 0.0 to 1.0 | already normalized |
| Avalonia | `PointerPointProperties.Pressure` | `float` | 0.0 to 1.0 | already normalized |
| RealTimeStylus | normal pressure packet property | device-specific | device-specific | divide by the property's maximum |

0 always means no pressure. "Normal" in `pkNormalPressure` means the force perpendicular to the surface, not normalized; Wintab's tangential pressure is the barrel pressure covered below.

**The maximum is a range, not a level count.** A Wacom DTH246 over Wintab reports a maximum of 32767 and resolves 8192 levels, in steps of 4. Measured twice on different code paths: 99.8% of the gaps between consecutive distinct pressures are multiples of 4 in WinPenKit's `testdata/wintab-digitizer-stroke-1.75x.csv` (managed, Avalonia sample), and 99.7% in `testdata/winuinative-wintab-hires-stroke.csv` (native C ABI, 1683 points), where the smallest step is exactly 4. No driver declares granularity: Wintab's `AXIS` has `axUnits` and `axResolution`, and for `DVC_NPRESSURE` the driver returns `TU_NONE` and 0 while filling both for X and Y. Granularity can only be observed from a captured stream.

**Pre-normalized pressure removes the device range.** A device with 8192 levels and one with 2048 both become 0.0 to 1.0, and WM\_POINTER's integer field can carry at most 1025 distinct values whatever the device resolves. If you need to model a coarser pen, see [Pressure quantization](../../processing-pen-data/pressure-quantization.md).

### Tilt and twist

Tilt has two equivalent representations:

* **Spherical:** azimuth (compass direction of the lean) and altitude (angle above the surface).
* **Cartesian:** TiltX and TiltY (lean along each axis).

| API | Native tilt | Units | Twist |
| --- | --- | --- | --- |
| Wintab | `orAzimuth`, `orAltitude` | tenths of a degree (0 to 3600, 0 to 900) | `orTwist`, 0 to 3600 tenths |
| WM\_POINTER | `tiltX`, `tiltY` | whole degrees, -90 to +90 | `rotation`, 0 to 359 whole degrees |
| WinUI 3 | `XTilt`, `YTilt` | degrees, `float` | `Twist` |
| WPF | `XTiltOrientation`, `YTiltOrientation` stylus point properties | WinPenKit assumes hundredths of a degree (-9000 to +9000) | `TwistOrientation` when the device reports it; WinPenKit assumes hundredths |
| Avalonia | `XTilt`, `YTilt` | degrees, `float` | `Twist` |
| RealTimeStylus | azimuth, altitude, X and Y tilt, and twist exist as packet properties | as the device reports them | twist packet property |

The two representations convert into each other exactly, so neither carries more information. Precision differs by the units of the source: Wintab's tenths of a degree are ten times finer than WM\_POINTER's whole degrees. An earlier note that X/Y tilt is "less precise than azimuth/altitude" for calligraphy and airbrush brushes describes the units, not the representation. For a drawing app, azimuth and altitude are usually easier to use, because they map to how a person describes a tilted brush.

| Value | Meaning | Range |
| --- | --- | --- |
| Azimuth | compass direction of the lean, clockwise from north (positive Y) | 0 to 360 |
| Altitude | angle above the surface; 90 is upright | 0 to 90 |
| TiltX | lean along X (left and right) | -90 to +90 |
| TiltY | lean along Y (forward and back) | -90 to +90 |

Wintab's values are in tenths: divide by 10.0 before converting. Tablet specifications typically give a tilt range of 60 degrees; readings of about 64 degrees have been seen in practice. The Wintab specification defines `orAltitude` as a signed angle, with negative values below the tablet plane. Whether a device reports negative altitude for the eraser end has not been recorded here; WinPenKit passes the value through unclamped.

The exact conversion, in degrees:

```csharp
public static class PenTiltConversion
{
    // Azimuth 0..360 clockwise from +Y, altitude 0..90 -> TiltX, TiltY in -90..+90.
    public static (double TiltX, double TiltY) AzimuthAltitudeToTiltXY(
        double azimuthDeg, double altitudeDeg)
    {
        double azRad = azimuthDeg * Math.PI / 180.0;
        double altRad = altitudeDeg * Math.PI / 180.0;
        // sin(azimuth) is the X component, cos(azimuth) the Y component.
        // The zenith angle is 90 - altitude, and tan(zenith) = 1 / tan(altitude).
        double tiltX = Math.Atan(Math.Sin(azRad) / Math.Tan(altRad)) * 180.0 / Math.PI;
        double tiltY = Math.Atan(Math.Cos(azRad) / Math.Tan(altRad)) * 180.0 / Math.PI;
        return (tiltX, tiltY);
    }

    // TiltX, TiltY in -90..+90 -> azimuth 0..360 clockwise from +Y, altitude 0..90.
    public static (double Azimuth, double Altitude) TiltXYToAzimuthAltitude(
        double tiltXDeg, double tiltYDeg)
    {
        double tanTx = Math.Tan(tiltXDeg * Math.PI / 180.0);
        double tanTy = Math.Tan(tiltYDeg * Math.PI / 180.0);
        // tan(zenith) = sqrt(tan(tiltX)^2 + tan(tiltY)^2); altitude = 90 - zenith.
        double zenithRad = Math.Atan(Math.Sqrt(tanTx * tanTx + tanTy * tanTy));
        double altitudeDeg = 90.0 - zenithRad * 180.0 / Math.PI;
        // atan2(sin(az), cos(az)) = atan2(tanTx, tanTy)
        double azimuthDeg = Math.Atan2(tanTx, tanTy) * 180.0 / Math.PI;
        if (azimuthDeg < 0) azimuthDeg += 360.0;
        return (azimuthDeg, altitudeDeg);
    }
}
```

The code above takes positive TiltX in the direction of azimuth 90. WinPenKit's [`PenTilt`](https://github.com/TheSevenPens/WinPenKit/blob/main/WinPenKit/PenTilt.cs) uses the same exact relation with TiltX negated: `tan(TiltX) = -tan(θ)·sin(azimuth)` and `tan(TiltY) = tan(θ)·cos(azimuth)`, where θ = 90 − altitude. Call `PenTilt.ToPlanar(azimuth, altitude)` and `PenTilt.ToSpherical(tiltX, tiltY)` to convert in WinPenKit's convention.

Edge cases:

* **Pen upright** (altitude 90, or TiltX = TiltY = 0): azimuth is undefined and any value is valid. The code above returns 0. `PenTilt.ToSpherical` returns 0 whenever the pen is within `PenTilt.UprightThreshold` (0.5 degrees) of vertical, because the direction of a nearly upright pen is mostly sensor noise.
* **Pen flat** (altitude 0): `tan(0)` is 0, so the first function divides by zero. Hardware does not report exactly 0, but guard small altitudes. `PenTilt` uses `atan2` and does not divide by zero.

Twist (rotation around the pen's long axis) needs both a tablet and a pen with a rotation sensor, such as the Wacom Art Pen. Most pens and most consumer tablets do not report it.

{% embed url="https://www.youtube.com/watch?v=O9cMFehZnsI" %}

### Buttons

| API | Encoding |
| --- | --- |
| Wintab | `pkButtons`. In relative button mode (`PK_BUTTONS` set in `lcPktMode`), one event per packet: `(action << 16) \| buttonNumber`, action 0 none, 1 released, 2 pressed; button 0 tip, 1 to 3 barrel. In absolute mode it is a state bitmask. |
| WM\_POINTER | `POINTER_PEN_INFO.penFlags`: `PEN_FLAG_BARREL`, `PEN_FLAG_INVERTED`, `PEN_FLAG_ERASER` |
| WinUI 3, Avalonia | `PointerPointProperties.IsBarrelButtonPressed` |
| WPF | `StylusDevice.StylusButtons`, which includes the tip switch |
| RealTimeStylus | button packet properties |

The two statements in earlier notes ("`pkButtons` bitmask" and "not a bitmask") describe the two Wintab modes. Which one you get depends on `lcPktMode`. The pointer APIs report one barrel flag, so a second or third side switch cannot be told from the first. Which physical switch is barrel 1, 2 or 3 depends on the pen model and the driver's button settings.

### Eraser

| API | How the eraser is reported |
| --- | --- |
| Wintab | `pkCursor` changes when the pen enters proximity, so the eraser is known while hovering, before contact. The number is assigned by the device: 13 (pen) and 14 (eraser) are observed values on Wacom, not a standard. The specification also defines a `TPS_INVERT` bit in `pkStatus`; WinPenKit does not read it. |
| WM\_POINTER | `PEN_FLAG_INVERTED` (eraser end toward the surface) and `PEN_FLAG_ERASER`, per message |
| WinUI 3, Avalonia | `PointerPointProperties.IsEraser` |
| WPF | `StylusEventArgs.Inverted` (also `StylusDevice.Inverted`) |
| RealTimeStylus | the cursor (stylus) identity |

### Barrel pressure and Z

| API | Barrel (tangential) pressure | Z (hover height) |
| --- | --- | --- |
| Wintab | `pkTangentPressure` | `pkZ` |
| WM\_POINTER | not available | not available |
| WinUI 3, WPF, Avalonia | not exposed as named properties read by WinPenKit | not read by WinPenKit |
| RealTimeStylus | packet property | packet property |

So "only Wintab has barrel pressure and Z" is true among the APIs WinPenKit implements, not among all Windows APIs: RealTimeStylus exposes both when the device reports them.

### Hover and proximity

| API | Proximity signal | Hover data |
| --- | --- | --- |
| Wintab | `WT_PROXIMITY` message; `TPS_PROXIMITY` bit in `pkStatus`, which the specification sets when the cursor is **out** of the context | full packets while hovering: position, tilt, buttons, cursor type; packets stop when the pen leaves range |
| WM\_POINTER | `IS_POINTER_INRANGE_WPARAM`; `WM_POINTERLEAVE` when the pen leaves range | `WM_POINTERUPDATE` with in-range but not in-contact |
| WinUI 3 | `PointerEntered`, `PointerExited`; `IsInContact` separates hover from contact | position, tilt, pressure 0 |
| WPF | `StylusInAirMove`; `StylusDevice.InAir` | position and tilt; less data than contact events |
| RealTimeStylus | `IStylusPlugin::InAirPackets` | position and tilt, through a separate callback |

## How WinPenKit handles it

[`PenPoint`](https://github.com/TheSevenPens/WinPenKit/blob/main/WinPenKit/PenPoint.cs) carries `Pressure` (`uint`), `Azimuth`, `Altitude`, `Twist`, `TiltX`, `TiltY` (all `double`, degrees), `Z` (`int`), `Status`, `Buttons` and `Cursor` (`uint`). Two properties on the session say how to read them: [`PenCapabilities`](https://github.com/TheSevenPens/WinPenKit/blob/main/WinPenKit/PenCapabilities.cs) answers "supported or not", and [`PenConventions`](https://github.com/TheSevenPens/WinPenKit/blob/main/WinPenKit/PenConventions.cs) answers "which encoding".

**Pressure.** `IPenSession.MaxPressure` names the scale; normalize with `(float)pt.Pressure / session.MaxPressure`. The Wintab sessions query it in [WintabSessionBase.cs](https://github.com/TheSevenPens/WinPenKit/blob/main/WinPenKit/Wintab/WintabSessionBase.cs) (`QueryMaxPressure`, from `DVC_NPRESSURE` `axMax`) and pass `pkNormalPressure` through. WM\_POINTER and WinForms report 1024 and pass `pressure` through, or 0 when `PEN_MASK_PRESSURE` is clear. WPF, WinUI and Avalonia report 1024 and compute `(uint)(pressure * 1024f)`, which truncates. Any finer resolution in those frameworks' `float` is reduced to 1025 steps; whether WPF's `PressureFactor` carries more than that on a given device has not been measured.

**Tilt.** Both representations are on every point, in degrees. Wintab divides `orAzimuth`, `orAltitude` and `orTwist` by 10 and computes TiltX and TiltY with `PenTilt.ToPlanar`. The pointer backends ([WmPointerSession.cs](https://github.com/TheSevenPens/WinPenKit/blob/main/WinPenKit/Pointer/WmPointerSession.cs) and the framework sessions) compute azimuth and altitude with `PenTilt.ToSpherical`, which returns azimuth 0 to 360 and altitude 0 to 90, with azimuth set to 0 within 0.5 degrees of vertical. The native DLL uses the same relation in `src/tilt.h`. [WpfStylusSession.cs](https://github.com/TheSevenPens/WinPenKit/blob/main/WinPenKit.Wpf/WpfStylusSession.cs) divides the WPF properties by 100.

Both directions use the exact relation from [PenTilt.cs](https://github.com/TheSevenPens/WinPenKit/blob/main/WinPenKit/PenTilt.cs), so values round-trip within WinPenKit. Earlier versions used the linear form `TiltX = -(90 - altitude) * sin(azimuth)`, `TiltY = (90 - altitude) * cos(azimuth)` and its inverse `altitude = 90 - sqrt(tiltX² + tiltY²)`. The two forms agree on the axes and differ off-axis, most at low altitude:

| Azimuth, altitude | Exact TiltX, TiltY (magnitude, current) | Linear TiltX, TiltY (magnitude, earlier) |
| --- | --- | --- |
| 90°, 30° | 60.0°, 0.0° | 60.0°, 0.0° |
| 45°, 60° | 22.2°, 22.2° | 21.2°, 21.2° |
| 45°, 30° | 50.8°, 50.8° | 42.4°, 42.4° |

A recording made with the earlier version holds the linear values. WinPenKit negates TiltX relative to the code above and documents positive TiltX as a lean to the right. Which sign matches a Wintab device has not been measured.

An earlier note said `PenPoint` stores tilt in tenths of a degree, with WM\_POINTER values multiplied by 10. The code stores `double` degrees.

**Twist.** Every session sets `PenCapabilities.Twist`, and so does the native WM\_POINTER session (`PEN_CAP_TWIST`). Wintab fills `Twist` from `orTwist`; the five pointer backends fill it from their APIs (WM\_POINTER and WinForms from `rotation` when `PEN_MASK_ROTATION` is set, WinUI and Avalonia from `Twist`, WPF from `TwistOrientation`). The flag means the backend reads twist. It does not mean the pen has a rotation sensor: a pen without one reports 0 on every backend.

**Buttons.** Both Wintab sessions set `lcPktMode = PK_BUTTONS` (relative mode) and `lcBtnDnMask`/`lcBtnUpMask` to all buttons, and pass `pkButtons` through: `Conventions.Buttons` is `WintabEvent`. The pointer backends write `PointerFlags`, a bitmask replaced on every point: bit 0 barrel, bit 1 eraser. WM\_POINTER sets bit 1 from `PEN_FLAG_ERASER`. WPF sets bit 0 for any `StylusButton` that is down except the tip switch, matched by `StylusPointProperties.TipButton.Id`; before that filter, every tip stroke set the barrel bit. [`PenButtonTracker`](https://github.com/TheSevenPens/WinPenKit/blob/main/WinPenKit/PenButtonTracker.cs) decodes both: call `Update(pt)` for every drained point in order, then read `IsTipDown` (pressure above 0, or a Wintab tip event), `IsBarrelDown(1..3)` and `IsEraser`. It resets its state when the source switches between Wintab and a pointer backend; call `Reset()` when restarting a session. On pointer backends `IsBarrelDown(2)` and `IsBarrelDown(3)` are always false. [`PenButtonAction`](https://github.com/TheSevenPens/WinPenKit/blob/main/WinPenKit/PenButtonAction.cs) and [`PenButtonNumber`](https://github.com/TheSevenPens/WinPenKit/blob/main/WinPenKit/PenButtonNumber.cs) name the Wintab codes. `PenPoint.ButtonAction`, `ButtonNumber`, `IsTipPressed`, `IsButtonPressed` and `IsButtonReleased` are `[Obsolete]`: they apply the Wintab decoding to every point and are always false on pointer backends.

**Eraser.** `PenPoint.IsEraser` is `Cursor == PenCursorType.Eraser` (14, from [PenCursorType.cs](https://github.com/TheSevenPens/WinPenKit/blob/main/WinPenKit/PenCursorType.cs)). The pointer backends write 13 or 14 themselves (`Conventions.Cursor` is `Normalised`): WM\_POINTER and WinForms from `PEN_FLAG_INVERTED`, WinUI and Avalonia from `IsEraser`, WPF from `Inverted`. Both Wintab sessions pass `pkCursor` through unchanged (`DeviceAssigned`), so on a device that numbers its eraser differently, `IsEraser` is false on Wintab and true on the pointer backends.

**Z, barrel pressure, proximity.** Wintab fills `Z` from `pkZ` and sets `ZHeight`; every other backend writes 0. `pkTangentPressure` is in WinPenKit's packet structure but has no `PenPoint` field. Wintab copies `pkStatus` to `Status` and sets `PenCapabilities.Proximity`. `IsInProximity` is `(Status & TPS_PROXIMITY) == 0`, so it is false on the packet a driver sends when the pen leaves. The pointer backends write 0 and leave the flag clear, so `IsInProximity` is true on every point they deliver, and no point marks the pen leaving. WinPenKit ignores `WT_PROXIMITY` messages. Hover points do arrive with pressure 0: WM\_POINTER through `WM_POINTERUPDATE`, WPF through `StylusInAirMove`, WinUI and Avalonia through `PointerMoved`.

## Traps

1. **Counting levels from `MaxPressure`.** "32767 levels" is wrong by a factor of 4 on the DTH246. Fix: treat it as a divisor only; measure granularity from a recording.
2. **Dividing WM\_POINTER pressure by 1023 or by the Wintab maximum.** Fix: divide by `session.MaxPressure` for whichever session produced the point.
3. **Reading `pkButtons` as a state bitmask in relative mode.** Buttons appear pressed for one packet and then read as released. Fix: hold state between events, as `PenButtonTracker` does, or open the context in absolute mode and read it as a bitmask.
4. **Using the obsolete `PenPoint` button properties.** Always false on pointer backends. Fix: `PenButtonTracker`.
5. **Counting the WPF tip switch as a button.** The barrel indicator lights for the length of every stroke. Fix: skip `StylusPointProperties.TipButton`.
6. **Testing the eraser as `pkCursor == 14`.** Works on the Wacom devices observed and fails on a device with other numbering. Fix: on Wintab, read the cursor's description from `WTInfo(WTI_CURSORS + n, ...)` or test `TPS_INVERT` in `pkStatus`. WinPenKit does neither yet; it tracks the numbering problem as issue 48.
7. **Reading `TPS_PROXIMITY` as "in range".** The Wintab specification defines the bit as set when the cursor is out of the context, so it is set on the packet sent when the pen leaves. Code that reads the bit directly as "in proximity" gets the inverse. WinPenKit's `IsInProximity` is `(Status & 0x0001) == 0`; an earlier version read the bit directly. On pointer backends `IsInProximity` is true on every point, and no point arrives when the pen leaves. Fix: test `(pkStatus & TPS_PROXIMITY) == 0` for "in range", and check `Capabilities.HasFlag(PenCapabilities.Proximity)` before relying on a leaving point. The bit's meaning has not been checked against a logged `pkStatus` stream.
8. **Reading the `Twist` flag as "this pen has a rotation sensor".** Every WinPenKit session sets the flag, and a pen without the sensor reports 0. The flag means the backend reads twist from its API, not that the device measures it. Fix: do not use the flag to decide whether to show rotation controls; a constant 0 is what a pen without the sensor reports. Earlier WinPenKit versions left the flag clear on the pointer backends while filling the value.
9. **Mixing tilt formulas.** The linear form `(90 - altitude) * sin(azimuth)` differs from the exact relation by up to 8.3 degrees off-axis (azimuth 45, altitude 30). Data from earlier WinPenKit versions, or from code that uses the linear form, does not match current WinPenKit values. Fix: use the exact relation, as [`PenTilt`](https://github.com/TheSevenPens/WinPenKit/blob/main/WinPenKit/PenTilt.cs) does, and check the sign of X against your source.
10. **Forgetting Wintab's tenths.** Values ten times too large. Fix: divide by 10.0, as WinPenKit does.

## Further reading

* [Stage 3: Timing](3-timing.md) and [Stage 7: The output contract](7-output.md) for the rest of `PenPoint`, `Conventions` and switching APIs.
* [API reference card](api-reference.md) for every API's values side by side.
* [Pressure quantization](../../processing-pen-data/pressure-quantization.md) and [Diagnosing a bad stroke](../../build-a-scribble-app/diagnosing-a-bad-stroke.md) (the **Lumpy** symptom).
* WinPenKit's [HOW\_TO\_USE.md](https://github.com/TheSevenPens/WinPenKit/blob/main/Docs/HOW_TO_USE.md), sections "What `MaxPressure` is, and is not", "Conventions" and "Buttons and Eraser".
