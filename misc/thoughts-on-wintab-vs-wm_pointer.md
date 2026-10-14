# Thoughts on WinTab vs WM\_POINTER

## For developers

Wacom published a page with frequently asked questions about WinTab:

[https://developer-support.wacom.com/hc/en-us/articles/12844524637975-Wintab](https://developer-support.wacom.com/hc/en-us/articles/12844524637975-Wintab) ([archive](https://archive.is/htSEG))

Here is a small snippet from the relevant section.

<div align="left"><figure><img src="/broken/files/XeyXgQ4MdLyF1q9yF25R" alt="" width="375"><figcaption></figcaption></figure></div>

Please read the document for the full details.

### My developer perspective

But here are a few things that stand out to me:

* It is a well-understood and stable API.
* There are wrappers for many languages, including C#, Rust, and Python, that let you work with the API.
  * I had a relatively simple time incorporating it into my test drawing app called [WinTabPainter](https://github.com/TheSevenPens/WinTabPainter).
* You can find many projects that use WinTab.
* It has been difficult for me to find clear examples of how to use the Windows Ink API. Most code focuses on inking features, which is great, but not on what I need: a way to get pen position, pressure, tilt data, and more.

So, at the moment, I intend to continue using WinTab until I find an easy way to consume the Windows Ink APIs.
