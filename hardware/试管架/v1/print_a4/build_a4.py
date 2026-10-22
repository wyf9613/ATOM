"""Rearrange existing vector tags onto A4 without resizing or rotating them.

Run with Python + PyMuPDF (fitz). Original rack artwork stays read-only.
"""
from pathlib import Path
import hashlib
import json
import xml.etree.ElementTree as ET

import pymupdf as fitz

OUT = Path(__file__).resolve().parent
SOURCE = OUT.parent / 'small_tags_PRINT_100percent.svg'
NS = {'s': 'http://www.w3.org/2000/svg'}
MM = 72 / 25.4


def main():
    root = ET.parse(SOURCE).getroot()
    assert root.attrib['viewBox'] == '0 0 320.0 63.0'
    groups = [[] for _ in range(5)]
    for poly in root.findall('.//s:polygon', NS):
        points = [tuple(map(float, pair.split(',')))
                  for pair in poly.attrib['points'].split()]
        tag_id = int((min(x for x, y in points) - 20) // 60)
        # Convert the source's upward Y axis into local top-down tag coordinates.
        groups[tag_id].append([(x - 20 - 60 * tag_id, 51.5 - y)
                               for x, y in points])

    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="210mm" '
           'height="297mm" viewBox="0 0 210 297">',
           '<rect width="210" height="297" fill="white"/>']

    def label(x, y, value, size=3.3):
        svg.append(f'<text x="{x}" y="{y}" font-family="Helvetica,Arial,sans-serif" '
                   f'font-size="{size}" fill="black">{value}</text>')

    def line(x1, y1, x2, y2):
        svg.append(f'<path d="M{x1},{y1} L{x2},{y2}" fill="none" '
                   'stroke="black" stroke-width="0.15"/>')

    label(20, 22, 'ATOM | Small rack | AprilTag 36h11 | IDs 0-4', 4.2)
    label(20, 31, 'A4 (210 x 297 mm) | Print at ACTUAL SIZE / 100%')
    label(20, 38, 'Disable Fit / Shrink. Black square: 40 x 40 mm.')
    label(20, 45, 'Keep 5 mm white margin on each side (cut size: 50 x 50 mm).')

    placements = []
    for tag_id, polygons in enumerate(groups):
        x, y = 25 + (tag_id % 3) * 60, 60 + (tag_id // 3) * 70
        assert polygons
        all_points = [p for polygon in polygons for p in polygon]
        assert min(p[0] for p in all_points) == 0
        assert min(p[1] for p in all_points) == 0
        assert max(p[0] for p in all_points) == 40
        assert max(p[1] for p in all_points) == 40
        for polygon in polygons:
            pts = ' '.join(f'{x + px:g},{y + py:g}' for px, py in polygon)
            svg.append(f'<polygon fill="black" points="{pts}"/>')
        # Crop marks stop outside the 50 mm white-backed cutout.
        for cx in (x - 5, x + 45):
            for cy in (y - 5, y + 45):
                sx = -1 if cx < x else 1
                sy = -1 if cy < y else 1
                line(cx + sx, cy, cx + 3 * sx, cy)
                line(cx, cy + sy, cx, cy + 3 * sy)
        label(x + 14, y + 53, f'ID {tag_id}')
        placements.append({'id': tag_id, 'black_square_top_left_mm': [x, y],
                           'black_square_size_mm': [40, 40],
                           'white_margin_per_side_mm': 5})

    label(25, 203, 'Scale check: end ticks must be 100 mm apart.')
    line(25, 211, 125, 211)
    for x in range(25, 126, 10):
        line(x, 209 if x in (25, 125) else 210, x, 213)
    label(25, 220, '0')
    label(114, 220, '100 mm')
    label(20, 240, 'Cut each tag separately; keep IDs 0-4 in rack slot order.')
    label(20, 247, 'After printing, measure both sides of a black square: 40 mm.')
    svg.append('</svg>')
    stem = 'small_tags_ID0-4_A4_40mm_PRINT_100percent'
    svg_path = OUT / f'{stem}.svg'
    svg_path.write_text('\n'.join(svg) + '\n', encoding='utf-8')
    with fitz.open(svg_path) as artwork:
        pdf = fitz.open('pdf', artwork.convert_to_pdf())
    # Request no automatic print scaling; the print dialog still needs checking.
    pdf.xref_set_key(pdf.pdf_catalog(), 'ViewerPreferences', '<</PrintScaling /None>>')
    pdf.set_metadata({'title': 'ATOM small rack tags ID0-4 | A4 | 40 mm',
                      'subject': 'Print at 100%; black border 40 mm; white margin 5 mm'})
    pdf.save(OUT / f'{stem}.pdf', deflate=True)
    assert len(pdf) == 1
    assert abs(pdf[0].rect.width / MM - 210) < 0.001
    assert abs(pdf[0].rect.height / MM - 297) < 0.001
    pdf.close()
    (OUT / 'manifest.json').write_text(json.dumps({
        'source': '../' + SOURCE.name,
        'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        'page_size_mm': [210, 297], 'family': 'tag36h11',
        'tags': placements, 'artwork': 'Original polygons, translation only; no scaling or rotation',
        'validation_scope': 'Digital layout only; printed size requires ruler measurement',
    }, indent=2) + '\n', encoding='utf-8')
    print(OUT / f'{stem}.pdf')


if __name__ == '__main__':
    main()
