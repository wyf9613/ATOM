"""Read a map_saver PGM/YAML pair and encode the image as PNG.

Pure standard library so it runs on a bare Raspberry Pi.
"""

import os
import struct
import zlib

import yaml


def load_map_yaml(yaml_path):
    with open(yaml_path, 'r', encoding='utf-8') as handle:
        meta = yaml.safe_load(handle)
    image = meta['image']
    if not os.path.isabs(image):
        image = os.path.join(os.path.dirname(os.path.abspath(yaml_path)), image)
    meta['image_path'] = image
    return meta


def read_pgm(path):
    """Return (width, height, bytes) for a binary P5 PGM with maxval <= 255."""
    with open(path, 'rb') as handle:
        data = handle.read()

    tokens = []
    pos = 0
    while len(tokens) < 4:
        # skip whitespace and comments
        while pos < len(data) and data[pos:pos + 1].isspace():
            pos += 1
        if data[pos:pos + 1] == b'#':
            while pos < len(data) and data[pos:pos + 1] not in (b'\n', b'\r'):
                pos += 1
            continue
        start = pos
        while pos < len(data) and not data[pos:pos + 1].isspace():
            pos += 1
        tokens.append(data[start:pos])
    pos += 1  # single whitespace after maxval

    if tokens[0] != b'P5':
        raise ValueError(f'{path}: only binary P5 PGM is supported')
    width, height, maxval = int(tokens[1]), int(tokens[2]), int(tokens[3])
    if maxval > 255:
        raise ValueError(f'{path}: 16-bit PGM not supported')
    pixels = data[pos:pos + width * height]
    if len(pixels) != width * height:
        raise ValueError(f'{path}: truncated pixel data')
    return width, height, pixels


def encode_png_gray(width, height, pixels):
    """Encode 8-bit grayscale pixels as a PNG byte string."""
    def chunk(tag, body):
        return (struct.pack('>I', len(body)) + tag + body
                + struct.pack('>I', zlib.crc32(tag + body) & 0xFFFFFFFF))

    raw = b''.join(
        b'\x00' + pixels[row * width:(row + 1) * width]
        for row in range(height))
    ihdr = struct.pack('>IIBBBBB', width, height, 8, 0, 0, 0, 0)
    return (b'\x89PNG\r\n\x1a\n'
            + chunk(b'IHDR', ihdr)
            + chunk(b'IDAT', zlib.compress(raw, 9))
            + chunk(b'IEND', b''))


def load_map(yaml_path):
    """Return (meta_dict_for_web, png_bytes)."""
    meta = load_map_yaml(yaml_path)
    width, height, pixels = read_pgm(meta['image_path'])
    if int(meta.get('negate', 0)):
        pixels = bytes(255 - p for p in pixels)
    png = encode_png_gray(width, height, pixels)
    web_meta = {
        'width': width,
        'height': height,
        'resolution': float(meta['resolution']),
        'origin': [float(v) for v in meta['origin'][:3]],
    }
    return web_meta, png


def pixel_to_map(px, py, meta):
    """Image pixel (origin top-left) -> map frame metres."""
    res = meta['resolution']
    ox, oy = meta['origin'][0], meta['origin'][1]
    return ox + px * res, oy + (meta['height'] - py) * res


def map_to_pixel(x, y, meta):
    res = meta['resolution']
    ox, oy = meta['origin'][0], meta['origin'][1]
    return (x - ox) / res, meta['height'] - (y - oy) / res
