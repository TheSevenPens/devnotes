# What Is "Windows Ink"?

"Windows Ink" is one of the most overloaded terms in Windows pen input. It gets used casually to mean very different things depending on who's talking — a tablet driver developer, an app developer, or an end user. This causes real confusion when troubleshooting pen input issues or choosing an API.

## The Three Meanings

### 1. Windows Ink as a Marketing Brand

Microsoft introduced "Windows Ink" as a brand name in Windows 10 Anniversary Update (2016). It was the umbrella term for pen-related features: the Windows Ink Workspace, Sticky Notes with handwriting, Screen Sketch, and handwriting recognition in text fields.

In this sense, "Windows Ink" is not a specific API — it's a marketing name for "pen stuff in Windows." This is the meaning most end users encounter.

### 2. Windows Ink as a Driver Setting

In tablet driver configuration panels (Wacom, Huion, XP-Pen), there is typically a checkbox labeled **"Windows Ink"** or **"Enable Windows Ink."**

This checkbox controls whether the driver exposes the **WM\_POINTER** input path alongside Wintab:

| Setting                  | What the driver does                     |
| ------------------------ | ---------------------------------------- |
| Windows Ink **enabled**  | Exposes both Wintab and WM\_POINTER APIs |
| Windows Ink **disabled** | Exposes Wintab only                      |

When someone says "turn off Windows Ink in your tablet driver," they mean: disable the WM\_POINTER path so only Wintab is active. This is a common troubleshooting step for drawing apps that have issues with WM\_POINTER input.

See [Wintab and Windows Ink Coexistence](implementation-notes/wintab-vs-windows-ink-driver-conflict.md) for details.

### 3. Windows Ink as a Set of APIs

For developers, "Windows Ink" loosely refers to the modern pen input stack that Microsoft built as an alternative to Wintab:

* **WM\_POINTER / WM\_POINTERUPDATE** — the Win32 message-level API (Windows 8+)
* **WinUI PointerPoint** — XAML-level wrapper over WM\_POINTER
* **WPF StylusPoint** — WPF's stylus event system
* **InkCanvas** — a ready-made XAML control for ink rendering (available in both WinUI and WPF)
* **RealTimeStylus** — the older COM-based API (Windows XP Tablet PC Edition)

None of these are literally called "Windows Ink API." There is no single API with that name. But when a developer says "our app uses Windows Ink," they typically mean one of the above — usually WM\_POINTER or the framework's pointer/stylus events.

## Why This Matters

The ambiguity causes real problems:

* **"Does your app support Windows Ink?"** — This could mean: does it use WM\_POINTER? Does it work when the driver's Windows Ink checkbox is enabled? Does it support the InkCanvas control?
* **"Turn off Windows Ink to fix the lag"** — This means: disable the WM\_POINTER path in the tablet driver, forcing Wintab-only mode. It has nothing to do with Windows Ink Workspace or Sticky Notes.
* **"We switched from Wintab to Windows Ink"** — This means: the app now uses WM\_POINTER (or a framework layer on top of it) instead of calling Wintab32.dll directly.

## The Practical Takeaway

When you encounter "Windows Ink" in a technical context, ask: **which meaning?**

| Context                             | "Windows Ink" means                                                   |
| ----------------------------------- | --------------------------------------------------------------------- |
| End user / marketing                | The pen features brand (Ink Workspace, Sticky Notes, etc.)            |
| Tablet driver settings              | The checkbox that enables/disables WM\_POINTER alongside Wintab       |
| App developer                       | WM\_POINTER and/or framework pointer events (not a specific API name) |
| App preferences ("Use Windows Ink") | The app will use WM\_POINTER instead of Wintab for pen input          |

For API-level discussions, prefer the specific name: **WM\_POINTER**, **PointerPoint**, **StylusPoint**, or **InkCanvas** — not "Windows Ink."
