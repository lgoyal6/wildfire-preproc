from __future__ import annotations

import argparse
import struct
from pathlib import Path

from PIL import Image


def fourcc(value: str) -> bytes:
    return value.encode("ascii")


def chunk(name: str, payload: bytes) -> bytes:
    padding = b"\0" if len(payload) % 2 else b""
    return fourcc(name) + struct.pack("<I", len(payload)) + payload + padding


def list_chunk(name: str, payload: bytes) -> bytes:
    return fourcc("LIST") + struct.pack("<I", len(payload) + 4) + fourcc(name) + payload


def riff(name: str, payload: bytes) -> bytes:
    return fourcc("RIFF") + struct.pack("<I", len(payload) + 4) + fourcc(name) + payload


def build_avi(frames: list[Path], output: Path, fps: int) -> None:
    if not frames:
        raise SystemExit("No JPEG frames found")

    with Image.open(frames[0]) as image:
        width, height = image.size

    frame_bytes = [frame.read_bytes() for frame in frames]
    max_frame_size = max(len(data) for data in frame_bytes)
    frame_count = len(frame_bytes)
    usec_per_frame = int(1_000_000 / fps)

    avih = chunk(
        "avih",
        struct.pack(
            "<IIIIIIIIIIIIII",
            usec_per_frame,
            max_frame_size * fps,
            0,
            0x10,
            frame_count,
            0,
            1,
            max_frame_size,
            width,
            height,
            0,
            0,
            0,
            0,
        ),
    )

    strh = chunk(
        "strh",
        struct.pack(
            "<4s4sIHHIIIIIIIIhhhh",
            fourcc("vids"),
            fourcc("MJPG"),
            0,
            0,
            0,
            0,
            1,
            fps,
            0,
            frame_count,
            max_frame_size,
            0xFFFFFFFF,
            0,
            0,
            0,
            width,
            height,
        ),
    )

    strf = chunk(
        "strf",
        struct.pack(
            "<IiiHH4sIiiII",
            40,
            width,
            height,
            1,
            24,
            fourcc("MJPG"),
            max_frame_size,
            0,
            0,
            0,
            0,
        ),
    )

    hdrl = list_chunk("hdrl", avih + list_chunk("strl", strh + strf))

    movi_payload = bytearray()
    index_entries = []
    offset = 4
    for data in frame_bytes:
        payload_size = len(data)
        frame_chunk = chunk("00dc", data)
        index_entries.append((fourcc("00dc"), 0x10, offset, payload_size))
        movi_payload.extend(frame_chunk)
        offset += len(frame_chunk)

    movi = list_chunk("movi", bytes(movi_payload))
    idx_payload = b"".join(struct.pack("<4sIII", *entry) for entry in index_entries)
    idx1 = chunk("idx1", idx_payload)
    output.write_bytes(riff("AVI ", hdrl + movi + idx1))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("frames_dir", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--fps", type=int, default=8)
    args = parser.parse_args()
    frames = sorted(args.frames_dir.glob("*.jpg"))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    build_avi(frames, args.output, args.fps)


if __name__ == "__main__":
    main()
