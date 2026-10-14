# Stage 3: Timing: batches, coalescing and timestamps

This stage decides whether every sample the pen produced reaches your code, in the order it was produced, with a time you can subtract. When samples are dropped, a fast stroke turns into long straight segments between widely spaced points. When a batch is replayed in the wrong order, each batch is drawn backwards and the stroke looks jittery. When timestamps are misread, velocity and time-based smoothing divide by zero or by a value from the wrong clock.

## In short

- On WM\_POINTER and WinForms, call `GetPointerPenInfoHistory` on every `WM_POINTERUPDATE`, use the history only when `count > 1`, clamp the count to your buffer size, and replay it from the last index down to 0.
- On WinUI 3, replay `GetIntermediatePoints` from the last index down to 0 (newest first, the reverse of Microsoft's documentation); on Avalonia, replay it from index 0 up (oldest first); on WPF, take every point of `GetStylusPoints`.
- Read `PenPoint.TimestampMicroseconds` only as a difference between two points from the same session, and allow a difference of zero, because WPF and recovered Avalonia batches share one timestamp across several points.
- Read `session.Conventions.Timestamp` to learn which clock a session uses; do not infer it from the value.
- Poll `DrainPoints()` from your render tick; every backend queues points on the thread that produced them.

## The problem

The pen samples at a fixed rate set by the device. On a Wacom DTH246, drawn on by hand on 13 Sep 2026, six unrelated code paths (the WinPenKit native C ABI over Wintab, WinForms, WinUI, Avalonia, WPF and Qt's own stack) all measured **180 Hz**: gaps averaging 5559 to 5560 µs on the four backends with one timestamp per point, and 180.1 Hz and 179.9 Hz from points divided by elapsed time on WPF and Qt. The rate is a property of the device, not of the API. Figures in earlier notes ("200+ Hz" for Wintab, "120 to 240 Hz" for WM\_POINTER, "up to 240+ Hz" for RealTimeStylus) were not measurements.

Between the device and your code, three things can go wrong:

1. **Merging.** If the thread that receives input is busy, some APIs merge several samples into one event. The event carries the newest sample; the older ones are available only if you ask for them.
2. **Order.** When you do ask, the batch comes back newest first or oldest first depending on the API, and one of them is documented the wrong way round.
3. **Time.** Every API stamps its samples on a different clock, in a different unit, at a different resolution, and two of the source fields are 32-bit counters that wrap.

## How the APIs differ here

### Which thread receives the samples

| API | Thread | What a busy UI thread does |
| --- | --- | --- |
| Wintab (both contexts) | Wintab posts `WT_PACKET` to the window passed to `WTOpen`, so the thread is whichever thread owns that window. WinPenKit creates that window on its own background thread. | Nothing to capture. Each packet is its own message, read with `WTPacket` by serial number, so packets are not merged. |
| WM\_POINTER | UI thread (window procedure) | `WM_POINTERUPDATE` messages are merged; history recovers them. |
| WinForms (WM\_POINTER) | UI thread (`IMessageFilter`) | Same as WM\_POINTER. |
| WPF Stylus | UI thread (`StylusMove` and related events) | Each event carries a `StylusPointCollection` batch. |
| WinUI 3 `PointerPoint` | UI thread (XAML pointer events) | Samples are merged; `GetIntermediatePoints` recovers them. |
| Avalonia | UI thread (pointer events) | Samples are merged; `GetIntermediatePoints` recovers them. |
| RealTimeStylus | Configurable: synchronous plug-ins run on the pen thread, asynchronous plug-ins on the UI thread | Not covered by WinPenKit. |

The Wintab specification gives each context a packet queue and a `TPS_QUEUE_ERR` status bit for when it overflows. WinPenKit does not call `WTQueueSizeSet`, so the driver's default queue size applies. Whether that queue has overflowed on WinPenKit's pump thread has not been measured.

### WM\_POINTER coalescing

When the UI thread falls behind, Windows merges several `WM_POINTERUPDATE` messages into one. The message carries the newest position, and the earlier ones are lost unless you call `GetPointerPenInfoHistory`. The symptom described in earlier notes is a stroke made of straight segments between widely spaced points, more visible in apps with heavy render loops (Electron was the example given) than in apps with a light message pump such as raw Win32 and GDI. That comparison was not measured.

```cpp
if (msg == WM_POINTERUPDATE) {
    POINTER_PEN_INFO history[64];
    UINT32 count = 64;
    if (GetPointerPenInfoHistory(pointerId, &count, history) && count > 1) {
        // count is the number Windows holds, which can exceed the buffer.
        if (count > 64) count = 64;  // or call again with a buffer of count entries
        for (int i = count - 1; i >= 0; i--)  // history is newest first
            process_point(history[i]);
        return;
    }
}

// Single point: not coalesced, or WM_POINTERDOWN / WM_POINTERUP.
POINTER_PEN_INFO pen_info = {};
GetPointerPenInfo(pointerId, &pen_info);
process_point(pen_info);
```

**Use `count > 1`, not `count > 0`.** When the history holds one entry, its data can differ from what `GetPointerPenInfo` returns for the same event. With `count > 0`, a Win32 scribble app stopped receiving any WM\_POINTER data, with no error. Fall through to `GetPointerPenInfo` for single events. Only `WM_POINTERUPDATE` needs the history: down and up are single events, and asking for their history returns the one point again.

### Framework batches

Earlier notes said WinUI 3, WPF, WinForms and Avalonia merge-and-recover internally, so that only raw Win32 needs history. That was never established, and WinPenKit's code does the recovery itself on every framework:

| Framework | Call that returns the batch | Order of the batch | Timestamp per point |
| --- | --- | --- | --- |
| WinForms | `GetPointerPenInfoHistory` from a raw `WM_POINTERUPDATE` | newest first | yes |
| WPF | `StylusEventArgs.GetStylusPoints(element)` | iterated in collection order | no: one per event |
| WinUI 3 | `PointerRoutedEventArgs.GetIntermediatePoints(element)` | **newest first** | yes |
| Avalonia | `PointerEventArgs.GetIntermediatePoints(element)` | **oldest first** | no: one per event |

The WinUI and Avalonia orders were measured, not read. Microsoft documents that the last item in the WinUI collection equals `GetCurrentPoint`. With an injected stroke moving in increasing X, a 40-point WinUI batch ran from 353.8 down to 295.1 and `GetCurrentPoint` returned 353.8, which is index 0. Avalonia's XML documentation for `GetIntermediatePoints` is a copy of `GetCurrentPoint`'s and says nothing about order; a 3-point batch ran 296.9, 298.2, 299.5 and `GetCurrentPoint` returned the last entry.

Merging depends on load. Before WinPenKit recovered Avalonia's batch, a hand-speed stroke on a Wacom tablet gave 131.6 points per 1000 px on Avalonia against 112.8 on WinForms (which recovers), with no gaps. After recovery was added, a 180 Hz stroke on Avalonia gave 2167 points and 2167 distinct timestamps, and `GetIntermediatePoints` returned one point every time. The batch path produces several points per event when the application falls behind, not as a rule.

### Latency

Latency (pen contact to point in your handler) has not been measured for any API here. Timestamps alone cannot measure it. Earlier notes estimated 4 to 20 ms for Wintab and 4 to 30 ms for WM\_POINTER, with WinUI adding XAML dispatch on top of WM\_POINTER; none of these were measured. What is known:

* WM\_POINTER and the framework events are handled on the UI thread, so heavy layout or a large redraw delays them. Wintab's background thread keeps capturing during that time. This is one reason given for drawing apps such as Photoshop, Krita and Clip Studio Paint preferring Wintab.
* An app that polls on a render timer adds up to one frame of delay on every backend.
* In one run, the time from a point's timestamp to its handler ranged from 0.372 ms to 26.6 ms. The largest was the first point after startup.

### Timestamps

| Backend | Source field | Source type | Clock (`PenTimestampSource`) | Measured on hardware | One timestamp per point |
| --- | --- | --- | --- | --- | --- |
| WM\_POINTER, WinForms | `POINTER_INFO.PerformanceCount` | `ulong` QPC ticks | `PerformanceCounter` | **1 µs**: 2070 points, 2070 distinct | yes |
| WinUI 3 | `PointerPoint.Timestamp` | `ulong` µs | `SystemTicks` (epoch only) | **1 µs**: 1878 points, 1878 distinct | yes |
| Avalonia | `PointerEventArgs.Timestamp` | `ulong` ms, filled from 32-bit `GetMessageTime` | `SystemTicks` | 1 ms: 2167 points, 2167 distinct | yes on the measured run; a recovered batch shares one |
| Wintab (high-res) | `PACKET.pkTime` | `uint` ms | `DeviceTicks` | 1 ms: 1683 points, 1683 distinct; gaps of 5 or 6 ms only, mean 5555 µs | yes |
| WPF Stylus | `StylusEventArgs.Timestamp` | `int` ms | `SystemTicks` | 1 ms clock, 15.6 ms batches: 2442 points, 885 distinct | **no**: two to four points share one |
| Qt (`Scribble.Qt`, for comparison) | `QInputEvent::timestamp` | `quint64` ms | not WinPenKit | **15.6 ms**: 2280 points, 810 distinct | no |

All rows were drawn on by hand on a Wacom DTH246 on 13 Sep 2026. Wintab's `pkTime` is filled on every packet because WinPenKit requests `PK_PKTBITS_ALL` in `lcPktData`. The Wintab specification calls it milliseconds and states no origin; a probe measured the origin as the `GetTickCount64` epoch (6217 packets over 41.7 s including a deliberate 5 s pause, `pkTime` advancing 41703 ms against 41703 ms of wall clock, offset within a 40 ms band).

WPF and Qt reach similar counts by opposite routes. WPF's clock resolves a millisecond (sixteen gaps of exactly 1000 µs appear through the stroke), but the timestamp belongs to the event, and events arrive on the 15.6 ms Windows timer tick (531 gaps of 16 ms, 329 of 15 ms). Qt delivers one event per point, but its clock advances only on the timer tick (smallest of 809 gaps is 15 ms). A finer clock would fix Qt and would not change WPF, which exposes no per-point time.

`POINTER_INFO` carries both `dwTime` (milliseconds on the `GetTickCount64` epoch) and `PerformanceCount` (QPC). They are two clocks, not two readings of one: they sat 27.08 ms apart across every sample.

**Synthetic input cannot measure a clock.** `InjectSyntheticPointerInput` stamps its own events. Through it, WM\_POINTER and WinUI both looked like 1 ms clocks (WinUI with a fixed sub-millisecond offset of 171 µs in one run and 622 µs in another) and Avalonia looked like it repeated values (113 for 172 points). Of five backends with an injected figure, four were wrong on hardware; only Qt's held. Wintab ignores injected input entirely. A greatest common divisor of the gaps is evidence of resolution only when the smallest gap is near it: Qt's gcd is 1000 µs because gcd(15000, 16000) is 1000, while no gap is under 15 ms.

**Wrapping.** A 32-bit millisecond counter repeats after 2³² ms, about 49.7 days of uptime; a signed `int` such as WPF's goes negative after about 24.9 days. Across that boundary, two points 1 ms apart would differ by about minus 49.7 days.

## How WinPenKit handles it

**Every backend queues, and the app polls** ([ARCHITECTURE.md decision 1](https://github.com/TheSevenPens/WinPenKit/blob/main/Docs/ARCHITECTURE.md)). Each session enqueues `PenPoint`s into a `ConcurrentQueue` on whichever thread produces them, and the app calls `DrainPoints()` from its render tick. `HasNewData` is a volatile flag set on every enqueue and cleared at the start of a drain. `DrainPoints(Span<PenPoint>)` fills at most the span's length and sets `HasNewData` back to true if points remain, so a caller that polls the flag does not leave points waiting after the pen lifts. `DrainPoints()` with no argument returns every queued point as an array, or an empty array. Both drains are thread-safe; call the other session members from the thread that created the session. On Wintab, `DrainPoints` also checks once a second that the driver still knows the context and reopens it if not, backing off to five seconds after a failed reopen ([WintabSessionBase.cs](https://github.com/TheSevenPens/WinPenKit/blob/main/WinPenKit/Wintab/WintabSessionBase.cs)).

**History replay.** [WmPointerSession.cs](https://github.com/TheSevenPens/WinPenKit/blob/main/WinPenKit/Pointer/WmPointerSession.cs) and [WinFormsPointerSession.cs](https://github.com/TheSevenPens/WinPenKit/blob/main/WinPenKit.WinForms/WinFormsPointerSession.cs) handle `WM_POINTERUPDATE` with a 64-entry `POINTER_PEN_INFO` buffer and take the history only when `count > 1`. If the returned `count` is larger than 64, they call `GetPointerPenInfoHistory` again with a buffer of `count` entries. They then replay from the last entry the buffer holds down to 0, and never read past the buffer. The native C ABI does the same. [WinUiPointerSession.cs](https://github.com/TheSevenPens/WinPenKit/blob/main/WinPenKit.WinUI/WinUiPointerSession.cs) replays `GetIntermediatePoints` in reverse and [AvaloniaPointerSession.cs](https://github.com/TheSevenPens/WinPenKit/blob/main/WinPenKit.Avalonia/AvaloniaPointerSession.cs) in forward order; both fall back to `GetCurrentPoint` when the collection is empty. [WpfStylusSession.cs](https://github.com/TheSevenPens/WinPenKit/blob/main/WinPenKit.Wpf/WpfStylusSession.cs) enqueues every point of `GetStylusPoints`.

**One unit, one contract.** `PenPoint.TimestampMicroseconds` is a `long` in microseconds on every backend. Values from one session never decrease, and the difference of two is elapsed microseconds; zero is a normal difference. The origin is deliberately unstated. `session.Conventions.Timestamp` names the clock ([PenConventions.cs](https://github.com/TheSevenPens/WinPenKit/blob/main/WinPenKit/PenConventions.cs)). `PenTimestampSource.None` means the backend supplied nothing and the field is zero; no session substitutes its own clock, which would measure when the library read the packet.

The conversions live in [PenTimestamp.cs](https://github.com/TheSevenPens/WinPenKit/blob/main/WinPenKit/PenTimestamp.cs):

* `FromPerformanceCount` (WM\_POINTER, WinForms) divides before multiplying, `(ticks / freq) * 1_000_000 + (ticks % freq) * 1_000_000 / freq`, because multiplying a 10 MHz counter by a million first overflows a signed 64-bit value after about 11 days of uptime. The division truncates, so the error is under 1 µs.
* `FromSystemTicks` (Wintab, WPF, Avalonia) anchors the raw reading to `Environment.TickCount64`: `extended = raw + round((TickCount64 - raw) / 2^32) * 2^32`, then multiplies by 1000. It is exact for a 32-bit source of either sign, a no-op for a true 64-bit source, and holds no state, so an idle session, the first packet after a wrap, and a gap in which the capture region discarded every packet all come back correct. It is valid only for a clock on the `GetTickCount` epoch, which was measured for all three sources. It replaced a backward-jump detector, which returned about minus 24.7 days for two WPF packets 25 days apart. Because the result is anchored, the WPF value is never negative.
* WinUI's value is cast to `long` with no anchoring. Whether it comes from a 32-bit millisecond clock underneath has not been traced; if it does, it wraps after about 49.7 days. Anchoring a clock that is truly 64-bit on another epoch would corrupt every reading, so it is left as it is.

Multiplying milliseconds by 1000 adds no resolution: on Wintab, WPF and Avalonia the last three digits are always `000`. Do not infer the clock from the value's remainder; read `Conventions.Timestamp`.

`dotnet run --project WinPenKit.TestConsole -- --selftest-clock` runs fifteen cases with no tablet, including both wraps and the epoch analysis. With the anchoring removed, the two wrap cases fail by exactly −4,294,967,295,000 µs. `--probe-wintab-epoch` records raw `pkTime` against the system clock through `WintabSessionBase.RawTimeObserver`, read before the capture region filters the packet.

## Traps

1. **Taking only the newest sample.** Reading `GetPointerPenInfo` or `GetCurrentPoint` alone drops the merged samples when the app falls behind. Symptom: long straight segments on fast strokes, with point spacing that grows with speed. This differs from the **Faceted** symptom in [Diagnosing a bad stroke](../../build-a-scribble-app/diagnosing-a-bad-stroke.md), where the angles come from quantized coordinates at any speed. Fix: recover the batch as in the table above.
2. **`count > 0` on `GetPointerPenInfoHistory`.** Pen data stops with no error. Fix: `count > 1`, and `GetPointerPenInfo` otherwise.
3. **Following Microsoft's documented order for WinUI.** Each batch is drawn backwards inside a stroke that still goes the right way overall, which looks like jitter. Fix: replay WinUI from the last index down; replay Avalonia from index 0 up.
4. **Not clamping the history count.** Microsoft documents that on success `entriesCount` is updated to the total number of entries available, which is not bounded by your buffer. Code that loops from `count - 1` without a check indexes past the array when more than 64 entries are coalesced. This has not been observed. Fix: call again with a buffer of `count` entries, or clamp `count` to the buffer size before the loop. WinPenKit (managed and native) does the first and never reads past its buffer.
5. **Dividing by a timestamp difference.** WPF gives about three points per value, Qt the same, and a recovered Avalonia batch shares one. Fix: guard zero, and treat a WPF batch as points sharing one instant, or interpolate across it knowing the values are invented.
6. **Reading one timestamp on its own, or comparing two backends.** The origin differs per backend. To align with wall-clock time, calibrate per session and keep the smallest offset:

   ```csharp
   long offsetUs = long.MaxValue;
   // per point:
   long nowUs = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds() * 1000;
   offsetUs = Math.Min(offsetUs, nowUs - pt.TimestampMicroseconds);
   // any point:
   var wall = DateTimeOffset.FromUnixTimeMilliseconds((pt.TimestampMicroseconds + offsetUs) / 1000);
   ```

   Each sample overestimates the offset by that point's handler latency, so a single sample can be 26 ms out. Recalibrate after switching backend. On WPF the calibration is bounded by the 1 ms clock; on Qt the 15.6 ms is the clock.
7. **Mixing `dwTime` and `PerformanceCount`.** They are 27.08 ms apart. Use one.
8. **Trusting a declared 64-bit type.** Avalonia's and Qt's timestamps are 64-bit properties filled from 32-bit `GetMessageTime`, so they have already wrapped. Fix: anchor them as `FromSystemTicks` does.
9. **Measuring resolution with synthetic input, or with a gcd alone.** Injection sets the floor it appears to measure. Fix: draw by hand, and quote the smallest gap with the gcd.

## Further reading

* [Stage 2: Delivery](2-delivery.md) for how packets reach the session and the poll loop.
* [Stage 7: The output contract](7-output.md) for the rest of `PenPoint`.
* [Stage 8: Verifying the pipeline](8-verifying.md) for checking point counts and gaps.
* [Position smoothing](../../processing-pen-data/position-smoothing.md), which consumes timestamps.
* [Build a Scribble app](../../build-a-scribble-app/README.md) and WinPenKit's [HOW\_TO\_USE.md](https://github.com/TheSevenPens/WinPenKit/blob/main/Docs/HOW_TO_USE.md), whose timestamp section is the measurement record (its statements about Avalonia's conversion, negative WPF values, and wrap handling on every backend are out of date; this page follows the code).
