# Generating the symptom images

> Tracked in [#8](https://github.com/TheSevenPens/devnotes/issues/8).

The four symptom illustrations in [Diagnosing a bad stroke](diagnosing-a-bad-stroke.md) come out of a script rather than a screen capture. This page explains why, and gives the script.

## Why generate them

A screenshot of a real fault carries everything else that was on screen at the time: window chrome, a different brush size, a different stroke, a different display scale. Two screenshots taken a week apart differ in a dozen ways, and a reader cannot tell which difference matters.

A generated image fixes every variable except the fault. The clean image and the faceted image come from the same path, the same brush, the same canvas, the same magnification. The only thing that changes is the one line that introduces the fault.

That has a second use beyond illustration. **Each fault below is a known-bad input you can point your own checks at.** Section 6 of the diagnosis page argues that a check nobody has seen fail is not yet a check; this script is one way to make each check fail on demand.

## The part that took three attempts

Express everything in **device pixels**, then magnify once at the end by a single constant.

The temptation is to tune each image separately until it looks convincing. That destroys the comparison. Two specific ways it goes wrong:

- **Magnifying with nearest-neighbour makes every image look pixelated**, so faceting and blockiness become indistinguishable. That is exactly the confusion the page exists to resolve.
- **Scaling one fault differently from the others** misrepresents its size. An early draft scaled the 44% surface by the magnification factor as well, which shrank its pixels by a factor of six and produced an image that looked perfectly clean.

Both faults are real, and both were introduced by the person drawing the illustrations rather than by any application.

So: `ZOOM` converts device pixels to image pixels, and nothing else does. A coordinate rounded to one device pixel and a surface rendered at 44% both scale by the same factor, which keeps the images comparable.

## What each fault does

| image | construction | what stays correct |
| --- | --- | --- |
| clean | the reference path, unmodified | everything |
| faceted | every coordinate rounded to a whole device pixel | the surface |
| blocky | rendered onto a surface holding 44% of the pixels it needs, magnified back with no filtering | the path |
| soft | the finished surface resampled to sit 0.64 device pixels off the grid vertically | the path and the resolution |
| lumpy | width varied by a signal the pressure data does not carry | the path |

The numbers come from real faults: 44% was `Scribble.Avalonia` and `Scribble.WinUI`, and 0.64px was `Scribble.Wpf`.

## The script

Lives at `images/make-symptom-images.py`. It needs Pillow, and WinPenKit checked out beside devnotes for the reference stroke.

```python
import csv
import math
import os

from PIL import Image, ImageDraw

ZOOM = 6                 # image pixels per device pixel
DEV_W, DEV_H = 140, 50   # canvas, in device pixels
BRUSH_DEV = 3.0          # stroke width, in device pixels

SURFACE_FRACTION = 0.44  # the real Avalonia and WinUI fault
OFFSET_DEV = 0.64        # the real WPF fault, in device pixels

SS = 3                   # supersample, because PIL draws aliased lines
INK = (24, 26, 30)
PAPER = (251, 250, 247)

W, H = DEV_W * ZOOM, DEV_H * ZOOM
STROKE_CSV = os.path.join('..', '..', '..', 'WinPenKit', 'testdata', 'reference-stroke.csv')


def load_reference():
    """A slow curving stretch of the reference stroke, in device pixels."""
    pts = []
    with open(STROKE_CSV) as f:
        for row in csv.DictReader(r for r in f if not r.startswith('#')):
            pts.append((float(row['desktopX']), float(row['desktopY'])))
    pts = pts[120:300]

    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    scale = min((DEV_W - 16) / (max(xs) - min(xs)), (DEV_H - 16) / (max(ys) - min(ys)))
    ox = (DEV_W - (max(xs) - min(xs)) * scale) / 2 - min(xs) * scale
    oy = (DEV_H - (max(ys) - min(ys)) * scale) / 2 - min(ys) * scale
    return [(x * scale + ox, y * scale + oy) for x, y in pts]


def draw_path(points, px_per_dev, out_size, widths=None):
    """Antialiased polyline. Points arrive in device pixels."""
    w, h = out_size
    img = Image.new('RGB', (w * SS, h * SS), PAPER)
    d = ImageDraw.Draw(img)

    for i in range(len(points) - 1):
        x1 = points[i][0] * px_per_dev * SS
        y1 = points[i][1] * px_per_dev * SS
        x2 = points[i + 1][0] * px_per_dev * SS
        y2 = points[i + 1][1] * px_per_dev * SS
        lw = (widths[i] if widths else BRUSH_DEV) * px_per_dev * SS
        d.line([(x1, y1), (x2, y2)], fill=INK, width=max(1, int(round(lw))))
        r = lw / 2
        d.ellipse([x1 - r, y1 - r, x1 + r, y1 + r], fill=INK)

    return img.resize((w, h), Image.LANCZOS)


def magnify(img):
    """Show the device pixels. Every image depicts the same 6x view of a screen."""
    return img.resize((W, H), Image.NEAREST)


def main():
    pts = load_reference()

    # Clean. The path as a digitizer reports it.
    clean = draw_path(pts, 1, (DEV_W, DEV_H))
    magnify(clean).save('symptom-clean.png')

    # Faceted. Each coordinate rounded to a whole device pixel. The surface holds
    # the pixels it should and the path turns angular, which is what an
    # integer-typed coordinate API produces.
    magnify(draw_path([(round(x), round(y)) for x, y in pts], 1, (DEV_W, DEV_H))) \
        .save('symptom-faceted.png')

    # Blocky. A surface holding 44% of the pixels it needs, magnified back with no
    # filtering. The path stays correct and the pixels grow.
    small = draw_path(pts, SURFACE_FRACTION,
                      (round(DEV_W * SURFACE_FRACTION), round(DEV_H * SURFACE_FRACTION)))
    small.resize((W, H), Image.NEAREST).save('symptom-blocky.png')

    # Soft. The finished surface resampled to sit 0.64 device pixels off the pixel
    # grid vertically. Every edge picks up a row of intermediate greys and the path
    # does not move.
    soft = clean.transform(clean.size, Image.AFFINE, (1, 0, 0, 0, 1, -OFFSET_DEV),
                           resample=Image.BILINEAR, fillcolor=PAPER)
    magnify(soft).save('symptom-soft.png')

    # Lumpy. The path stays correct and the width carries a fault.
    widths = [BRUSH_DEV * (1 + 0.45 * math.sin(i * 0.30)) for i in range(len(pts))]
    magnify(draw_path(pts, 1, (DEV_W, DEV_H), widths=widths)).save('symptom-lumpy.png')


if __name__ == '__main__':
    main()
```

## Two details worth keeping if you adapt it

**The supersample.** Pillow draws aliased lines, so `draw_path` renders at three times the target size and downsamples with Lanczos. Without that, every image carries stair-stepped edges of its own and the soft and blocky faults disappear into the noise.

**The round joins.** Each segment gets an ellipse at its start. A polyline drawn as separate segments notches at every join where the width changes, and the lumpy image is entirely about width changes.

## Turning these into test input

The images demonstrate the faults. The same constructions produce input for a check:

- **Faceted** applies `round()` to a coordinate. Feed the rounded path to your conversion and `L3.conversion-snap` should report close to 100%.
- **Blocky** allocates a surface at 44%. Your surface check should report the shortfall and name the percentage.
- **Soft** offsets by 0.64. Your alignment check should report a fractional offset on one axis and a whole number on the other.

If any of those passes, the check cannot detect the fault it exists for.
