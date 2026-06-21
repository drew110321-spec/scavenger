#!/usr/bin/env python3
"""
Build roadai_demo.gif — an animated GIF of the same 5-stage pipeline slides.
GIF opens on any device (phone, browser, chat) but has no audio track.
Pure Python stdlib, reuses the frame renderer in make_video.py.

    python3 make_gif.py   ->  roadai_demo.gif
"""

import struct
import make_video as mv

OUT = "roadai_demo.gif"
FPS = mv.FPS
DELAY_CS = max(2, round(100 / FPS))   # centiseconds per frame


def lzw_encode(indices, min_code_size):
    """Standard GIF LZW. Returns packed sub-block byte stream."""
    clear = 1 << min_code_size
    end = clear + 1
    code_size = min_code_size + 1
    table = {bytes([i]): i for i in range(clear)}
    next_code = end + 1

    out = bytearray()
    bitbuf = 0
    bitcnt = 0

    def emit(code):
        nonlocal bitbuf, bitcnt
        bitbuf |= code << bitcnt
        bitcnt += code_size
        while bitcnt >= 8:
            out.append(bitbuf & 0xFF)
            bitbuf >>= 8
            bitcnt -= 8

    emit(clear)
    w = b""
    for c in indices:
        wc = w + bytes([c])
        if wc in table:
            w = wc
        else:
            emit(table[w])
            table[wc] = next_code
            next_code += 1
            if next_code == (1 << code_size) and code_size < 12:
                code_size += 1
            if next_code > 4095:
                emit(clear)
                table = {bytes([i]): i for i in range(clear)}
                next_code = end + 1
                code_size = min_code_size + 1
            w = bytes([c])
    if w:
        emit(table[w])
    emit(end)
    if bitcnt > 0:
        out.append(bitbuf & 0xFF)

    # chunk into <=255-byte sub-blocks
    packed = bytearray()
    i = 0
    while i < len(out):
        block = out[i:i + 255]
        packed.append(len(block))
        packed += block
        i += 255
    packed.append(0)   # block terminator
    return bytes(packed)


def main():
    print("Rendering frames...")
    frames = mv.render_frames()           # list of top-down index bytearrays
    W, H = mv.W, mv.H
    n = len(frames)
    print(f"  {n} frames @ {FPS}fps")

    # 16-entry global color table (indices 0..14 used)
    gct = bytearray()
    for i in range(16):
        r, g, b = mv.PAL[i] if i < len(mv.PAL) else (0, 0, 0)
        gct += bytes((r, g, b))
    min_code_size = 4   # 16-color table

    out = bytearray()
    out += b"GIF89a"
    # logical screen descriptor: GCTF=1, color res=7, sort=0, GCT size=3 (16)
    out += struct.pack("<HH", W, H) + bytes((0xF3, 0, 0)) + gct
    # NETSCAPE looping extension (loop forever)
    out += b"\x21\xFF\x0B" + b"NETSCAPE2.0" + b"\x03\x01\x00\x00\x00"

    print("Encoding (LZW)...")
    for fi, fr in enumerate(frames):
        # graphic control extension: disposal=1, delay, no transparency
        out += b"\x21\xF9\x04\x04" + struct.pack("<H", DELAY_CS) + b"\x00\x00"
        # image descriptor
        out += b"\x2C" + struct.pack("<HHHH", 0, 0, W, H) + b"\x00"
        out += bytes([min_code_size])
        out += lzw_encode(fr, min_code_size)
        if (fi + 1) % 40 == 0:
            print(f"  {fi + 1}/{n}")
    out += b"\x3B"   # trailer

    with open(OUT, "wb") as fh:
        fh.write(out)
    print(f"Wrote {OUT}  ({len(out)/1_048_576:.1f} MB, {n/FPS:.1f}s, {W}x{H})")


if __name__ == "__main__":
    main()
