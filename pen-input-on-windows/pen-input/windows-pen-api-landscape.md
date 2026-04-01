# Windows Pen API Landscape

A comparison of the available APIs for receiving pen/stylus input on Windows, relevant to drawing and handwriting applications.

There are five different APIs available depending on your needs and situation.

* Wintab
* RealTimeStylus API
* WPF StylusPoint
* WM\_POINTER
* WinUI PointerPoint

## Wintab

Introduced by Wacom in 1991, Wintab is a 3rd-party pen API. Almost all pen-aware apps for creative use support Wintab.&#x20;

Wintab has two modes called "contexts" in their API:

* The Sytem context&#x20;
* The Digitizer context

The digitizer context requires some more effort to use - but the advantage is that it gives you access to the full tablet digitizer resolution. In other words, the digitizer context offers "sub-pixel precision".

For a long time, for creative apps Wintab was "the only game in town" for working with a drawing tablet to get pressure sensitivity, tilt, etc.

## **RealTimeStylus API**

Microsoft introduced this API via its "Tablet PC" development effort - around 2005 to 2006. It was integrated into Windows Vista and the Windows 7.

Reference: [https://learn.microsoft.com/en-us/windows/win32/tablet/what-s-new-in-tablet-pc-development](https://learn.microsoft.com/en-us/windows/win32/tablet/what-s-new-in-tablet-pc-development)

When RealTimeStylus API was introduced it did not use WM\_POINTER (WM\_POINTER was not available in Vista and Windows 7) but since since Window 8, RealTimeStylus may have moved to using WM\_POINTER directly.

## WPF StylusPoint

Microsoft introduced WPF StylusPoint as part of WPF 1.0 in late 2006.

At least when it was first introduced, WPF StylusPoint called the RealTimeStylus API under the covers. It's not entirely clear if it continues to use RealTimeStylus or now uses WM\_POINTER directly.

## WM\_POINTER

Microsoft introduced WM\_POINTER messages in Windows 8 in 2012.

WM\_POINTER unifies touch, pen, and mouse input to simplify working with different kinds of "pointer" input.

## WinUI PointerPoint

This is the newest pen API that Microsoft introduced in Windows 10.&#x20;

This API uses WM\_POINTER underneath.
