#!/usr/bin/env python3
"""
Hand-coded H.264 (.mov) encoder — pure Python stdlib, NO ffmpeg.

Encodes the demo slides as H.264 using only I_PCM macroblocks (raw, lossless,
no DCT/CAVLC needed) and muxes them with the background music as uncompressed
16-bit PCM ('sowt') into a QuickTime .mov — which iPhones play natively, WITH
sound.

    python3 make_mov.py   ->  roadai_demo.mov

It's "uncompressed" so the file is large, but it is a genuine, standards-shaped
H.264/MOV that a phone can open.
"""

import struct
import make_video as mv

OUT = "roadai_demo.mov"
VFPS = 4                      # frames/sec for the video track (keeps size sane)
SR = mv.SR

# pad height up to a multiple of 16 for macroblocks; crop back in SPS
DISP_W, DISP_H = mv.W, mv.H               # 640 x 360 displayed
ENC_W = (DISP_W + 15) // 16 * 16          # 640
ENC_H = (DISP_H + 15) // 16 * 16          # 368
MBW, MBH = ENC_W // 16, ENC_H // 16       # 40 x 23
CROP_BOTTOM = (ENC_H - DISP_H) // 2       # in 2-luma-sample units -> 4


# ── Bit writer (MSB-first, for H.264 RBSP) ───────────────────────────────────────
class BitW:
    def __init__(self):
        self.b = bytearray()
        self.cur = 0
        self.n = 0

    def bit(self, x):
        self.cur = (self.cur << 1) | (x & 1)
        self.n += 1
        if self.n == 8:
            self.b.append(self.cur)
            self.cur = 0
            self.n = 0

    def bits(self, val, k):
        for i in range(k - 1, -1, -1):
            self.bit((val >> i) & 1)

    def ue(self, v):
        v += 1
        nbits = v.bit_length()
        for _ in range(nbits - 1):
            self.bit(0)
        for i in range(nbits - 1, -1, -1):
            self.bit((v >> i) & 1)

    def se(self, v):
        self.ue(0 if v == 0 else (2 * abs(v) - (1 if v > 0 else 0)))

    def byte_align_zero(self):
        while self.n != 0:
            self.bit(0)

    def rbsp_trailing(self):
        self.bit(1)
        self.byte_align_zero()

    def bytes_(self, data):           # only valid when byte aligned
        assert self.n == 0
        self.b += data

    def get(self):
        assert self.n == 0
        return bytes(self.b)


def emulation_prevent(rbsp):
    out = bytearray()
    zeros = 0
    for byte in rbsp:
        if zeros >= 2 and byte <= 3:
            out.append(3)
            zeros = 0
        out.append(byte)
        zeros = zeros + 1 if byte == 0 else 0
    return bytes(out)


def nal(nal_ref_idc, nal_type, rbsp):
    hdr = (nal_ref_idc << 5) | nal_type
    return bytes([hdr]) + emulation_prevent(rbsp)


# ── SPS / PPS ────────────────────────────────────────────────────────────────────
def build_sps():
    w = BitW()
    w.bits(66, 8)             # profile_idc = Baseline
    w.bits(0, 8)              # constraint flags + reserved
    w.bits(41, 8)            # level_idc = 4.1
    w.ue(0)                   # seq_parameter_set_id
    w.ue(0)                   # log2_max_frame_num_minus4 -> frame_num is 4 bits
    w.ue(2)                   # pic_order_cnt_type = 2
    w.ue(1)                   # max_num_ref_frames
    w.bit(0)                  # gaps_in_frame_num_value_allowed_flag
    w.ue(MBW - 1)            # pic_width_in_mbs_minus1
    w.ue(MBH - 1)            # pic_height_in_map_units_minus1
    w.bit(1)                  # frame_mbs_only_flag
    w.bit(1)                  # direct_8x8_inference_flag
    w.bit(1)                  # frame_cropping_flag
    w.ue(0)                   # crop left
    w.ue(0)                   # crop right
    w.ue(0)                   # crop top
    w.ue(CROP_BOTTOM)         # crop bottom
    w.bit(0)                  # vui_parameters_present_flag
    w.rbsp_trailing()
    return w.get()


def build_pps():
    w = BitW()
    w.ue(0)     # pic_parameter_set_id
    w.ue(0)     # seq_parameter_set_id
    w.bit(0)    # entropy_coding_mode_flag (CAVLC)
    w.bit(0)    # bottom_field_pic_order_in_frame_present_flag
    w.ue(0)     # num_slice_groups_minus1
    w.ue(0)     # num_ref_idx_l0_default_active_minus1
    w.ue(0)     # num_ref_idx_l1_default_active_minus1
    w.bit(0)    # weighted_pred_flag
    w.bits(0, 2)  # weighted_bipred_idc
    w.se(0)     # pic_init_qp_minus26
    w.se(0)     # pic_init_qs_minus26
    w.se(0)     # chroma_qp_index_offset
    w.bit(0)    # deblocking_filter_control_present_flag
    w.bit(0)    # constrained_intra_pred_flag
    w.bit(0)    # redundant_pic_cnt_present_flag
    w.rbsp_trailing()
    return w.get()


# ── RGB(palette index) frame -> YUV420 planes (studio-range BT.601) ──────────────
def palette_yuv():
    yt, ut, vt = [], [], []
    for (r, g, b) in mv.PAL:
        y = 16 + (65.481 * r + 128.553 * g + 24.966 * b) / 255.0
        u = 128 + (-37.797 * r - 74.203 * g + 112.0 * b) / 255.0
        v = 128 + (112.0 * r - 93.786 * g - 18.214 * b) / 255.0
        yt.append(max(0, min(255, int(round(y)))))
        ut.append(max(0, min(255, int(round(u)))))
        vt.append(max(0, min(255, int(round(v)))))
    # pad palette to 256
    while len(yt) < 256:
        yt.append(16); ut.append(128); vt.append(128)
    return yt, ut, vt

YT, UT, VT = palette_yuv()


def frame_to_planes(buf):
    """buf: top-down W*H palette indices -> (Y[ENC_W*ENC_H], Cb, Cr) subsampled."""
    W, H = mv.W, mv.H
    Y = bytearray([16]) * (ENC_W * ENC_H)
    # luma
    for y in range(H):
        row = buf[y * W:(y + 1) * W]
        o = y * ENC_W
        yp = Y
        for x in range(W):
            yp[o + x] = YT[row[x]]
        # pad columns (W==ENC_W here, so none)
    # padded bottom rows already 16
    # chroma (subsample 2x2 average over the displayed area; pad rest)
    cw, ch = ENC_W // 2, ENC_H // 2
    Cb = bytearray([128]) * (cw * ch)
    Cr = bytearray([128]) * (cw * ch)
    for cy in range(H // 2):
        for cx in range(W // 2):
            x0 = cx * 2; y0 = cy * 2
            i00 = buf[y0 * W + x0]; i01 = buf[y0 * W + x0 + 1]
            i10 = buf[(y0 + 1) * W + x0]; i11 = buf[(y0 + 1) * W + x0 + 1]
            cb = (UT[i00] + UT[i01] + UT[i10] + UT[i11] + 2) >> 2
            cr = (VT[i00] + VT[i01] + VT[i10] + VT[i11] + 2) >> 2
            Cb[cy * cw + cx] = cb
            Cr[cy * cw + cx] = cr
    return Y, Cb, Cr, cw, ch


def encode_slice(Y, Cb, Cr, cw, ch, idr_pic_id):
    w = BitW()
    # slice header (IDR)
    w.ue(0)          # first_mb_in_slice
    w.ue(7)          # slice_type = 7 (I, all slices I)
    w.ue(0)          # pic_parameter_set_id
    w.bits(0, 4)     # frame_num (log2_max_frame_num = 4)
    w.ue(idr_pic_id) # idr_pic_id
    # pic_order_cnt_type == 2 -> nothing
    # dec_ref_pic_marking (IDR)
    w.bit(0)         # no_output_of_prior_pics_flag
    w.bit(0)         # long_term_reference_flag
    w.se(0)          # slice_qp_delta (QP = 26)
    # slice_data: every MB is I_PCM
    for mby in range(MBH):
        for mbx in range(MBW):
            w.ue(25)            # mb_type = I_PCM
            w.byte_align_zero() # pcm_alignment_zero_bit(s)
            # luma 16x16
            ybase = (mby * 16) * ENC_W + mbx * 16
            for r in range(16):
                o = ybase + r * ENC_W
                w.bytes_(bytes(Y[o:o + 16]))
            # chroma 8x8 Cb then Cr
            cbase = (mby * 8) * cw + mbx * 8
            for r in range(8):
                o = cbase + r * cw
                w.bytes_(bytes(Cb[o:o + 8]))
            for r in range(8):
                o = cbase + r * cw
                w.bytes_(bytes(Cr[o:o + 8]))
    w.rbsp_trailing()
    return w.get()


# ── ISOBMFF / QuickTime box helpers ──────────────────────────────────────────────
def box(typ, *payload):
    body = b"".join(payload)
    return struct.pack(">I", 8 + len(body)) + typ + body


def fullbox(typ, version, flags, *payload):
    return box(typ, bytes([version]) + struct.pack(">I", flags)[1:], *payload)


def build_moov(nframes, vsizes, video_off, audio_bytes_len, naudio):
    MV_TS = 600
    vdur_mv = nframes * (MV_TS // VFPS)
    # ---- video trak ----
    avcc = (bytes([1, 66, 0, 41]) +              # cfgver, profile, compat, level
            bytes([0xFF]) +                       # 6b reserved + lengthSizeMinusOne=3
            bytes([0xE1]) +                       # 3b reserved + numSPS=1
            struct.pack(">H", len(SPS)) + SPS +
            bytes([1]) + struct.pack(">H", len(PPS)) + PPS)
    avcC = box(b"avcC", avcc)
    avc1 = box(b"avc1",
        b"\x00" * 6 + struct.pack(">H", 1) +      # reserved, data_ref_index
        struct.pack(">HH", 0, 0) + b"\x00" * 12 + # predefined/reserved
        struct.pack(">HH", DISP_W, DISP_H) +
        struct.pack(">II", 0x00480000, 0x00480000) +
        struct.pack(">I", 0) + struct.pack(">H", 1) +
        bytes([4]) + b"h264" + b"\x00" * 27 +     # compressorname (pascal, 32)
        struct.pack(">H", 0x0018) + struct.pack(">h", -1) +
        avcC)
    v_stsd = fullbox(b"stsd", 0, 0, struct.pack(">I", 1), avc1)
    v_stts = fullbox(b"stts", 0, 0, struct.pack(">I", 1),
                     struct.pack(">II", nframes, MV_TS // VFPS))
    v_stsc = fullbox(b"stsc", 0, 0, struct.pack(">I", 1),
                     struct.pack(">III", 1, nframes, 1))
    v_stsz = fullbox(b"stsz", 0, 0, struct.pack(">I", 0),
                     struct.pack(">I", nframes) +
                     b"".join(struct.pack(">I", s) for s in vsizes))
    v_stco = fullbox(b"stco", 0, 0, struct.pack(">I", 1),
                     struct.pack(">I", video_off))
    v_stbl = box(b"stbl", v_stsd, v_stts, v_stsc, v_stsz, v_stco)
    v_vmhd = fullbox(b"vmhd", 0, 1, struct.pack(">HHHH", 0, 0, 0, 0))
    v_dref = fullbox(b"dref", 0, 0, struct.pack(">I", 1),
                     fullbox(b"url ", 0, 1))
    v_dinf = box(b"dinf", v_dref)
    v_minf = box(b"minf", v_vmhd, v_dinf, v_stbl)
    v_hdlr = fullbox(b"hdlr", 0, 0, b"\x00" * 4 + b"vide" + b"\x00" * 12 + b"VideoHandler\x00")
    v_mdhd = fullbox(b"mdhd", 0, 0, struct.pack(">IIII", 0, 0, MV_TS, vdur_mv) +
                     struct.pack(">HH", 0x55c4, 0))
    v_mdia = box(b"mdia", v_mdhd, v_hdlr, v_minf)
    v_tkhd = fullbox(b"tkhd", 0, 7,
        struct.pack(">IIIII", 0, 0, 1, 0, vdur_mv) + b"\x00" * 8 +
        struct.pack(">hhhh", 0, 0, 0, 0) +
        struct.pack(">iiiiiiiii", 0x10000, 0, 0, 0, 0x10000, 0, 0, 0, 0x40000000) +
        struct.pack(">II", DISP_W << 16, DISP_H << 16))
    v_trak = box(b"trak", v_tkhd, v_mdia)

    # ---- audio trak ----
    adur_mv = int(naudio * MV_TS / SR)
    a_stsd = fullbox(b"stsd", 0, 0, struct.pack(">I", 1),
        box(b"sowt",
            b"\x00" * 6 + struct.pack(">H", 1) +           # reserved + data_ref_index
            struct.pack(">H", 0) +                         # version
            struct.pack(">H", 0) +                         # revision level
            struct.pack(">I", 0) +                         # vendor
            struct.pack(">H", 1) +                         # num channels
            struct.pack(">H", 16) +                        # sample size (bits)
            struct.pack(">h", 0) +                         # compression id
            struct.pack(">H", 0) +                         # packet size
            struct.pack(">I", SR << 16)))                  # sample rate 16.16
    a_stts = fullbox(b"stts", 0, 0, struct.pack(">I", 1),
                     struct.pack(">II", naudio, 1))
    a_stsc = fullbox(b"stsc", 0, 0, struct.pack(">I", 1),
                     struct.pack(">III", 1, naudio, 1))
    a_stsz = fullbox(b"stsz", 0, 0, struct.pack(">I", 2), struct.pack(">I", naudio))
    a_stco = fullbox(b"stco", 0, 0, struct.pack(">I", 1),
                     struct.pack(">I", video_off + sum(vsizes)))
    a_stbl = box(b"stbl", a_stsd, a_stts, a_stsc, a_stsz, a_stco)
    a_smhd = fullbox(b"smhd", 0, 0, struct.pack(">HH", 0, 0))
    a_dinf = box(b"dinf", fullbox(b"dref", 0, 0, struct.pack(">I", 1), fullbox(b"url ", 0, 1)))
    a_minf = box(b"minf", a_smhd, a_dinf, a_stbl)
    a_hdlr = fullbox(b"hdlr", 0, 0, b"\x00" * 4 + b"soun" + b"\x00" * 12 + b"SoundHandler\x00")
    a_mdhd = fullbox(b"mdhd", 0, 0, struct.pack(">IIII", 0, 0, SR, naudio) +
                     struct.pack(">HH", 0x55c4, 0))
    a_mdia = box(b"mdia", a_mdhd, a_hdlr, a_minf)
    a_tkhd = fullbox(b"tkhd", 0, 7,
        struct.pack(">IIIII", 0, 0, 2, 0, adur_mv) + b"\x00" * 8 +
        struct.pack(">hhhh", 0, 0, 0x0100, 0) +
        struct.pack(">iiiiiiiii", 0x10000, 0, 0, 0, 0x10000, 0, 0, 0, 0x40000000) +
        struct.pack(">II", 0, 0))
    a_trak = box(b"trak", a_tkhd, a_mdia)

    dur = max(vdur_mv, adur_mv)
    mvhd = fullbox(b"mvhd", 0, 0,
        struct.pack(">IIII", 0, 0, MV_TS, dur) +
        struct.pack(">I", 0x00010000) + struct.pack(">H", 0x0100) +
        struct.pack(">H", 0) + struct.pack(">II", 0, 0) +
        struct.pack(">iiiiiiiii", 0x10000, 0, 0, 0, 0x10000, 0, 0, 0, 0x40000000) +
        b"\x00" * 24 + struct.pack(">I", 3))
    return box(b"moov", mvhd, v_trak, a_trak)


SPS = build_sps()
PPS = build_pps()


def main():
    mv.FPS = VFPS  # make render_frames + progress use the video fps
    print("Rendering frames...")
    frames = mv.render_frames()
    nframes = len(frames)
    print(f"  {nframes} frames @ {VFPS}fps  ({nframes/VFPS:.1f}s), enc {ENC_W}x{ENC_H}")

    print("Encoding H.264 (I_PCM macroblocks)...")
    samples = []
    for i, fr in enumerate(frames):
        Y, Cb, Cr, cw, ch = frame_to_planes(fr)
        slice_rbsp = encode_slice(Y, Cb, Cr, cw, ch, i & 0xFFFF)
        unit = nal(3, 5, slice_rbsp)                  # IDR
        samples.append(struct.pack(">I", len(unit)) + unit)
        if (i + 1) % 30 == 0:
            print(f"  {i+1}/{nframes}")
    vsizes = [len(s) for s in samples]

    print("Synthesizing background music (PCM)...")
    naudio = int(nframes * SR / VFPS)
    audio = mv.synth_music(naudio)
    naudio = len(audio) // 2

    # two-pass: build moov with placeholder offsets to learn its size
    ftyp = box(b"ftyp", b"qt  " + struct.pack(">I", 0x20060000) +
               b"qt  " + b"isom" + b"mp42")
    moov0 = build_moov(nframes, vsizes, 0, len(audio), naudio)
    video_off = len(ftyp) + len(moov0) + 8           # +8 for mdat header
    moov = build_moov(nframes, vsizes, video_off, len(audio), naudio)
    assert len(moov) == len(moov0)

    mdat_body = b"".join(samples) + audio
    mdat = struct.pack(">I", 8 + len(mdat_body)) + b"mdat" + mdat_body

    data = ftyp + moov + mdat
    with open(OUT, "wb") as fh:
        fh.write(data)
    print(f"Wrote {OUT}  ({len(data)/1_048_576:.1f} MB, {nframes/VFPS:.1f}s, "
          f"{DISP_W}x{DISP_H}, H.264 I_PCM + PCM audio)")


if __name__ == "__main__":
    main()
