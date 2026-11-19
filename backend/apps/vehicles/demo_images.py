"""Original illustrations used by the demo data command.

Everything is drawn with Pillow, so no external photos (and no licences) are
involved. The images are stylised drawings, not photographs.
"""

import io
import math
import random

from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageOps

SS = 2  # supersampling factor: drawn at 2x and shrunk for smooth edges

THEMES = {
    "dusk": {
        "top": (43, 43, 43),
        "bottom": (23, 23, 23),
        "road": (18, 18, 18),
        "curb": (42, 42, 42),
        "sun": (255, 199, 0),
        "buildings": [(42, 42, 42), (27, 27, 27)],
        "window": (255, 199, 0),
    },
    "day": {
        "top": (190, 214, 245),
        "bottom": (233, 241, 251),
        "road": (70, 74, 80),
        "curb": (150, 154, 160),
        "sun": (255, 235, 160),
        "buildings": [(170, 184, 205), (142, 158, 184)],
        "window": (255, 255, 255),
    },
    "dawn": {
        "top": (84, 60, 110),
        "bottom": (240, 150, 110),
        "road": (40, 36, 44),
        "curb": (90, 80, 96),
        "sun": (255, 214, 140),
        "buildings": [(68, 50, 84), (46, 34, 60)],
        "window": (255, 214, 140),
    },
}

YELLOW = (255, 199, 0)


# ---------------------------------------------------------------- helpers


def hex_to_rgb(value):
    value = value.lstrip("#")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))


def _mix(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _gradient(width, height, top, bottom):
    image = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(image)
    for y in range(height):
        draw.line([(0, y), (width, y)], fill=_mix(top, bottom, y / max(1, height - 1)))
    return image


def _quad(p0, p1, p2, steps=12):
    return [
        (
            (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t**2 * p2[0],
            (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t**2 * p2[1],
        )
        for t in (i / steps for i in range(steps + 1))
    ]


def _cubic(p0, p1, p2, p3, steps=16):
    points = []
    for i in range(steps + 1):
        t = i / steps
        u = 1 - t
        points.append(
            (
                u**3 * p0[0] + 3 * u**2 * t * p1[0] + 3 * u * t**2 * p2[0] + t**3 * p3[0],
                u**3 * p0[1] + 3 * u**2 * t * p1[1] + 3 * u * t**2 * p2[1] + t**3 * p3[1],
            )
        )
    return points


def _path(commands):
    """Turns M/L/Q/C commands into a list of points (curves are sampled)."""
    points = []
    current = None
    for command, *args in commands:
        if command in ("M", "L"):
            current = (args[0], args[1])
            points.append(current)
        elif command == "Q":
            control, end = (args[0], args[1]), (args[2], args[3])
            points.extend(_quad(current, control, end)[1:])
            current = end
        elif command == "C":
            c1, c2, end = (args[0], args[1]), (args[2], args[3]), (args[4], args[5])
            points.extend(_cubic(current, c1, c2, end)[1:])
            current = end
    return points


def _font(size):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def _jpeg(image, quality=82):
    buffer = io.BytesIO()
    image.convert("RGB").save(buffer, format="JPEG", quality=quality, optimize=True)
    return buffer.getvalue()


def _centered_text(draw, center, text, font, fill):
    try:
        draw.text(center, text, font=font, fill=fill, anchor="mm")
    except ValueError:
        length = draw.textlength(text, font=font)
        draw.text((center[0] - length / 2, center[1] - 10), text, font=font, fill=fill)


def _caption(image, text):
    width, height = image.size
    bar = int(height * 0.12)
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rectangle([0, height - bar, width, height], fill=(0, 0, 0, 150))
    _centered_text(
        draw, (width // 2, height - bar // 2), text, _font(int(bar * 0.5)), (255, 255, 255, 255)
    )
    return Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")


# ------------------------------------------------------------- background


def _background(width, height, palette, horizon, seed):
    rnd = random.Random(seed)
    image = _gradient(width, height, palette["top"], palette["bottom"])
    draw = ImageDraw.Draw(image)

    radius = int(height * 0.22)
    cx = int(width * (0.3 + 0.4 * rnd.random()))
    cy = int(horizon - height * 0.1)
    draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=palette["sun"])

    for layer, tone in enumerate(palette["buildings"]):
        low, high = (0.10, 0.30) if layer == 0 else (0.06, 0.20)
        x = -int(rnd.random() * 60 * SS)
        while x < width:
            w = rnd.randint(70, 150) * SS
            h = int(height * rnd.uniform(low, high))
            top = horizon - h
            draw.rectangle([x, top, x + w, horizon], fill=tone)
            if layer == 1:
                for wy in range(top + 20 * SS, horizon - 14 * SS, 34 * SS):
                    for wx in range(x + 14 * SS, x + w - 22 * SS, 28 * SS):
                        if rnd.random() < 0.3:
                            draw.rectangle(
                                [wx, wy, wx + 12 * SS, wy + 16 * SS], fill=palette["window"]
                            )
            x += w + rnd.randint(4, 16) * SS

    draw.rectangle([0, horizon, width, height], fill=palette["road"])
    draw.rectangle([0, horizon, width, horizon + 14 * SS], fill=palette["curb"])
    dash_y = int(height * 0.94)
    for x in range(-60 * SS, width, 230 * SS):
        draw.rectangle([x, dash_y, x + 130 * SS, dash_y + 12 * SS], fill=YELLOW)
    return image


# ------------------------------------------------------------------- car


def _draw_car(draw, image, width, ground, zoom, focus, color, palette, scratch):
    scale = (0.72 * width / 680) * zoom
    focus_x = 25 + 653 * focus
    ox = width / 2 - focus_x * scale
    oy = ground - 204 * scale

    def pt(x, y):
        return (ox + x * scale, oy + y * scale)

    def polygon(points, fill):
        draw.polygon([pt(x, y) for x, y in points], fill=fill)

    shadow = _mix(palette["road"], (0, 0, 0), 0.6)
    draw.ellipse([*pt(5, 194), *pt(695, 218)], fill=shadow)

    body = _path(
        [
            ("M", 25, 160),
            ("L", 25, 128),
            ("Q", 25, 108, 50, 104),
            ("L", 120, 96),
            ("C", 150, 60, 185, 22, 255, 14),
            ("L", 400, 14),
            ("C", 455, 16, 500, 48, 545, 92),
            ("L", 625, 104),
            ("Q", 672, 112, 678, 140),
            ("L", 678, 160),
        ]
    )
    polygon(body, color)

    # Darker lower band, clipped to the body shape.
    body_mask = Image.new("L", image.size, 0)
    ImageDraw.Draw(body_mask).polygon([pt(x, y) for x, y in body], fill=255)
    band_mask = Image.new("L", image.size, 0)
    ImageDraw.Draw(band_mask).rectangle([*pt(0, 136), *pt(700, 166)], fill=255)
    band = Image.new("RGB", image.size, _mix(color, (0, 0, 0), 0.2))
    image.paste(band, (0, 0), ImageChops.multiply(body_mask, band_mask))

    draw.line([pt(40, 128), pt(668, 128)], fill=YELLOW, width=max(2, int(5 * scale)))

    window = (22, 22, 22)
    polygon(
        _path(
            [
                ("M", 140, 94),
                ("C", 168, 58, 195, 32, 250, 28),
                ("L", 318, 28),
                ("L", 318, 94),
            ]
        ),
        window,
    )
    polygon(
        _path(
            [
                ("M", 336, 28),
                ("L", 398, 28),
                ("C", 440, 30, 475, 56, 508, 94),
                ("L", 336, 94),
            ]
        ),
        window,
    )

    draw.rounded_rectangle([*pt(288, 104), *pt(316, 109)], radius=2, fill=_mix(color, (0, 0, 0), 0.4))
    draw.rounded_rectangle([*pt(652, 112), *pt(678, 124)], radius=4 * SS, fill=(255, 246, 204))
    draw.rounded_rectangle([*pt(25, 110), *pt(35, 126)], radius=3 * SS, fill=(255, 90, 54))

    for cx in (140, 545):
        for radius, fill in ((56, (14, 14, 14)), (44, (26, 26, 26)), (29, (216, 216, 216))):
            draw.ellipse(
                [*pt(cx - radius, 160 - radius), *pt(cx + radius, 160 + radius)], fill=fill
            )
        for i in range(5):
            angle = math.radians(i * 72 - 90)
            draw.line(
                [pt(cx, 160), pt(cx + 27 * math.cos(angle), 160 + 27 * math.sin(angle))],
                fill=(141, 141, 141),
                width=max(2, int(5 * scale)),
            )
        draw.ellipse([*pt(cx - 8, 152), *pt(cx + 8, 168)], fill=(43, 43, 43))

    if scratch:
        scratch_points = [pt(330, 98), pt(372, 112), pt(420, 100), pt(470, 116)]
        draw.line(scratch_points, fill=(220, 40, 40), width=max(3, int(5 * scale)))


# ------------------------------------------------------------------ bike


def _draw_bike(draw, width, ground, zoom, focus, color, palette):
    scale = (0.62 * width / 600) * zoom
    focus_x = 150 + 600 * focus
    ox = width / 2 - focus_x * scale
    oy = ground - 310 * scale

    def pt(x, y):
        return (ox + x * scale, oy + y * scale)

    def stroke(points, fill, weight):
        coords = [pt(x, y) for x, y in points]
        w = max(2, int(weight * scale))
        draw.line(coords, fill=fill, width=w, joint="curve")
        for x, y in coords:
            draw.ellipse([x - w / 2, y - w / 2, x + w / 2, y + w / 2], fill=fill)

    shadow = _mix(palette["road"], (0, 0, 0), 0.6)
    draw.ellipse([*pt(120, 300), *pt(780, 324)], fill=shadow)

    for cx, cy in ((260, 200), (640, 200)):
        draw.ellipse(
            [*pt(cx - 100, cy - 100), *pt(cx + 100, cy + 100)],
            outline=(208, 208, 208),
            width=max(2, int(5 * scale)),
        )
        for i in range(16):
            angle = math.radians(i * 22.5)
            draw.line(
                [pt(cx, cy), pt(cx + 98 * math.cos(angle), cy + 98 * math.sin(angle))],
                fill=(122, 122, 122),
                width=max(1, int(2 * scale)),
            )
        draw.ellipse(
            [*pt(cx - 110, cy - 110), *pt(cx + 110, cy + 110)],
            outline=(10, 10, 10),
            width=max(3, int(16 * scale)),
        )
        draw.ellipse([*pt(cx - 10, cy - 10), *pt(cx + 10, cy + 10)], fill=YELLOW)

    stroke([(440, 205), (405, 92), (585, 82), (595, 118), (440, 205)], color, 12)
    stroke([(405, 96), (260, 200), (440, 205)], color, 12)
    stroke([(585, 82), (595, 118), (640, 200)], color, 12)
    stroke([(585, 82), (582, 58)], color, 12)
    stroke([(556, 56), (614, 56)], (242, 242, 242), 10)
    stroke([(405, 92), (399, 70)], color, 12)
    draw.rounded_rectangle([*pt(366, 60), *pt(434, 73)], radius=6 * SS, fill=(242, 242, 242))
    draw.ellipse(
        [*pt(416, 181), *pt(464, 229)], outline=YELLOW, width=max(2, int(6 * scale))
    )
    stroke([(440, 205), (418, 250)], (242, 242, 242), 7)
    draw.rounded_rectangle([*pt(402, 246), *pt(432, 255)], radius=4 * SS, fill=(242, 242, 242))


# ----------------------------------------------------------- public API


def render_vehicle(
    kind,
    color,
    *,
    theme="dusk",
    zoom=1.0,
    focus=0.5,
    seed=0,
    size=(1200, 800),
    mirror=False,
    scratch=False,
    label=None,
):
    """A side view of a car or bike. `color` is a hex string like "#2F5D9E"."""
    width, height = size[0] * SS, size[1] * SS
    palette = THEMES[theme]
    horizon = int(height * 0.62)
    ground = int(height * (0.80 if zoom <= 1 else 0.90))
    image = _background(width, height, palette, horizon, seed)
    draw = ImageDraw.Draw(image)
    rgb = hex_to_rgb(color)

    if kind == "bike":
        _draw_bike(draw, width, ground, zoom, focus, rgb, palette)
    else:
        _draw_car(draw, image, width, ground, zoom, focus, rgb, palette, scratch)

    if mirror:
        image = ImageOps.mirror(image)
    image = image.resize(size, Image.LANCZOS)
    if label:
        image = _caption(image, label)
    return _jpeg(image)


def render_dashboard(fuel_percent, *, label=None, size=(900, 600)):
    """A simple fuel gauge, used for the dashboard inspection photo."""
    width, height = size
    image = _gradient(width, height, (38, 38, 38), (14, 14, 14))
    draw = ImageDraw.Draw(image)
    cx, cy, radius = width // 2, int(height * 0.52), int(height * 0.32)

    draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], outline=(90, 90, 90), width=10)
    for tick in range(0, 101, 10):
        angle = math.radians(210 - 240 * tick / 100)
        outer, inner = radius - 18, radius - 50
        draw.line(
            [
                (cx + math.cos(angle) * outer, cy - math.sin(angle) * outer),
                (cx + math.cos(angle) * inner, cy - math.sin(angle) * inner),
            ],
            fill=(200, 200, 200),
            width=6,
        )

    value = max(0, min(100, fuel_percent))
    angle = math.radians(210 - 240 * value / 100)
    tip = radius - 30
    draw.line(
        [(cx, cy), (cx + math.cos(angle) * tip, cy - math.sin(angle) * tip)],
        fill=YELLOW,
        width=12,
    )
    draw.ellipse([cx - 16, cy - 16, cx + 16, cy + 16], fill=YELLOW)
    _centered_text(draw, (cx, cy + int(radius * 0.55)), f"{value}%", _font(int(height * 0.12)), (255, 255, 255))

    image = image.convert("RGB")
    if label:
        image = _caption(image, label)
    return _jpeg(image)


ANGLE_VIEWS = {
    "front": {"zoom": 1.7, "focus": 1.0},
    "rear": {"zoom": 1.7, "focus": 0.0},
    "left": {"zoom": 1.0, "focus": 0.5},
    "right": {"zoom": 1.0, "focus": 0.5, "mirror": True},
}


def render_inspection(
    kind, color, angle, phase, *, seed=0, fuel=None, scratch=False, size=(900, 600)
):
    """One inspection photo (start or end of a trip) for the given angle."""
    label = f"{phase.upper()} - {angle.upper()}"
    if angle == "dashboard":
        return render_dashboard(fuel if fuel is not None else 50, label=label, size=size)
    return render_vehicle(
        kind,
        color,
        theme="day",
        seed=seed,
        size=size,
        label=label,
        scratch=scratch and angle == "right",
        **ANGLE_VIEWS[angle],
    )


def render_document(doc_type, *, size=(900, 600)):
    """A clearly marked sample document image for the verification queue."""
    width, height = size
    image = _gradient(width, height, (226, 230, 236), (196, 202, 212))
    draw = ImageDraw.Draw(image)

    if doc_type == "selfie":
        draw.ellipse(
            [width * 0.36, height * 0.12, width * 0.64, height * 0.52], fill=(214, 178, 150)
        )
        draw.pieslice(
            [width * 0.22, height * 0.5, width * 0.78, height * 1.3],
            180,
            360,
            fill=(70, 84, 110),
        )
        draw.rounded_rectangle(
            [width * 0.58, height * 0.6, width * 0.9, height * 0.85],
            radius=14,
            fill=(250, 250, 250),
            outline=(120, 120, 120),
            width=3,
        )
    else:
        draw.rounded_rectangle(
            [width * 0.1, height * 0.14, width * 0.9, height * 0.86],
            radius=24,
            fill=(250, 250, 250),
            outline=(120, 120, 120),
            width=4,
        )
        draw.rectangle(
            [width * 0.16, height * 0.26, width * 0.36, height * 0.62], fill=(190, 196, 206)
        )
        for i in range(5):
            top = height * (0.26 + 0.1 * i)
            draw.rectangle(
                [width * 0.42, top, width * (0.84 - 0.08 * (i % 3)), top + height * 0.035],
                fill=(205, 208, 214),
            )

    title = doc_type.replace("_", " ").upper()
    return _jpeg(_caption(image, f"SAMPLE - {title}"))
