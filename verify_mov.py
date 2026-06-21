#!/usr/bin/env python3
"""Decode our own roadai_demo.mov back: validate boxes + reconstruct frame 0."""
import struct, zlib
import make_video as mv
import make_mov as mm

data = open("roadai_demo.mov", "rb").read()

# ── walk top-level + nested boxes we care about ──
def find_boxes(buf, start, end):
    boxes = []
    o = start
    while o + 8 <= end:
        sz = struct.unpack(">I", buf[o:o+4])[0]; typ = buf[o+4:o+8]
        if sz < 8: break
        boxes.append((typ, o, sz))
        o += sz
    return boxes

top = find_boxes(data, 0, len(data))
print("top-level:", [(t.decode('latin1'), s) for t, o, s in top])
assert any(t == b"ftyp" for t, _, _ in top) and any(t == b"moov" for t, _, _ in top) and any(t == b"mdat" for t, _, _ in top)

def descend(path):
    """find nested box by path of types, return (offset, size) of payload start."""
    o, end = 0, len(data)
    cur = find_boxes(data, 0, len(data))
    res = None
    for want in path:
        found = None
        for t, bo, bs in cur:
            if t == want:
                found = (bo, bs); break
        assert found, f"missing {want}"
        bo, bs = found
        res = (bo + 8, bo + bs)
        cur = find_boxes(data, bo + 8, bo + bs)
    return res

# locate first video sample via stco (video trak is first trak)
moov = descend([b"moov"])
# crude: first stco/stsz under first trak's stbl
trak_start = None
for t, bo, bs in find_boxes(data, moov[0], moov[1]):
    if t == b"trak":
        trak_start = (bo, bs); break
def sub(path, region):
    cur = find_boxes(data, region[0], region[1])
    for want in path:
        nxt = None
        for t, bo, bs in cur:
            if t == want:
                nxt = (bo, bs); cur = find_boxes(data, bo+8, bo+bs); break
        assert nxt, want
        region = (nxt[0]+8, nxt[0]+nxt[1])
    return region

stbl = sub([b"mdia", b"minf", b"stbl"], (trak_start[0]+8, trak_start[0]+trak_start[1]))
stco = sub([b"stco"], stbl)
stsz = sub([b"stsz"], stbl)
voff = struct.unpack(">I", data[stco[0]+8:stco[0]+12])[0]
samp_size_const, count = struct.unpack(">II", data[stsz[0]+4:stsz[0]+12])
first_sz = struct.unpack(">I", data[stsz[0]+12:stsz[0]+16])[0]
print(f"video: {count} samples, first chunk offset {voff}, first sample {first_sz} bytes")

# first sample = 4-byte length + NAL
nlen = struct.unpack(">I", data[voff:voff+4])[0]
nal = data[voff+4:voff+4+nlen]
print("NAL header byte: 0x%02x (expect 0x65 IDR)" % nal[0])
assert nal[0] == 0x65

# remove emulation prevention
rbsp = bytearray()
i, b = 1, nal
while i < len(b):
    if i+2 < len(b) and b[i] == 0 and b[i+1] == 0 and b[i+2] == 3:
        rbsp += b"\x00\x00"; i += 3
    else:
        rbsp.append(b[i]); i += 1
rbsp = bytes(rbsp)

# bit reader (MSB-first)
class R:
    def __init__(s, d): s.d=d; s.p=0
    def u1(s):
        byte = s.d[s.p>>3]; bit = (byte >> (7-(s.p&7))) & 1; s.p+=1; return bit
    def u(s,n):
        v=0
        for _ in range(n): v=(v<<1)|s.u1()
        return v
    def ue(s):
        z=0
        while s.u1()==0: z+=1
        if z==0: return 0
        return (1<<z)-1 + s.u(z)
    def se(s):
        k=s.ue(); return (k+1)//2 if k%2 else -(k//2)
    def align(s):
        while s.p & 7: s.p+=1

r = R(rbsp)
first_mb = r.ue(); stype = r.ue(); pps = r.ue()
frame_num = r.u(4); idr = r.ue()
noout = r.u1(); longterm = r.u1(); qpd = r.se()
print(f"slice hdr: first_mb={first_mb} type={stype} pps={pps} frame_num={frame_num} idr={idr} qp_delta={qpd}")
assert first_mb == 0 and stype == 7 and pps == 0

# read all MBs as I_PCM, fill luma plane
ENC_W, ENC_H, MBW, MBH = mm.ENC_W, mm.ENC_H, mm.MBW, mm.MBH
Yp = bytearray(ENC_W*ENC_H)
cw = ENC_W//2
for mby in range(MBH):
    for mbx in range(MBW):
        mbt = r.ue()
        assert mbt == 25, f"mb_type {mbt} at {mbx},{mby}"
        r.align()
        for rr in range(16):
            base = (mby*16+rr)*ENC_W + mbx*16
            for c in range(16):
                Yp[base+c] = r.u(8)
        # skip chroma (8x8 Cb + 8x8 Cr)
        for _ in range(64+64): r.u(8)

# reconstruct expected luma from the same frame
mv.FPS = mm.VFPS
frame0 = mv.render_frames()[0]
Yexp, Cb, Cr, _, _ = mm.frame_to_planes(frame0)
match = all(Yp[y*ENC_W+x] == Yexp[y*ENC_W+x] for y in range(mv.H) for x in range(mv.W))
print("LUMA ROUND-TRIP:", "MATCH" if match else "MISMATCH")

# write grayscale PNG of decoded luma (display area)
W, H = mv.W, mv.H
raw = bytearray()
for y in range(H):
    raw.append(0)
    for x in range(W):
        v = Yp[y*ENC_W+x]; raw += bytes((v, v, v))
def ch(t,p): c=t+p; return struct.pack(">I",len(p))+c+struct.pack(">I",zlib.crc32(c)&0xffffffff)
open("mov_frame0.png","wb").write(b"\x89PNG\r\n\x1a\n"+ch(b"IHDR",struct.pack(">IIBBBBB",W,H,8,2,0,0,0))+ch(b"IDAT",zlib.compress(bytes(raw),9))+ch(b"IEND",b""))
print("wrote mov_frame0.png (decoded from the H.264 stream)")
