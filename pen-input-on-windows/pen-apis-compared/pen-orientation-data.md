# Pen Orientation Data

### Overview

Orientation is how the table is rotated in space. The primary components are Tilt and Twist.

* **Tilt** - is how much the pen "leans over" and in what direction it leans
* **Twist** (also called **barrel rotation**) is the rotation of the pen around its own long axis — like turning a screwdriver.&#x20;

Both Tilt and Twist are reported as angles. TIlt is a pair of angles - either Altitude & Azimuth or TiltX and TiltY depending on the API.

See this video for more details

{% embed url="https://www.youtube.com/watch?v=O9cMFehZnsI" %}

| API                | Tilt representation                                                                         | Twist                               | Notes                                       |
| ------------------ | ------------------------------------------------------------------------------------------- | ----------------------------------- | ------------------------------------------- |
| Wintab             | Azimuth (compass direction, 0–3600 tenths of degree) + Altitude (angle from surface, 0–900) | orTwist (barrel rotation, 0–3600)   | Full spherical coordinates; most detailed   |
| WM\_POINTER        | TiltX / TiltY (degrees, -90 to +90)                                                         | Rotation (degrees, 0–359)           | Cartesian tilt; simpler but less expressive |
| WinUI PointerPoint | `Properties.XTilt` / `YTilt` (float, degrees)                                               | `Properties.Twist` (float, degrees) | Same as WM\_POINTER                         |
| WPF StylusPoint    | `XTiltOrientation` / `YTiltOrientation`                                                     | Not directly available              | Limited                                     |
| RealTimeStylus     | Azimuth + Altitude + Twist                                                                  | Full                                | Similar to Wintab                           |

## Twist support in hardware is rare&#x20;

It requires both a specific tablet model and a specific pen that contains a rotation sensor (e.g., Wacom's Art Pen or Airbrush stylus). Standard pen styluses do not report twist, and most consumer tablets do not support it even with the right pen. The APIs list twist support, but in practice very few hardware setups actually produce twist data.
