"""STAGE 1-2: DISCOVER + INVENTORY.

Recursive discovery, dimensions, orientation, RAW detection, metadata via
exiftool (batch JSON), no pixel decoding. Writes analysis/photo_inventory.json.
"""
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageOps

sys.path.insert(0, str(Path(__file__).parent))
from config import ANALYSIS, IMG_EXTS, INPUT_DIR, RAW_EXTS

Image.MAX_IMAGE_PIXELS = None


def discover(root: Path):
    return sorted(p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in IMG_EXTS)


def exiftool_batch(paths):
    """One exiftool invocation for all files -> dict keyed by SourceFile."""
    tags = ["-j", "-n", "-FileName", "-DateTimeOriginal", "-CreateDate", "-Make", "-Model",
            "-LensID", "-LensModel", "-ISO", "-ExposureTime", "-FNumber", "-FocalLength",
            "-Orientation", "-ImageWidth", "-ImageHeight", "-Flash", "-WhiteBalance",
            "-ExposureCompensation", "-MeteringMode", "-ColorSpace", "-GPSLatitude",
            "-GPSLongitude", "-Software", "-FileType", "-SubSecTimeOriginal"]
    out = subprocess.run(["exiftool", *tags, "-@", "-"],
                         input="\n".join(str(p) for p in paths),
                         capture_output=True, text=True, timeout=1800)
    if out.returncode not in (0, 1) or not out.stdout.strip():
        print("exiftool stderr:", out.stderr[:500], file=sys.stderr)
        return {}
    return {Path(r["SourceFile"]).name: r for r in json.loads(out.stdout)}


def parse_dt(rec):
    for k in ("DateTimeOriginal", "CreateDate"):
        v = rec.get(k)
        if isinstance(v, str) and len(v) >= 19:
            try:
                return datetime.strptime(v[:19], "%Y:%m:%d %H:%M:%S")
            except ValueError:
                pass
    return None


def main():
    paths = discover(INPUT_DIR)
    print(f"discovered {len(paths)} image files under {INPUT_DIR}")
    meta = exiftool_batch(paths)
    print(f"exiftool returned metadata for {len(meta)} files")

    inv, failed = [], []
    for p in paths:
        rec = meta.get(p.name, {})
        try:
            with Image.open(p) as im:
                w, h = im.size
                fmt = im.format
                # display orientation after honouring the EXIF orientation flag
                dw, dh = ImageOps.exif_transpose(im).size
        except Exception as e:  # noqa: BLE001
            failed.append({"file": p.name, "error": repr(e)})
            continue

        dt = parse_dt(rec)
        exif_o = rec.get("Orientation")
        inv.append({
            "file": p.name,
            "path": str(p),
            "is_raw": p.suffix.lower() in RAW_EXTS,
            "format": fmt,
            "file_type": rec.get("FileType"),
            "file_size": p.stat().st_size,
            "stored_width": w, "stored_height": h,
            "width": dw, "height": dh,                       # as-displayed
            "megapixels": round(dw * dh / 1e6, 2),
            "aspect_ratio": round(dw / dh, 4),
            "orientation": "portrait" if dh > dw else ("square" if dh == dw else "landscape"),
            "exif_orientation": exif_o,
            "rotated_by_exif": bool(exif_o and int(exif_o) != 1),
            "datetime_original": dt.isoformat() if dt else None,
            "event_day": dt.strftime("%Y-%m-%d") if dt else None,
            "capture_ts": dt.timestamp() if dt else None,
            "camera": " ".join(str(x) for x in (rec.get("Make"), rec.get("Model")) if x).strip() or None,
            "lens": rec.get("LensID") or rec.get("LensModel"),
            "iso": rec.get("ISO"),
            "exposure_time": rec.get("ExposureTime"),
            "f_number": rec.get("FNumber"),
            "focal_length": rec.get("FocalLength"),
            "exposure_compensation": rec.get("ExposureCompensation"),
            "flash": rec.get("Flash"),
            "white_balance": rec.get("WhiteBalance"),
            "metering": rec.get("MeteringMode"),
            "color_space": rec.get("ColorSpace"),
            "gps": ([rec.get("GPSLatitude"), rec.get("GPSLongitude")]
                    if rec.get("GPSLatitude") is not None else None),
            "software": rec.get("Software"),
        })

    inv.sort(key=lambda r: (r["capture_ts"] or 0, r["file"]))
    (ANALYSIS / "photo_inventory.json").write_text(json.dumps(inv, indent=1))
    if failed:
        (ANALYSIS / "unprocessable.json").write_text(json.dumps(failed, indent=1))

    # ---- summary
    from collections import Counter
    print(f"\ninventoried: {len(inv)}   failed: {len(failed)}")
    print(f"RAW files:   {sum(r['is_raw'] for r in inv)}")
    print("orientation:", dict(Counter(r["orientation"] for r in inv)))
    print("dimensions :", dict(Counter(f"{r['width']}x{r['height']}" for r in inv)))
    print("cameras    :", dict(Counter(r["camera"] for r in inv)))
    print("lenses     :", dict(Counter(str(r["lens"]) for r in inv)))
    print("colorspace :", dict(Counter(str(r["color_space"]) for r in inv)))
    print("gps present:", sum(bool(r["gps"]) for r in inv))
    print("\nby event day:")
    for d, n in sorted(Counter(str(r["event_day"]) for r in inv).items()):
        print(f"   {d}  {n:4d}")
    iso = [r["iso"] for r in inv if r["iso"]]
    print(f"\nISO range  : {min(iso)}-{max(iso)}")
    fl = [r["focal_length"] for r in inv if r["focal_length"]]
    print(f"focal range: {min(fl)}-{max(fl)} mm")


if __name__ == "__main__":
    main()
