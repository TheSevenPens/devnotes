# PenSession Tilt handling

The unified `PenPoint` struct carries **both** representations (Azimuth/Altitude and TiltX/TiltY), all normalized to **tenths of a degree**. Each backend computes whichever it doesn't have natively. WM\_POINTER's integer degrees are multiplied by 10; Wintab's spherical values are converted via trigonometry. Consumers can use either representation without knowing which API produced the data.
