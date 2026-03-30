# WinTab vs WM\_POINTER

#### WM\_POINTER

* Also called: Windows Pointer API  / Windows Ink&#x20;
* Uses `WM_POINTER*` messages
* PROS:
  * Comes as part of Windows
  * Multiple tablet brands can work simultaneously

#### WinTab API

* Third-party API (`wintab32.dll`)
* CON: Each tablet brand has their own wintab32.dll and they install it so that they ovewrite the previous dll. On Windows can't really use multiple tablet brands simultaneously.&#x20;
* PRO: Can be used to provide much higher-resolution coordinates than WM\_POINTER.
