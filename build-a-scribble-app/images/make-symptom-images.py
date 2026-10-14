"""Generate the symptom illustrations for diagnosing-a-bad-stroke.md.

Every image draws the same path, taken from WinPenKit's reference stroke, with
one fault applied. None of them captures a real bug: each fault gets introduced
deliberately, so the only thing that differs between images stays the fault.

All five depict a view zoomed to ZOOM, which is what the page asks a reader to
do before judging a stroke. Working in device pixels and multiplying up keeps
each fault at its true size relative to the others: a coordinate rounded to one
device pixel and a surface rendered at 44% both scale by the same factor, so the
images stay comparable.

Run from this directory, with the WinPenKit checkout beside devnotes:

    python make-symptom-images.py
"""

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


def save(img, name):
    img.save(name, 'PNG')
    print(f'  {name}  {img.width}x{img.height}')


def magnify(img):
    """Show the device pixels. Every image depicts the same 6x view of a screen."""
    return img.resize((W, H), Image.NEAREST)


def main():
    pts = load_reference()

    # Every surface below holds one pixel per device pixel, except the blocky one,
    # which is the whole point of that image. Rendering them all at device
    # resolution and magnifying the same way keeps the comparison fair: the only
    # difference between any two images is the fault.

    # Clean. The path as a digitizer reports it.
    clean = draw_path(pts, 1, (DEV_W, DEV_H))
    save(magnify(clean), 'symptom-clean.png')

    # Faceted. Each coordinate rounded to a whole device pixel. The surface holds
    # the pixels it should and the path turns angular, which is what an
    # integer-typed coordinate API produces.
    save(magnify(draw_path([(round(x), round(y)) for x, y in pts], 1, (DEV_W, DEV_H))),
         'symptom-faceted.png')

    # Blocky. A surface holding 44% of the pixels it needs, magnified back with no
    # filtering. The path stays correct and the pixels grow.
    small = draw_path(pts, SURFACE_FRACTION,
                      (round(DEV_W * SURFACE_FRACTION), round(DEV_H * SURFACE_FRACTION)))
    save(small.resize((W, H), Image.NEAREST), 'symptom-blocky.png')

    # Soft. The finished surface resampled to sit 0.64 device pixels off the pixel
    # grid vertically. Every edge picks up a row of intermediate greys and the path
    # does not move.
    soft = clean.transform(clean.size, Image.AFFINE, (1, 0, 0, 0, 1, -OFFSET_DEV),
                           resample=Image.BILINEAR, fillcolor=PAPER)
    save(magnify(soft), 'symptom-soft.png')

    # Lumpy. The path stays correct and the width carries a fault.
    widths = [BRUSH_DEV * (1 + 0.45 * math.sin(i * 0.30)) for i in range(len(pts))]
    save(magnify(draw_path(pts, 1, (DEV_W, DEV_H), widths=widths)), 'symptom-lumpy.png')


if __name__ == '__main__':
    main()
