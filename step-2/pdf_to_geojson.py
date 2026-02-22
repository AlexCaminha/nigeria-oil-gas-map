"""
Extract all vector drawing paths and text labels from the Nigeria Oil Fields
PDF and convert them to GeoJSON FeatureCollections with geographic coordinates.

The PDF contains 100% vector content (2,846 drawing paths, 783 text labels)
using a World Equidistant Cylindrical projection, so PDF x/y coordinates map
linearly to longitude/latitude.

The coordinate transform is calibrated from degree markers found in the PDF:
    Longitude: 2°E→x=246.7, 4°E→x=1003.4, 6°E→x=1760.1, 8°E→x=2516.8, 10°E→x=3271.8
    Latitude:  6°N→y=867.2, 4°N→y=1626.6

Output GeoJSON FeatureCollections:
    areas.geojson  - Filled polygons (oil blocks, fields, land, water)
    lines.geojson  - Stroked paths without fill (boundaries, pipelines, contours)
    labels.geojson - Text labels as points (block IDs, field names, cities)

Usage:
    from pdf_to_geojson import extract_geojson
    results = extract_geojson("path/to/file.pdf", "output_dir")
"""

import json
import os

import fitz  # PyMuPDF

# ---------------------------------------------------------------------------
# Coordinate transform: PDF points → (longitude, latitude)
# ---------------------------------------------------------------------------
# Linear fits from degree-marker positions on the map axes.
#   lon = LON_A * x + LON_B
#   lat = LAT_A * y + LAT_B

LON_A = 8.0 / (3271.8 - 246.7)   # ≈ 0.0026446 deg/pt
LON_B = 2.0 - LON_A * 246.7      # ≈ 1.3475

LAT_A = -2.0 / (1626.6 - 867.2)  # ≈ -0.0026336 deg/pt
LAT_B = 6.0 - LAT_A * 867.2      # ≈ 8.2840


def pdf_to_lonlat(x: float, y: float) -> tuple[float, float]:
    """Convert PDF point coordinates to (longitude, latitude)."""
    return (
        round(LON_A * x + LON_B, 6),
        round(LAT_A * y + LAT_B, 6),
    )


def rgb_to_hex(rgb) -> str | None:
    """Convert an (r, g, b) float tuple to a #RRGGBB hex string."""
    if rgb is None:
        return None
    r, g, b = (int(c * 255) for c in rgb)
    return f"#{r:02X}{g:02X}{b:02X}"


# ---------------------------------------------------------------------------
# Fill-color classification from the map legend (see step-1/prompt.md)
# ---------------------------------------------------------------------------
FILL_CLASSES: dict[str, str] = {
    # Oil field fills
    "#00FF00": "Oil or Oil/Gas field",
    "#FF0000": "Gas or Gas/Condensate field",
    # Oil block status fills
    "#FFFF00": "Returned to NNPC",
    "#BEFFB0": "Onshore licensed",
    "#DBFFD1": "Onshore relinquished",
    "#FFFFBE": "Onshore open",
    "#A1FFFF": "Offshore licensed",
    "#A0FFFF": "Offshore licensed",
    "#EBFFFF": "Offshore open",
    # Non-legend fills
    "#FFFFFF": "Background",
    "#000000": "Marker",
    "#00008C": "Feature marker",
    "#73DFFF": "Water",
    "#D1FFFF": "Water variant",
    "#B2B2B2": "Relinquished area",
    "#D2FCE3": "Area variant",
}


def classify_fill(hex_color: str | None) -> str | None:
    if hex_color is None:
        return None
    return FILL_CLASSES.get(hex_color, "Unclassified")


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------
def _bezier(p0, p1, p2, p3, t):
    """Evaluate a cubic Bezier at parameter t."""
    u = 1 - t
    return (
        u**3 * p0[0] + 3 * u**2 * t * p1[0] + 3 * u * t**2 * p2[0] + t**3 * p3[0],
        u**3 * p0[1] + 3 * u**2 * t * p1[1] + 3 * u * t**2 * p2[1] + t**3 * p3[1],
    )


def _extract_coords(drawing: dict, bezier_steps: int = 4) -> list[tuple[float, float]]:
    """Extract a list of (x, y) PDF-point coordinates from a drawing."""
    coords: list[tuple[float, float]] = []
    for item in drawing["items"]:
        kind = item[0]
        if kind == "l":  # line segment
            p1, p2 = item[1], item[2]
            if not coords or coords[-1] != (p1.x, p1.y):
                coords.append((p1.x, p1.y))
            coords.append((p2.x, p2.y))
        elif kind == "c":  # cubic Bezier
            p0, p1, p2, p3 = item[1], item[2], item[3], item[4]
            if not coords or coords[-1] != (p0.x, p0.y):
                coords.append((p0.x, p0.y))
            for i in range(1, bezier_steps + 1):
                bx, by = _bezier(
                    (p0.x, p0.y), (p1.x, p1.y),
                    (p2.x, p2.y), (p3.x, p3.y),
                    i / bezier_steps,
                )
                coords.append((bx, by))
        elif kind == "re":  # rectangle
            r = item[1]
            coords.extend([
                (r.x0, r.y0), (r.x1, r.y0),
                (r.x1, r.y1), (r.x0, r.y1),
                (r.x0, r.y0),
            ])
        elif kind == "qu":  # quad
            q = item[1]
            coords.extend([
                (q.ul.x, q.ul.y), (q.ur.x, q.ur.y),
                (q.lr.x, q.lr.y), (q.ll.x, q.ll.y),
                (q.ul.x, q.ul.y),
            ])
    return coords


def _is_closed(coords: list[tuple[float, float]], tolerance: float = 2.0) -> bool:
    """True if the first and last points are within *tolerance* PDF points."""
    if len(coords) < 3:
        return False
    dx = coords[0][0] - coords[-1][0]
    dy = coords[0][1] - coords[-1][1]
    return dx * dx + dy * dy < tolerance * tolerance


# ---------------------------------------------------------------------------
# Main extraction
# ---------------------------------------------------------------------------
def extract_geojson(pdf_path: str, output_dir: str) -> dict:
    """Extract vector paths and text labels from *pdf_path* as GeoJSON.

    Writes three FeatureCollection files into *output_dir* and returns a
    summary dict keyed by collection name.
    """
    doc = fitz.open(pdf_path)
    page = doc[0]

    drawings = page.get_drawings()
    text_data = page.get_text("dict")

    page_info = {
        "page_width_pt": page.rect.width,
        "page_height_pt": page.rect.height,
        "total_drawings": len(drawings),
        "total_text_blocks": len(text_data["blocks"]),
        "projection": "World Equidistant Cylindrical",
    }

    areas: list[dict] = []
    lines: list[dict] = []
    labels: list[dict] = []

    # --- drawings --------------------------------------------------------
    for i, d in enumerate(drawings):
        coords = _extract_coords(d)
        if len(coords) < 2:
            continue

        # Skip the large map-background rectangles
        rect = d.get("rect")
        if rect:
            r = fitz.Rect(rect)
            if r.width > 3200 and r.height > 2000:
                continue

        fill = d.get("fill")
        stroke = d.get("color")
        width = d.get("width")
        fill_hex = rgb_to_hex(fill)
        stroke_hex = rgb_to_hex(stroke)

        props: dict = {"index": i}
        if fill_hex:
            props["fill"] = fill_hex
            props["class"] = classify_fill(fill_hex)
        if stroke_hex:
            props["stroke"] = stroke_hex
        if width is not None:
            props["stroke_width"] = round(width, 2)

        geo_coords = [pdf_to_lonlat(x, y) for x, y in coords]

        if fill and (_is_closed(coords) or d.get("closePath", False)):
            # Ensure the ring is closed for valid GeoJSON
            if geo_coords[0] != geo_coords[-1]:
                geo_coords.append(geo_coords[0])
            areas.append({
                "type": "Feature",
                "geometry": {"type": "Polygon", "coordinates": [geo_coords]},
                "properties": props,
            })
        else:
            lines.append({
                "type": "Feature",
                "geometry": {"type": "LineString", "coordinates": geo_coords},
                "properties": props,
            })

    # --- text labels -----------------------------------------------------
    for block in text_data["blocks"]:
        if "lines" not in block:
            continue
        for line in block["lines"]:
            for span in line["spans"]:
                text = span["text"].strip()
                if not text:
                    continue
                bbox = span["bbox"]
                cx = (bbox[0] + bbox[2]) / 2
                cy = (bbox[1] + bbox[3]) / 2
                lon, lat = pdf_to_lonlat(cx, cy)

                labels.append({
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [lon, lat]},
                    "properties": {
                        "text": text,
                        "font": span["font"],
                        "size": round(span["size"], 1),
                        "color": f"#{span['color']:06X}",
                    },
                })

    doc.close()

    # --- write GeoJSON files ---------------------------------------------
    os.makedirs(output_dir, exist_ok=True)

    results = {"page": page_info}
    for name, features in [("areas", areas), ("lines", lines), ("labels", labels)]:
        fc = {"type": "FeatureCollection", "features": features}
        path = os.path.join(output_dir, f"{name}.geojson")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(fc, f, ensure_ascii=False)
        results[name] = {
            "path": os.path.abspath(path),
            "features": len(features),
            "file_size_mb": round(os.path.getsize(path) / 1024 / 1024, 2),
        }

    return results


if __name__ == "__main__":
    import sys

    pdf = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(__file__), "..", "data", "Map of Nigeria Oil Field.pdf"
    )
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
        os.path.dirname(__file__), "output"
    )

    res = extract_geojson(pdf, out)
    print(f"\nPage: {res['page']['page_width_pt']} x {res['page']['page_height_pt']} pt")
    print(f"Projection: {res['page']['projection']}")
    print(f"Drawings: {res['page']['total_drawings']}")
    print(f"Text blocks: {res['page']['total_text_blocks']}")
    for name in ("areas", "lines", "labels"):
        r = res[name]
        print(f"\n{name}.geojson: {r['features']} features ({r['file_size_mb']} MB)")
