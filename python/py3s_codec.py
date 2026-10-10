#!/usr/bin/env python3
# Copyright (c) 2026 PyGrassReal AI. All Rights Reserved.
# Brand: PyGrassReal (https://pygrassreal.ai)
# Specification: PyGrassReal 3D Splat Single Container Asset Format (.py3s)
"""
PyGrassReal 3D Splat (.py3s) Codec & CLI Tool
Official Reference Implementation by PyGrassReal AI
Packing and Unpacking tool for .py3s Single-Container Assets.
"""

import sys
import os
import json
import struct
import argparse
from typing import Optional, Dict, Any

HEADER_MAGIC = b"PY3S"
HEADER_FORMAT = "<4sHHIIQQQQQQQQ48s"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
assert HEADER_SIZE == 128, f"Header size must be 128 bytes, got {HEADER_SIZE}"

VERSION_MAJOR = 1
VERSION_MINOR = 0

FLAG_NONE = 0x0
FLAG_SPZ_ZSTD = 0x1
FLAG_COLLIDER_GLB = 0x2
FLAG_COLLIDER_FBX = 0x4


class Py3sContainer:
    def __init__(self):
        self.version_major = VERSION_MAJOR
        self.version_minor = VERSION_MINOR
        self.flags = FLAG_SPZ_ZSTD | FLAG_COLLIDER_GLB
        self.spz_data: bytes = b""
        self.collider_data: bytes = b""
        self.metadata: Dict[str, Any] = {}
        self.thumbnail_data: bytes = b""

    @classmethod
    def pack(cls, spz_bytes: bytes, collider_bytes: bytes, metadata_dict: Dict[str, Any], thumbnail_bytes: bytes = b"") -> bytes:
        container = cls()
        container.spz_data = spz_bytes
        container.collider_data = collider_bytes
        container.metadata = metadata_dict
        container.thumbnail_data = thumbnail_bytes

        meta_json = json.dumps(metadata_dict, ensure_ascii=False).encode('utf-8')

        current_offset = HEADER_SIZE
        spz_offset = current_offset
        spz_size = len(container.spz_data)
        current_offset += spz_size

        collider_offset = current_offset
        collider_size = len(container.collider_data)
        current_offset += collider_size

        meta_offset = current_offset
        meta_size = len(meta_json)
        current_offset += meta_size

        section_count = 3
        thumb_offset = 0
        thumb_size = 0
        if container.thumbnail_data:
            thumb_offset = current_offset
            thumb_size = len(container.thumbnail_data)
            current_offset += thumb_size
            section_count = 4

        col_format = metadata_dict.get("collision", {}).get("format", "glb").lower()
        flags = FLAG_SPZ_ZSTD | (FLAG_COLLIDER_FBX if col_format == "fbx" else FLAG_COLLIDER_GLB)

        reserved = b"\x00" * 48

        header = struct.pack(
            HEADER_FORMAT,
            HEADER_MAGIC,
            VERSION_MAJOR,
            VERSION_MINOR,
            section_count,
            flags,
            spz_offset,
            spz_size,
            collider_offset,
            collider_size,
            meta_offset,
            meta_size,
            thumb_offset,
            thumb_size,
            reserved
        )

        return header + container.spz_data + container.collider_data + meta_json + container.thumbnail_data

    @classmethod
    def unpack(cls, buffer: bytes) -> 'Py3sContainer':
        if len(buffer) < HEADER_SIZE:
            raise ValueError(f"Buffer too small: {len(buffer)} < {HEADER_SIZE}")

        magic, v_maj, v_min, sec_count, flags, spz_off, spz_sz, col_off, col_sz, meta_off, meta_sz, thumb_off, thumb_sz, _ = struct.unpack_from(
            HEADER_FORMAT, buffer, 0
        )

        if magic != HEADER_MAGIC:
            raise ValueError(f"Invalid PY3S magic header: {magic}")

        container = cls()
        container.version_major = v_maj
        container.version_minor = v_min
        container.flags = flags

        if spz_sz > 0:
            container.spz_data = buffer[spz_off : spz_off + spz_sz]

        if col_sz > 0:
            container.collider_data = buffer[col_off : col_off + col_sz]

        if meta_sz > 0:
            meta_json = buffer[meta_off : meta_off + meta_sz].decode('utf-8')
            container.metadata = json.loads(meta_json)

        if thumb_sz > 0 and thumb_off > 0:
            container.thumbnail_data = buffer[thumb_off : thumb_off + thumb_sz]

        return container


def cmd_pack(args):
    splat_path = getattr(args, "splat", None) or getattr(args, "spz", None)
    if not splat_path or not os.path.exists(splat_path):
        print(f"Error: Visual splat input file not found: {splat_path}")
        sys.exit(1)

    with open(splat_path, "rb") as f:
        spz_data = f.read()

    collider_data = b""
    if args.collider and os.path.exists(args.collider):
        with open(args.collider, "rb") as f:
            collider_data = f.read()

    metadata = {}
    if args.metadata and os.path.exists(args.metadata):
        with open(args.metadata, "r", encoding="utf-8") as f:
            metadata = json.load(f)
    else:
        # Default metadata
        col_ext = os.path.splitext(args.collider)[1].lstrip('.').lower() if args.collider else "glb"
        metadata = {
            "format": "py3s",
            "version": "1.0.0",
            "generator": "py3s-codec-cli",
            "asset": {
                "name": os.path.splitext(os.path.basename(args.output))[0],
                "pointCount": 0
            },
            "collision": {
                "format": col_ext,
                "enablePhysicsBounce": True
            },
            "alignment": {
                "rotation": [0.0, -90.0, 0.0],
                "offset": [0.0, 0.0, 0.0],
                "scale": [-1.0, 1.0, 1.0]
            }
        }

    thumb_data = b""
    if args.thumbnail and os.path.exists(args.thumbnail):
        with open(args.thumbnail, "rb") as f:
            thumb_data = f.read()

    packed = Py3sContainer.pack(spz_data, collider_data, metadata, thumb_data)
    with open(args.output, "wb") as f:
        f.write(packed)

    print(f"✅ Successfully packed into '{args.output}' ({len(packed):,} bytes)")
    print(f"   - SPZ: {len(spz_data):,} bytes")
    print(f"   - Collider: {len(collider_data):,} bytes")
    print(f"   - Metadata: {len(json.dumps(metadata)):,} bytes")
    if thumb_data:
        print(f"   - Thumbnail: {len(thumb_data):,} bytes")


def cmd_unpack(args):
    with open(args.input, "rb") as f:
        buffer = f.read()

    container = Py3sContainer.unpack(buffer)
    out_dir = args.outdir or os.path.splitext(args.input)[0] + "_extracted"
    os.makedirs(out_dir, exist_ok=True)

    base_name = os.path.splitext(os.path.basename(args.input))[0]

    # 1. SPZ
    if container.spz_data:
        spz_path = os.path.join(out_dir, f"{base_name}.spz")
        with open(spz_path, "wb") as f:
            f.write(container.spz_data)
        print(f"   Extracted SPZ: {spz_path} ({len(container.spz_data):,} bytes)")

    # 2. Collider
    if container.collider_data:
        col_fmt = container.metadata.get("collision", {}).get("format", "glb").lower()
        col_path = os.path.join(out_dir, f"{base_name}_collider.{col_fmt}")
        with open(col_path, "wb") as f:
            f.write(container.collider_data)
        print(f"   Extracted Collider: {col_path} ({len(container.collider_data):,} bytes)")

    # 3. Metadata
    if container.metadata:
        meta_path = os.path.join(out_dir, f"{base_name}_metadata.json")
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(container.metadata, f, indent=2, ensure_ascii=False)
        print(f"   Extracted Metadata: {meta_path}")

    # 4. Thumbnail
    if container.thumbnail_data:
        thumb_path = os.path.join(out_dir, f"{base_name}_thumb.webp")
        with open(thumb_path, "wb") as f:
            f.write(container.thumbnail_data)
        print(f"   Extracted Thumbnail: {thumb_path}")

    print(f"✅ Finished extracting '{args.input}' into '{out_dir}/'")


def cmd_info(args):
    with open(args.input, "rb") as f:
        buffer = f.read()

    container = Py3sContainer.unpack(buffer)
    print(f"==================================================")
    print(f" PY3S Container Info: {args.input}")
    print(f"==================================================")
    print(f" Version      : {container.version_major}.{container.version_minor}")
    print(f" File Size    : {len(buffer):,} bytes")
    print(f" SPZ Payload  : {len(container.spz_data):,} bytes")
    print(f" Collider Mesh: {len(container.collider_data):,} bytes")
    print(f" Thumbnail    : {len(container.thumbnail_data):,} bytes")
    print(f" Metadata     :")
    print(json.dumps(container.metadata, indent=2, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description="PyGrassReal 3D Splat (.py3s) Codec CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # pack
    p_pack = subparsers.add_parser("pack", help="Pack Visual Splat + Collision Mesh + Metadata into .py3s")
    p_pack.add_argument("--splat", "--spz", dest="splat", required=True, help="Path to input 3DGS visual splat file")
    p_pack.add_argument("--collider", required=False, help="Path to input collision geometry mesh")
    p_pack.add_argument("--metadata", required=False, help="Path to custom metadata .json")
    p_pack.add_argument("--thumbnail", required=False, help="Path to thumbnail preview image")
    p_pack.add_argument("-o", "--output", required=True, help="Path to output .py3s file")
    p_pack.set_defaults(func=cmd_pack)

    # unpack
    p_unpack = subparsers.add_parser("unpack", help="Unpack .py3s file into constituent files")
    p_unpack.add_argument("input", help="Path to input .py3s file")
    p_unpack.add_argument("-d", "--outdir", help="Directory to output extracted files")
    p_unpack.set_defaults(func=cmd_unpack)

    # info
    p_info = subparsers.add_parser("info", help="Inspect .py3s container metadata")
    p_info.add_argument("input", help="Path to input .py3s file")
    p_info.set_defaults(func=cmd_info)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
