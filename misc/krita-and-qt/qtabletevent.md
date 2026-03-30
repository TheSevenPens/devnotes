# QTabletEvent

### QTabletEvent unified pen data

Regardless of backend, Qt emits a QTabletEvent.

This unifies:

* Pressure
* Tilt
* Position
* Device type

The caller (such as Krita) does **not know** which API is being used.
