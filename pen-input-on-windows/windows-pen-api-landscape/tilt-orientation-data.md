# Tilt / Orientation Data

### Tilt / Orientation Data

**Twist** (also called **barrel rotation**) is the rotation of the pen around its own long axis — like turning a screwdriver. Twist support is rare — it requires both a specific tablet model and a specific pen that contains a rotation sensor (e.g., Wacom's Art Pen or Airbrush stylus). Standard pen styluses do not report twist, and most consumer tablets do not support it even with the right pen. The APIs list twist support, but in practice very few hardware setups actually produce twist data.

| API                | Tilt representation                                                                         | Twist                               | Notes                                       |
| ------------------ | ------------------------------------------------------------------------------------------- | ----------------------------------- | ------------------------------------------- |
| Wintab             | Azimuth (compass direction, 0–3600 tenths of degree) + Altitude (angle from surface, 0–900) | orTwist (barrel rotation, 0–3600)   | Full spherical coordinates; most detailed   |
| WM\_POINTER        | TiltX / TiltY (degrees, -90 to +90)                                                         | Rotation (degrees, 0–359)           | Cartesian tilt; simpler but less expressive |
| WinUI PointerPoint | `Properties.XTilt` / `YTilt` (float, degrees)                                               | `Properties.Twist` (float, degrees) | Same as WM\_POINTER                         |
| WPF StylusPoint    | `XTiltOrientation` / `YTiltOrientation`                                                     | Not directly available              | Limited                                     |
| RealTimeStylus     | Azimuth + Altitude + Twist                                                                  | Full                                | Similar to Wintab                           |

**PenPoint normalization:** The unified `PenPoint` struct carries **both** representations (Azimuth/Altitude and TiltX/TiltY), all normalized to **tenths of a degree**. Each backend computes whichever it doesn't have natively. WM\_POINTER's integer degrees are multiplied by 10; Wintab's spherical values are converted via trigonometry. Consumers can use either representation without knowing which API produced the data.
