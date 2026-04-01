# Converting Between Tilt Representations

## The situation

There are two mathematically equicalent ways of representing pen tilt

* Spherical coordinates - Azimuth and altitude
* Cartesian tilt coordinates - Tilt X and Tilt X

Depdnding on the Pen API you use, you will receive tilt coordinates in one of two tilt coordinate&#x20;

* **Wintab** and **RealTimeStylus** use **Azimuth** and **Altitude** (spherical coordinates).
* **WM\_POINTER**, **WinUI**, and **WPF** use **TiltX** and **TiltY** (Cartesian tilt).

## Which one is more useful

For a drawing app, I think spherical coordinates are generally more useful because they map to an intuitive sense of how the brush is tilted.&#x20;

## Definitions and ranges

All angles are in **degrees**.

| Value    | Description                                                                             | Range      |
| -------- | --------------------------------------------------------------------------------------- | ---------- |
| Azimuth  | Compass direction the pen is leaning toward, measured clockwise from North (positive Y) | 0 to 360   |
| Altitude | Angle of the pen above the tablet surface (90 = perfectly upright)                      | 0 to 90    |
| TiltX    | Tilt of the pen along the X axis (left/right lean)                                      | -90 to +90 |
| TiltY    | Tilt of the pen along the Y axis (forward/backward lean)                                | -90 to +90 |

**Notes**:&#x20;

* Wintab reports azimuth and altitude in **tenths of a degree** (0–3600 and 0–900). Divide by 10.0 before using the conversions below.
* The reported values for tilt altitude should - according to the tablet specs be within 0deg to 60 deg. In practice I've found sometimes you might see a value like 64deg.

## C# conversion code

```csharp
using System;

public static class PenTiltConversion
{
    /// <summary>
    /// Convert Azimuth/Altitude to TiltX/TiltY.
    /// All values in degrees.
    /// Azimuth: 0..360 (clockwise from +Y axis)
    /// Altitude: 0..90 (0 = flat on surface, 90 = straight up)
    /// TiltX: -90..+90
    /// TiltY: -90..+90
    /// </summary>
    public static (double TiltX, double TiltY) AzimuthAltitudeToTiltXY(
        double azimuthDeg, double altitudeDeg)
    {
        double azRad = azimuthDeg * Math.PI / 180.0;
        double altRad = altitudeDeg * Math.PI / 180.0;

        // Azimuth is clockwise from +Y, so:
        //   sin(azimuth) gives the X component
        //   cos(azimuth) gives the Y component
        // altitude measures up from the surface, so the zenith angle is (90 - altitude)
        // and tan(zenith) = 1/tan(altitude)

        double tiltX = Math.Atan(Math.Sin(azRad) / Math.Tan(altRad)) * 180.0 / Math.PI;
        double tiltY = Math.Atan(Math.Cos(azRad) / Math.Tan(altRad)) * 180.0 / Math.PI;

        return (tiltX, tiltY);
    }

    /// <summary>
    /// Convert TiltX/TiltY to Azimuth/Altitude.
    /// All values in degrees.
    /// TiltX: -90..+90
    /// TiltY: -90..+90
    /// Azimuth: 0..360 (clockwise from +Y axis)
    /// Altitude: 0..90
    /// </summary>
    public static (double Azimuth, double Altitude) TiltXYToAzimuthAltitude(
        double tiltXDeg, double tiltYDeg)
    {
        double txRad = tiltXDeg * Math.PI / 180.0;
        double tyRad = tiltYDeg * Math.PI / 180.0;

        double tanTx = Math.Tan(txRad);
        double tanTy = Math.Tan(tyRad);

        // Altitude: angle above the surface
        // tan(zenith) = sqrt(tan(tiltX)^2 + tan(tiltY)^2)
        // altitude = 90 - zenith
        double zenithRad = Math.Atan(Math.Sqrt(tanTx * tanTx + tanTy * tanTy));
        double altitudeDeg = 90.0 - zenithRad * 180.0 / Math.PI;

        // Azimuth: clockwise from +Y
        // atan2(sin(az), cos(az)) = atan2(tanTx, tanTy)
        double azimuthRad = Math.Atan2(tanTx, tanTy);
        double azimuthDeg = azimuthRad * 180.0 / Math.PI;

        // Normalize to 0..360
        if (azimuthDeg < 0)
            azimuthDeg += 360.0;

        return (azimuthDeg, altitudeDeg);
    }
}
```

## Edge cases

* **Pen straight up** (Altitude = 90): Azimuth is undefined — any value is valid. TiltX and TiltY will both be 0.
* **Pen flat on surface** (Altitude = 0): This is a mathematical singularity. In practice, hardware never reports altitude exactly at 0, but guard against division by zero if altitude is very small.
* **TiltX = 0 and TiltY = 0**: The pen is straight up, so Altitude = 90 and Azimuth is arbitrary (the code above will return 0).
