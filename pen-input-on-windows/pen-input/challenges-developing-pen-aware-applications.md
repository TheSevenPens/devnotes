# Challenges developing pen-aware applications on Windows

## Lots of APIs

What makes this challenging is that windows has had a very long lifetime so the story has evolved. This leaves us with lots of APIs to deal with.

## Limits of official documentation

The documentation around these topics can be difficult to deal with. While it does work great as reference material it is very difficult to figure out how to assemble all the pieces together. And there are a lack of samples that work with end to end.

And in fact it's not entirely clear what all the pieces are. For developer just starting out with creating a pen aware application there's no clear starting point. There is no map to easily follow to acquire the knowledge you need.

## Third-party APIs

Another complication of the windows system is that normally this windows itself give us lots of choice in API's that come built into windows but also we have to contend with third party APIs - specifically this has to deal with the WinTab API that Wacom.

## UI frameworks

Furthermore if you're familiar with windows you probably know that windows has evolved different UI frameworks over time. You can work at the very lowest level – aka the win32 level - or you can work through libraries such as MFC, or entire UI frameworks such as WinForms or XAML or WINUI3 or Avalonia. The choice of framework affects which APIs you need to work with.

Guidance is mostly missing:

* Which API works in what situation
* pros and cons,&#x20;
* trade-offs
* non obvious things you'll eventually have to deal with

## An attempt at clarification

So these docs are my attempt at sharing what I've learned.

The doc builds upon

* Hand-crafting applications that use some of these APIs
* Discussions with and feedback from tablet enthusiasts
* A great deal of AI assistance in building apps that excercise the APIs. This was most helpful in cases when I am familiar with some frameworks (WIN32, WinForms) but not experienced in others (WPF, Avalonia).
