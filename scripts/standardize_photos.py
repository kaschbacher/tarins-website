#!/usr/bin/env python3
"""
standardize_photos.py — batch-normalize photos to a uniform square size and color space.

Pipeline per image:
  1. Apply EXIF orientation (so rotated iPhone shots aren't sideways)
  2. Convert embedded ICC profile -> sRGB (iPhone captures Display P3)
  3. Optional gray-world white balance
  4. Optional autocontrast
  5. Center-crop or pad to square
  6. Resize to target size with Lanczos resampling
  7. Save as PNG or JPEG

Setup (once):
    python3 -m pip install --upgrade pillow pillow-heif

Usage:
    python3 standardize_photos.py INPUT_DIR
    python3 standardize_photos.py ~/Pictures/incoming -o ~/Pictures/standardized
    python3 standardize_photos.py ~/Pictures/incoming --size 250 --fit pad --format jpg
    python3 standardize_photos.py ~/Pictures/incoming --white-balance --no-autocontrast
"""

from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path

try:
    from PIL import Image, ImageCms, ImageOps
except ImportError:
    sys.exit("Pillow is not installed. Run: python3 -m pip install --upgrade pillow pillow-heif")

# HEIC/HEIF support (iPhone default format). Optional but almost always needed.
HEIF_OK = False
try:
    import pillow_heif

    pillow_heif.register_heif_opener()
    HEIF_OK = True
except ImportError:
    pass

EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".webp",
    ".heic", ".heif", ".HEIC", ".HEIF",
}

SRGB_PROFILE = ImageCms.createProfile("sRGB")


def to_srgb(img: Image.Image) -> tuple[Image.Image, str]:
    """Convert an image to sRGB using its embedded ICC profile, if present.

    Returns (image, note). Images with no profile are assumed to already be sRGB,
    which is the correct assumption for the overwhelming majority of web/JPEG files.
    """
    icc = img.info.get("icc_profile")
    if not icc:
        return img.convert("RGB"), "no ICC profile (assumed sRGB)"

    try:
        src_profile = ImageCms.ImageCmsProfile(io.BytesIO(icc))
        src_name = ImageCms.getProfileDescription(src_profile).strip()
        converted = ImageCms.profileToProfile(
            img,
            src_profile,
            SRGB_PROFILE,
            renderingIntent=ImageCms.Intent.PERCEPTUAL,
            outputMode="RGB",
        )
        return converted, f"{src_name} -> sRGB"
    except Exception as exc:  # malformed or unsupported profile
        return img.convert("RGB"), f"ICC conversion failed ({exc}); assumed sRGB"


def is_grayscale(img: Image.Image, tolerance: int = 8) -> bool:
    """True if the image is black and white.

    Catches two cases: images already in a single-channel mode, and RGB images
    whose three channels are effectively identical (a B&W photo saved as RGB,
    which is what a scan or an in-camera mono filter usually produces).

    `tolerance` is the maximum allowed per-pixel channel spread, 0-255. A small
    nonzero value absorbs JPEG chroma noise in an otherwise neutral image.
    """
    if img.mode in ("1", "L", "LA", "I", "I;16"):
        return True
    if img.mode not in ("RGB", "RGBA"):
        return False

    # Downsample first: exact enough for this decision, ~1000x faster on 12MP files.
    probe = img.convert("RGB").resize((64, 64), Image.Resampling.BILINEAR)
    r, g, b = probe.split()
    from PIL import ImageChops

    spread = ImageChops.lighter(
        ImageChops.difference(r, g), ImageChops.difference(g, b)
    )
    return spread.getextrema()[1] <= tolerance


def gray_world_balance(img: Image.Image) -> Image.Image:
    """Simple gray-world white balance: scale each channel so its mean matches the
    overall mean. Effective for consistent indoor/outdoor color casts, but it will
    shift images that are legitimately dominated by one color."""
    r, g, b = img.split()
    means = [ch.resize((1, 1), Image.Resampling.BOX).getpixel((0, 0)) for ch in (r, g, b)]
    target = sum(means) / 3.0
    channels = []
    for ch, mean in zip((r, g, b), means):
        scale = target / mean if mean else 1.0
        channels.append(ch.point(lambda v, s=scale: min(255, int(v * s + 0.5))))
    return Image.merge("RGB", channels)


def make_square(img: Image.Image, size: int, fit: str, bg: tuple[int, int, int]) -> Image.Image:
    """Return a size x size image, either center-cropped or padded."""
    if fit == "crop":
        # ImageOps.fit crops to aspect ratio from the center, then resizes.
        return ImageOps.fit(img, (size, size), method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))

    # pad: scale longest edge to `size`, then center on a square canvas
    img = img.copy()
    img.thumbnail((size, size), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (size, size), bg)
    canvas.paste(img, ((size - img.width) // 2, (size - img.height) // 2))
    return canvas


def parse_bg(value: str) -> tuple[int, int, int]:
    v = value.strip().lstrip("#")
    if len(v) != 6:
        raise argparse.ArgumentTypeError("background must be a hex color like FFFFFF")
    return tuple(int(v[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def main() -> int:
    p = argparse.ArgumentParser(
        description="Standardize photos to a uniform square size and sRGB color.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("input_dir", type=Path, help="folder containing the source photos")
    p.add_argument("-o", "--output-dir", type=Path, default=None,
                   help="destination folder (default: INPUT_DIR/standardized)")
    p.add_argument("--size", type=int, default=250, help="output edge length in pixels")
    p.add_argument("--fit", choices=("crop", "pad"), default="crop",
                   help="crop = center-crop to square; pad = fit whole image, add bars")
    p.add_argument("--background", type=parse_bg, default="FFFFFF",
                   help="pad color as hex, e.g. FFFFFF or 000000")
    p.add_argument("--format", choices=("png", "jpg"), default="png", help="output file format")
    p.add_argument("--quality", type=int, default=95, help="JPEG quality (ignored for PNG)")
    p.add_argument("--autocontrast", dest="autocontrast", action="store_true", default=True,
                   help="stretch tonal range so exposure is consistent (default: on)")
    p.add_argument("--no-autocontrast", dest="autocontrast", action="store_false")
    p.add_argument("--cutoff", type=float, default=0.5,
                   help="percent of pixels clipped at each end by autocontrast")
    p.add_argument("--white-balance", action="store_true",
                   help="apply gray-world white balance (off by default; can shift skin tones)")
    p.add_argument("--bw-tolerance", type=int, default=8,
                   help="max channel spread (0-255) still counted as black and white")
    p.add_argument("--bw-autocontrast", action="store_true",
                   help="also autocontrast B&W photos (off by default: they pass through untouched)")
    p.add_argument("--gray-output", choices=("rgb", "l"), default="rgb",
                   help="save B&W photos as 3-channel RGB (uniform arrays) or 1-channel L")
    p.add_argument("--recursive", action="store_true", help="also process subfolders")
    p.add_argument("--dry-run", action="store_true", help="report what would happen, write nothing")
    args = p.parse_args()

    src_dir: Path = args.input_dir.expanduser().resolve()
    if not src_dir.is_dir():
        sys.exit(f"Not a directory: {src_dir}")

    out_dir: Path = (args.output_dir.expanduser().resolve()
                     if args.output_dir else src_dir / "standardized")

    pattern = "**/*" if args.recursive else "*"
    files = sorted(
        f for f in src_dir.glob(pattern)
        if f.is_file() and f.suffix.lower() in {e.lower() for e in EXTENSIONS}
        and out_dir not in f.parents
    )

    if not files:
        sys.exit(f"No supported image files found in {src_dir}")

    heic_present = any(f.suffix.lower() in {".heic", ".heif"} for f in files)
    if heic_present and not HEIF_OK:
        sys.exit("HEIC files found but pillow-heif is not installed.\n"
                 "Run: python3 -m pip install pillow-heif")

    print(f"Source:      {src_dir}")
    print(f"Destination: {out_dir}")
    print(f"Found {len(files)} image(s). Target: {args.size}x{args.size} "
          f"({args.fit}), sRGB, .{args.format}\n")

    if not args.dry_run:
        out_dir.mkdir(parents=True, exist_ok=True)

    ext = ".png" if args.format == "png" else ".jpg"
    ok = skipped = bw_count = 0
    used_names: set[str] = set()

    for f in files:
        try:
            with Image.open(f) as im:
                im.load()
                original = f"{im.width}x{im.height}"

                im = ImageOps.exif_transpose(im)          # 1. orientation
                gray = is_grayscale(im, args.bw_tolerance)

                if gray:
                    # B&W: skip color-space and white-balance work entirely.
                    # Geometry still applies so every output is the same shape.
                    im = im.convert("RGB")
                    color_note = "b&w — color steps skipped"
                    if args.bw_autocontrast and args.autocontrast:
                        im = ImageOps.autocontrast(im, cutoff=args.cutoff)
                else:
                    im, color_note = to_srgb(im)          # 2. color space
                    if args.white_balance:                # 3. white balance
                        im = gray_world_balance(im)
                    if args.autocontrast:                 # 4. tonal range
                        im = ImageOps.autocontrast(im, cutoff=args.cutoff)

                im = make_square(im, args.size, args.fit, args.background)  # 5-6.

                if gray and args.gray_output == "l":
                    im = im.convert("L")

                # Avoid collisions when e.g. IMG_0001.heic and IMG_0001.jpg both exist
                stem = f.stem
                name = stem + ext
                n = 2
                while name.lower() in used_names:
                    name = f"{stem}_{n}{ext}"
                    n += 1
                used_names.add(name.lower())

                dest = out_dir / name
                if not args.dry_run:                      # 7. save
                    if args.format == "png":
                        im.save(dest, "PNG", optimize=True)
                    else:
                        im.save(dest, "JPEG", quality=args.quality,
                                subsampling=0, optimize=True)

                print(f"  ok   {f.name:<32} {original:>11}  [{color_note}]  -> {name}")
                ok += 1
                bw_count += 1 if gray else 0

        except Exception as exc:
            print(f"  SKIP {f.name:<32} {exc}", file=sys.stderr)
            skipped += 1

    verb = "would process" if args.dry_run else "processed"
    print(f"\n{verb} {ok} file(s) ({bw_count} black and white), skipped {skipped}.")
    if not args.dry_run and ok:
        print(f"Output: {out_dir}")
    return 0 if skipped == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
