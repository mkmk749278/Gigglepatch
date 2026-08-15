"""The pass that makes a composited frame look like one picture.

The character is a generated render — soft gradients, subsurface warmth, real
specular falloff. The locations are flat vector fills. Composite them raw and
the eye reads two different pictures stacked, however well the animation moves;
the character looks pasted on. That is not a drawing problem, it is a
compositing one, and it is fixed after the fact rather than in the artwork.

Four things do almost all of the work, in order of how much they matter:

    contact shadow   anchors the figure to the floor instead of floating
    depth of field   puts the background on a different focal plane, which is
                     the single strongest cue that it is *behind* rather than
                     *behind-and-pasted*
    shared grade     one light source, one contrast curve, one colour cast over
                     everything, so both layers agree about the weather
    grain            a common noise floor. Flat vector fills have none at all,
                     which is exactly what makes them read as clip art

None of this touches the rig, and none of it needs new artwork.
"""
import numpy as np
from PIL import Image, ImageDraw, ImageFilter


def soften(bg, blur=0.0032, desat=0.16, lift=0.05):
    """Push a background back: defocus it, drain it, flatten its contrast.

    Done once per shot on the still, not per frame — it is far too expensive to
    blur a 1080p image 120 times for no gain.
    """
    w, h = bg.size
    out = bg.convert('RGBA').filter(ImageFilter.GaussianBlur(max(w * blur, 0.6)))
    a = np.asarray(out).astype(np.float32)
    rgb = a[..., :3]
    grey = rgb @ np.array([0.299, 0.587, 0.114], np.float32)
    rgb = rgb + (grey[..., None] - rgb) * desat          # toward neutral
    rgb = 255.0 - (255.0 - rgb) * (1.0 - lift)           # raise the black point
    a[..., :3] = np.clip(rgb, 0, 255)
    return Image.fromarray(a.astype(np.uint8))


def contact_shadow(frame, x, y, rx, ry=None, alpha=86, squash=0.26):
    """A soft ellipse under the figure, darkest at the centre.

    A single flat ellipse reads as a sticker in its own right. Two stacked —
    one tight and dark, one wide and faint — gives the falloff a real contact
    shadow has, where the darkest part is directly under the weight.
    """
    ry = ry or rx * squash
    layer = Image.new('RGBA', frame.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.ellipse((x - rx * 1.5, y - ry * 1.5, x + rx * 1.5, y + ry * 1.5),
              fill=(38, 28, 22, int(alpha * 0.42)))
    d.ellipse((x - rx * 0.62, y - ry * 0.62, x + rx * 0.62, y + ry * 0.62),
              fill=(32, 24, 18, alpha))
    layer = layer.filter(ImageFilter.GaussianBlur(rx * 0.22))
    frame.alpha_composite(layer)
    return frame


def _vignette(size, strength=0.20):
    w, h = size
    ys = np.linspace(-1.0, 1.0, h, dtype=np.float32)[:, None]
    xs = np.linspace(-1.0, 1.0, w, dtype=np.float32)[None, :]
    r = np.sqrt(xs * xs * 0.86 + ys * ys)
    return (1.0 - strength * np.clip((r - 0.55) / 0.85, 0, 1) ** 1.6)


class Grade:
    """One look applied to the whole frame, character and background alike.

    Holds the vignette and the grain tile, because both depend only on frame
    size and rebuilding them every frame is pure waste. The grain is cycled
    rather than regenerated so it stays cheap while still moving — static grain
    over moving picture reads as dirt on the lens.
    """

    def __init__(self, size, warmth=0.055, contrast=0.13, bloom=0.16,
                 vignette=0.20, grain=2.4, seed=7):
        self.size = size
        self.warmth, self.contrast, self.bloom = warmth, contrast, bloom
        self.vig = _vignette(size, vignette)[..., None]
        rng = np.random.default_rng(seed)
        self.grain = [rng.normal(0, grain, (size[1], size[0], 1)).astype(np.float32)
                      for _ in range(5)]

    def __call__(self, frame, t=0.0, i=0):
        a = np.asarray(frame.convert('RGBA')).astype(np.float32)
        rgb = a[..., :3] / 255.0

        # bloom: bright areas bleed a little, which is what ties a rendered
        # figure to a sunlit background more than any amount of colour matching
        if self.bloom > 0:
            hi = np.clip((rgb - 0.72) / 0.28, 0, 1)
            glow = np.asarray(Image.fromarray((hi * 255).astype(np.uint8))
                              .filter(ImageFilter.GaussianBlur(
                                  max(self.size[0] * 0.006, 1)))
                              ).astype(np.float32) / 255.0
            rgb = 1.0 - (1.0 - rgb) * (1.0 - glow * self.bloom)

        # gentle S-curve — the same one over both layers
        rgb = np.clip(rgb, 0, 1)
        rgb = rgb + self.contrast * (rgb * (1.0 - rgb) * (rgb - 0.5)) * 4.0

        # one light: warm the highlights, cool the shadows very slightly
        luma = rgb @ np.array([0.299, 0.587, 0.114], np.float32)
        w = self.warmth
        rgb[..., 0] += w * luma * 1.00
        rgb[..., 1] += w * luma * 0.42
        rgb[..., 2] -= w * (1.0 - luma) * 0.55

        rgb = rgb * self.vig
        out = np.clip(rgb, 0, 1) * 255.0 + self.grain[i % len(self.grain)]
        a[..., :3] = np.clip(out, 0, 255)
        frame.paste(Image.fromarray(a.astype(np.uint8)))
        return frame
