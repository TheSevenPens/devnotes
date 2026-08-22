# Wintab input routing

Wintab sessions create their own hidden Win32 window on a dedicated background thread. The Wacom driver delivers `WT_PACKET` messages to that window regardless of what UI framework the app uses. The session is completely decoupled from the app's windowing model.

This is why Wintab is the universal fallback — it works in every framework without any framework-specific code.

**Important:** The hidden window must be a regular top-level window, not `HWND_MESSAGE`. The Wacom driver doesn't deliver `WT_PACKET` to message-only windows.
