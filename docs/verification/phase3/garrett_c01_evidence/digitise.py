"""Log-log chart digitiser: calibrate from the plot frame, trace a line pixel by pixel."""
import math, sys, numpy as np, pypdfium2 as pdfium
PDF = sys.argv[1] if len(sys.argv) > 1 else None
SCALE = 4.0

def render(pdf, page):
    img = pdfium.PdfDocument(pdf)[page - 1].render(scale=SCALE).to_pil().convert("L")
    return np.asarray(img, dtype=np.int16)

def lines(a, axis, thresh=110, frac=0.55):
    dark = a < thresh
    f = dark.mean(axis=axis)
    idx = np.where(f > frac)[0]
    groups, cur = [], [idx[0]] if len(idx) else []
    for i in idx[1:]:
        if i - cur[-1] <= 2: cur.append(i)
        else: groups.append(cur); cur = [i]
    if cur: groups.append(cur)
    return [(g[0], g[-1]) for g in groups]

def frame(a):
    # Gridline darkness varies by page; raise the threshold until a full grid appears.
    for thresh in (110, 140, 170, 200):
        rows = lines(a, 1, thresh=thresh, frac=0.45)
        cols = lines(a, 0, thresh=thresh, frac=0.30)
        if len(rows) >= 8 and len(cols) >= 8:
            break
    top, bottom = rows[0], rows[-1]
    left, right = cols[0], cols[-1]
    return left, right, top, bottom, rows, cols

class Chart:
    def __init__(self, pdf, page, xdec, ydec):
        self.a = render(pdf, page)
        l, r, t, b, self.rows, self.cols = frame(self.a)
        self.x0, self.x1 = (l[0] + l[1]) / 2, (r[0] + r[1]) / 2
        self.y0, self.y1 = (b[0] + b[1]) / 2, (t[0] + t[1]) / 2   # y0 = bottom
        # The left frame line spans the full plot height; use its longest dark run
        # (gridlines can be too faint to detect at the bottom edge).
        col = self.a[:, int(round(self.x0))] < 170
        best, start = (0, 0, 0), None
        for i, d in enumerate(list(col) + [False]):
            if d and start is None: start = i
            elif not d and start is not None:
                if i - start > best[0]: best = (i - start, start, i - 1)
                start = None
        if best[0] > 0.5 * (self.y0 - self.y1) and best[0] > 400:
            self.y1, self.y0 = min(self.y1, float(best[1])), max(self.y0, float(best[2]))
        self.xd, self.yd = xdec, ydec   # (log10 min, log10 max)
    def px(self, x):
        return self.x0 + (math.log10(x) - self.xd[0]) / (self.xd[1] - self.xd[0]) * (self.x1 - self.x0)
    def val_y(self, py):
        return 10 ** (self.yd[0] + (self.y0 - py) / (self.y0 - self.y1) * (self.yd[1] - self.yd[0]))
    def py(self, y):
        return self.y0 - (math.log10(y) - self.yd[0]) / (self.yd[1] - self.yd[0]) * (self.y0 - self.y1)
    def runs(self, col):
        c = self.a[int(self.y1) + 3:int(self.y0) - 3, col] < 110
        grid = set()
        for r0, r1 in self.rows:
            grid.update(range(r0 - 1, r1 + 2))
        out, start = [], None
        for i, d in enumerate(c):
            y = i + int(self.y1) + 3
            if d and y not in grid:
                start = y if start is None else start
            elif start is not None and not (d and y in grid):
                if y - start >= 3: out.append((start, y - 1))
                start = None
        return out
    def trace(self, x, expect, window=0.25):
        """Line centre near expected cost (log-window), averaged over 5 nearby columns off gridlines."""
        base = int(round(self.px(x)))
        vgrid = set()
        for c0, c1 in self.cols:
            vgrid.update(range(c0 - 2, c1 + 3))
        cols = [c for c in range(base - 12, base + 13) if c not in vgrid][:9]
        ys = []
        for col in cols:
            cands = [((r0 + r1) / 2, r1 - r0 + 1) for r0, r1 in self.runs(col)]
            cands = [(y, w) for y, w in cands if abs(math.log10(self.val_y(y)) - math.log10(expect)) < window and w <= 40]
            if cands:
                ys.append(min(cands, key=lambda t: abs(math.log10(self.val_y(t[0])) - math.log10(expect)))[0])
        if not ys: return None, 0
        # Slope correction: columns straddle x; fit a line y(col) would be better, but 9 cols span <1% in x.
        return self.val_y(float(np.median(ys))), len(ys)
