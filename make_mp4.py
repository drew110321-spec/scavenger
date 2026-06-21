#!/usr/bin/env python3
"""
Convert the hand-coded H.264 stream into an MP4 (ISO BMFF) — pure Python, no ffmpeg.

Reuses the verified H.264 I_PCM encoder from make_mov.py and re-muxes it into an
.mp4 with ISO branding and a corrected PCM ('sowt') audio sample entry so the
background music is carried with the standard MP4 boxes.

    python3 make_mp4.py   ->  roadai_demo.mp4
"""

import struct
import make_video as mv
import make_mov as mm

OUT = "roadai_demo.mp4"
SR = mm.SR
VFPS = mm.VFPS
DISP_W, DISP_H = mm.DISP_W, mm.DISP_H
box, fullbox = mm.box, mm.fullbox


def audio_sample_entry(naudio):
    # Correct QuickTime v0 sound sample description (sowt = signed LE PCM)
    return box(b"sowt",
        b"\x00" * 6 + struct.pack(">H", 1) +     # reserved + data_ref_index
        struct.pack(">H", 0) +                   # version
        struct.pack(">H", 0) +                   # revision level
        struct.pack(">I", 0) +                   # vendor
        struct.pack(">H", 1) +                   # num channels
        struct.pack(">H", 16) +                  # sample size (bits)
        struct.pack(">h", 0) +                   # compression id
        struct.pack(">H", 0) +                   # packet size
        struct.pack(">I", SR << 16))             # sample rate 16.16


def build_moov(nframes, vsizes, video_off, naudio):
    MV_TS = 600
    vdur = nframes * (MV_TS // VFPS)

    # ---- video trak (avc1 = standard MP4 H.264) ----
    avcc = (bytes([1, 66, 0, 41]) + bytes([0xFF]) + bytes([0xE1]) +
            struct.pack(">H", len(mm.SPS)) + mm.SPS +
            bytes([1]) + struct.pack(">H", len(mm.PPS)) + mm.PPS)
    avc1 = box(b"avc1",
        b"\x00" * 6 + struct.pack(">H", 1) +
        struct.pack(">HH", 0, 0) + b"\x00" * 12 +
        struct.pack(">HH", DISP_W, DISP_H) +
        struct.pack(">II", 0x00480000, 0x00480000) +
        struct.pack(">I", 0) + struct.pack(">H", 1) +
        bytes([4]) + b"h264" + b"\x00" * 27 +
        struct.pack(">H", 0x0018) + struct.pack(">h", -1) +
        box(b"avcC", avcc))
    v_stbl = box(b"stbl",
        fullbox(b"stsd", 0, 0, struct.pack(">I", 1), avc1),
        fullbox(b"stts", 0, 0, struct.pack(">I", 1), struct.pack(">II", nframes, MV_TS // VFPS)),
        fullbox(b"stsc", 0, 0, struct.pack(">I", 1), struct.pack(">III", 1, nframes, 1)),
        fullbox(b"stsz", 0, 0, struct.pack(">I", 0),
                struct.pack(">I", nframes) + b"".join(struct.pack(">I", s) for s in vsizes)),
        fullbox(b"stco", 0, 0, struct.pack(">I", 1), struct.pack(">I", video_off)))
    v_minf = box(b"minf",
        fullbox(b"vmhd", 0, 1, struct.pack(">HHHH", 0, 0, 0, 0)),
        box(b"dinf", fullbox(b"dref", 0, 0, struct.pack(">I", 1), fullbox(b"url ", 0, 1))),
        v_stbl)
    v_mdia = box(b"mdia",
        fullbox(b"mdhd", 0, 0, struct.pack(">IIII", 0, 0, MV_TS, vdur) + struct.pack(">HH", 0x55c4, 0)),
        fullbox(b"hdlr", 0, 0, b"\x00" * 4 + b"vide" + b"\x00" * 12 + b"VideoHandler\x00"),
        v_minf)
    v_tkhd = fullbox(b"tkhd", 0, 7,
        struct.pack(">IIIII", 0, 0, 1, 0, vdur) + b"\x00" * 8 +
        struct.pack(">hhhh", 0, 0, 0, 0) +
        struct.pack(">iiiiiiiii", 0x10000, 0, 0, 0, 0x10000, 0, 0, 0, 0x40000000) +
        struct.pack(">II", DISP_W << 16, DISP_H << 16))
    v_trak = box(b"trak", v_tkhd, v_mdia)

    # ---- audio trak (PCM) ----
    adur = int(naudio * MV_TS / SR)
    a_stbl = box(b"stbl",
        fullbox(b"stsd", 0, 0, struct.pack(">I", 1), audio_sample_entry(naudio)),
        fullbox(b"stts", 0, 0, struct.pack(">I", 1), struct.pack(">II", naudio, 1)),
        fullbox(b"stsc", 0, 0, struct.pack(">I", 1), struct.pack(">III", 1, naudio, 1)),
        fullbox(b"stsz", 0, 0, struct.pack(">I", 2), struct.pack(">I", naudio)),
        fullbox(b"stco", 0, 0, struct.pack(">I", 1), struct.pack(">I", video_off + sum(vsizes))))
    a_minf = box(b"minf",
        fullbox(b"smhd", 0, 0, struct.pack(">HH", 0, 0)),
        box(b"dinf", fullbox(b"dref", 0, 0, struct.pack(">I", 1), fullbox(b"url ", 0, 1))),
        a_stbl)
    a_mdia = box(b"mdia",
        fullbox(b"mdhd", 0, 0, struct.pack(">IIII", 0, 0, SR, naudio) + struct.pack(">HH", 0x55c4, 0)),
        fullbox(b"hdlr", 0, 0, b"\x00" * 4 + b"soun" + b"\x00" * 12 + b"SoundHandler\x00"),
        a_minf)
    a_tkhd = fullbox(b"tkhd", 0, 7,
        struct.pack(">IIIII", 0, 0, 2, 0, adur) + b"\x00" * 8 +
        struct.pack(">hhhh", 0, 0, 0x0100, 0) +
        struct.pack(">iiiiiiiii", 0x10000, 0, 0, 0, 0x10000, 0, 0, 0, 0x40000000) +
        struct.pack(">II", 0, 0))
    a_trak = box(b"trak", a_tkhd, a_mdia)

    dur = max(vdur, adur)
    mvhd = fullbox(b"mvhd", 0, 0,
        struct.pack(">IIII", 0, 0, MV_TS, dur) +
        struct.pack(">I", 0x00010000) + struct.pack(">H", 0x0100) + struct.pack(">H", 0) +
        struct.pack(">II", 0, 0) +
        struct.pack(">iiiiiiiii", 0x10000, 0, 0, 0, 0x10000, 0, 0, 0, 0x40000000) +
        b"\x00" * 24 + struct.pack(">I", 3))
    return box(b"moov", mvhd, v_trak, a_trak)


def main():
    mv.FPS = VFPS
    print("Rendering frames...")
    frames = mv.render_frames()
    nframes = len(frames)
    print(f"  {nframes} frames @ {VFPS}fps")

    print("Encoding H.264 (I_PCM)...")
    samples = []
    for i, fr in enumerate(frames):
        Y, Cb, Cr, cw, ch = mm.frame_to_planes(fr)
        unit = mm.nal(3, 5, mm.encode_slice(Y, Cb, Cr, cw, ch, i & 0xFFFF))
        samples.append(struct.pack(">I", len(unit)) + unit)
        if (i + 1) % 30 == 0:
            print(f"  {i+1}/{nframes}")
    vsizes = [len(s) for s in samples]

    print("Synthesizing music (PCM)...")
    audio = mv.synth_music(int(nframes * SR / VFPS))
    naudio = len(audio) // 2

    ftyp = box(b"ftyp", b"isom" + struct.pack(">I", 0x200) +
               b"isom" + b"iso2" + b"avc1" + b"mp42" + b"qt  ")
    moov0 = build_moov(nframes, vsizes, 0, naudio)
    video_off = len(ftyp) + len(moov0) + 8
    moov = build_moov(nframes, vsizes, video_off, naudio)
    assert len(moov) == len(moov0)

    mdat_body = b"".join(samples) + audio
    mdat = struct.pack(">I", 8 + len(mdat_body)) + b"mdat" + mdat_body
    data = ftyp + moov + mdat
    with open(OUT, "wb") as fh:
        fh.write(data)
    print(f"Wrote {OUT}  ({len(data)/1_048_576:.1f} MB, {nframes/VFPS:.1f}s, "
          f"{DISP_W}x{DISP_H}, H.264 + PCM audio)")


if __name__ == "__main__":
    main()
