#!/usr/bin/env python3
"""Parse roadai_demo.avi back, validate structure, and export a PNG preview frame."""
import struct, zlib, sys

PAL = __import__("make_video").PAL
W = __import__("make_video").W
H = __import__("make_video").H

data = open("roadai_demo.avi", "rb").read()
assert data[:4] == b"RIFF", "not RIFF"
assert data[8:12] == b"AVI ", "not AVI"
print("RIFF AVI ok, size", len(data))

def walk(buf, off, end, depth=0):
    while off < end:
        tag = buf[off:off+4]; size = struct.unpack("<I", buf[off+4:off+8])[0]
        if tag in (b"RIFF", b"LIST"):
            sub = buf[off+8:off+12]
            print("  "*depth + f"{tag.decode()} '{sub.decode()}' ({size})")
            walk(buf, off+12, off+8+size, depth+1)
        else:
            if depth <= 2:
                print("  "*depth + f"{tag.decode()} ({size})")
        off += 8 + size + (size & 1)

walk(data, 0, 8 + struct.unpack("<I", data[4:8])[0])

# find movi + idx1, pull first 00db frame via index
movi = data.find(b"movi")
idx = data.find(b"idx1")
isize = struct.unpack("<I", data[idx+4:idx+8])[0]
entries = isize // 16
print(f"idx1: {entries} entries")
first = None
counts = {}
for i in range(entries):
    e = idx + 8 + i*16
    ck = data[e:e+4]; flags, offc, sz = struct.unpack("<III", data[e+4:e+16])
    counts[ck] = counts.get(ck, 0) + 1
    if ck == b"00db" and first is None:
        first = (offc, sz)
print("chunk counts:", {k.decode(): v for k, v in counts.items()})

# movi data starts at the 'movi' fourcc; offsets are relative to it
offc, sz = first
abs_off = movi + offc + 8  # skip ckid+size of the chunk itself
frame = data[abs_off:abs_off+sz]
assert len(frame) == W*H, f"frame size {len(frame)} != {W*H}"
print("first frame extracted ok:", len(frame), "bytes")

# un-flip (DIB bottom-up) and write PNG
rows = [frame[(H-1-y)*W:(H-1-y)*W+W] for y in range(H)]
raw = bytearray()
for r in rows:
    raw.append(0)
    for ix in r:
        rr, gg, bb = PAL[ix] if ix < len(PAL) else (0,0,0)
        raw += bytes((rr, gg, bb))

def png_chunk(typ, payload):
    c = typ + payload
    return struct.pack(">I", len(payload)) + c + struct.pack(">I", zlib.crc32(c) & 0xffffffff)

png = b"\x89PNG\r\n\x1a\n"
png += png_chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
png += png_chunk(b"IDAT", zlib.compress(bytes(raw), 9))
png += png_chunk(b"IEND", b"")
open("preview.png", "wb").write(png)
print("wrote preview.png")
