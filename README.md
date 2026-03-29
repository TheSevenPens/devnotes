# Developer Notes

Notes on building drawing applications and creative technology on Windows. Covers pen input APIs, UI frameworks, rendering approaches, and hard-won lessons from building pen-enabled apps across multiple languages and frameworks.

## Topics

* **Pen Input** — Windows pen APIs, framework-specific input routing, coordinate spaces, DPI handling
* **Rendering** — Bitmap-backed drawing, SkiaSharp, Win2D, GDI, tiny-skia
* **Frameworks** — WinUI 3, WPF, WinForms, Avalonia, egui, Win32

## Related Projects

* [WinPenSession](https://github.com/TheSevenPens/WinPenSession) — Unified pen input SDK for Windows
* [Wacom\_WintabDN](https://github.com/TheSevenPens/Wacom_WinTabDN) — Low-level Wintab .NET library. This is a refactoring and cleanup of Wacom's WintabDN library. It does exactly the same thing but the code inside is more modern, follows more best practices. I don't think anyone would need this in practice, but I am keeping it around since it was the start of my exploration with the topic of Windows pen input APIs.
