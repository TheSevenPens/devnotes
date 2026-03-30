# Krita pen api implementation notes

### The Krita → Qt → WinTab / WM\_POINTER path

#### Krita side

Krita startup code on Windows with Qt6:

* Krita reads its saved tablet preference
* computes `forceWinTab`
* gets Qt’s Windows-native application interface
* calls `setWinTabEnabled(forceWinTab)`.&#x20;

Krita startup code on Windows with Qt5

* Krita instead uses `Qt::AA_MSWindowsUseWinTabAPI`. ([GitHub](https://github.com/KDE/krita/blob/master/krita/main.cc))

The flow is:

```
Tablet Settings UI
  -> save config (useWin8PointerInput)
  -> next launch reads config
  -> Krita tells Qt Windows backend whether WinTab should be enabled
```

#### Qt side

The key Qt pieces are:

* `QNativeInterface::Private::QWindowsApplication` declares `isWinTabEnabled()` and `setWinTabEnabled(bool)`. ([Code Browser](https://codebrowser.dev/qt6/qtbase/src/gui/kernel/qguiapplication_p.h.html?utm_source=chatgpt.com))
* In the Windows platform plugin, `QWindowsApplication::setWinTabEnabled()` is implemented by asking `QWindowsContext` to either `initTablet()` or `disposeTablet()`.
* `QWindowsContext::initTablet()` creates `QWindowsTabletSupport`; `disposeTablet()` destroys it.

#### WinTab inside Qt

The WinTab implementation lives in:

* `src/plugins/platforms/windows/qwindowstabletsupport.cpp`
* plus the bundled WinTab headers mentioned by Qt’s attribution page: `src/3rdparty/wintab/pktdef.h` and `wintab.h`. ([Qt Documentation](https://doc.qt.io/qt-6/qtgui-attribution-wintab.html?utm_source=chatgpt.com))

What that code does:

1. Loads `wintab32.dll`
2. Creates a hidden dummy window
3. Opens a WinTab context with `WTOpenW`
4. Receives `WT_PROXIMITY` and `WT_PACKET`
5. Converts packet data into Qt tablet events via `QWindowSystemInterface::handleTabletEvent(...)`

#### WM\_POINTER / Windows Pointer path inside Qt

The Windows event dispatcher path in `qwindowscontext.cpp` includes `qwindowspointerhandler.h`, and routes `PointerEvent` / `NonClientPointerEvent` to `QWindowsPointerHandler::translatePointerEvent(...)`. Mouse events go through the same pointer handler’s mouse translation path.

So, conceptually for WM\_POINTER:

```
WM_POINTER / Windows Ink
  -> QWindowsPointerHandler
  -> QWindowSystemInterface
  -> QTabletEvent / Qt input events
```

while while for WinTab:

```
WinTab
  -> QWindowsTabletSupport
  -> QWindowSystemInterface
  -> QTabletEvent / Qt input events
```

### Minimal code that mimics Krita’s Qt 6 startup logic

Important note: This uses **Qt private API**. Krita can do that because it is willing to depend on Qt internals. For ordinary apps, this is not a stable public API. Krita’s own code is effectively doing that on Windows + Qt 6. ([GitHub](https://github.com/KDE/krita/blob/master/krita/main.cc))

```cpp
// main.cpp
#include <QApplication>
#include <QWidget>
#include <QVBoxLayout>
#include <QLabel>
#include <QDebug>
#include <QTabletEvent>

#ifdef Q_OS_WIN
#include <QtGui/private/qguiapplication_p.h>   // private API
#endif

class TabletWidget : public QWidget
{
public:
    TabletWidget()
    {
        setAttribute(Qt::WA_TabletTracking, true);

        auto *layout = new QVBoxLayout(this);
        label = new QLabel("Use pen on this widget", this);
        layout->addWidget(label);
        setLayout(layout);
        resize(600, 300);
    }

protected:
    bool event(QEvent *e) override
    {
        switch (e->type()) {
        case QEvent::TabletPress:
        case QEvent::TabletMove:
        case QEvent::TabletRelease: {
            auto *te = static_cast<QTabletEvent*>(e);
            label->setText(QString(
                "type=%1  pos=(%2,%3)  pressure=%4  xTilt=%5  yTilt=%6  pointerType=%7")
                .arg(int(e->type()))
                .arg(te->position().x())
                .arg(te->position().y())
                .arg(te->pressure(), 0, 'f', 3)
                .arg(te->xTilt())
                .arg(te->yTilt())
                .arg(int(te->pointingDevice()->pointerType())));
            return true;
        }
        default:
            break;
        }
        return QWidget::event(e);
    }

private:
    QLabel *label = nullptr;
};

int main(int argc, char *argv[])
{
    QApplication app(argc, argv);

#ifdef Q_OS_WIN
    // Simulate Krita's saved preference:
    // true  => force WinTab
    // false => use default Windows pointer path
    const bool forceWinTab = true;

    using QWindowsApplication = QNativeInterface::Private::QWindowsApplication;

    if (auto *nativeWindowsApp =
            dynamic_cast<QWindowsApplication *>(QGuiApplicationPrivate::platformIntegration())) {
        const bool ok = nativeWindowsApp->setWinTabEnabled(forceWinTab);
        qDebug() << "setWinTabEnabled(" << forceWinTab << ") =>" << ok
                 << "isWinTabEnabled() =>" << nativeWindowsApp->isWinTabEnabled();
    } else {
        qWarning() << "Windows platform integration not available";
    }
#endif

    TabletWidget w;
    w.show();
    return app.exec();
}
```

### The closest “public-ish” alternative

If you do **not** want to rely on private Qt headers, the usual WinTab forcing mechanism is to set `QT_WINTAB_ENABLED=1` before creating the application object. Qt documents WinTab as being used by the Windows platform plugin, and the WinTab support is part of the tablet-event feature set. ([Qt Documentation](https://doc.qt.io/qt-6/qtgui-attribution-wintab.html?utm_source=chatgpt.com))

```cpp
#include <QApplication>
#include <QWidget>
#include <QCoreApplication>

int main(int argc, char *argv[])
{
#ifdef Q_OS_WIN
    qputenv("QT_WINTAB_ENABLED", "1");
#endif

    QApplication app(argc, argv);
    QWidget w;
    w.resize(400, 200);
    w.show();
    return app.exec();
}
```

### Clean model of the exact Qt 6 flow

This is the most accurate compact picture:

```
Krita startup
  -> read config
  -> forceWinTab = !useWin8PointerInput
  -> QNativeInterface::Private::QWindowsApplication::setWinTabEnabled(forceWinTab)

If true:
  -> QWindowsApplication::setWinTabEnabled(true)
  -> QWindowsContext::initTablet()
  -> QWindowsTabletSupport::create()
  -> load wintab32.dll, create dummy window, open WinTab context
  -> WT_PACKET / WT_PROXIMITY
  -> QWindowSystemInterface::handleTabletEvent(...)
  -> QTabletEvent to app

If false:
  -> no WinTab tablet support object
  -> normal Windows pointer path remains active
  -> qwindowspointerhandler handles WM_POINTER-family input
  -> Qt emits unified events to the app
```

