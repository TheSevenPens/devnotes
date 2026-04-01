# Cursor follows pen

A comparison of the available APIs for receiving pen/stylus input on Windows, relevant to drawing and handwriting applications.

<table data-full-width="true"><thead><tr><th>API</th><th>Threading</th></tr></thead><tbody><tr><td><strong>Wintab (System)</strong></td><td>Background thread (200+ Hz)</td></tr><tr><td><strong>Wintab (Digitizer Hi-Res)</strong></td><td>Background thread (200+ Hz)</td></tr><tr><td><strong>WM_POINTER / WM_POINTERUPDATE</strong></td><td>UI thread (message-driven)</td></tr><tr><td><strong>Windows Ink (WinUI PointerPoint)</strong></td><td>UI thread</td></tr><tr><td><strong>Windows Ink (WPF StylusPoint)</strong></td><td>UI thread</td></tr><tr><td><strong>RealTimeStylus (COM)</strong></td><td>Configurable (sync or async plugin)</td></tr></tbody></table>

