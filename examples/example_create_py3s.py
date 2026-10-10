#!/usr/bin/env python3
# Copyright (c) 2026 PyGrassReal AI. All Rights Reserved.
# Brand: PyGrassReal (https://pygrassreal.ai)
# Specification: PyGrassReal 3D Splat Single Container Asset Format (.py3s)
"""
PyGrassReal 3D Splat (.py3s) Generator Example
Official Reference Implementation by PyGrassReal AI
"""

import io
import os
import sys

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32" and isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "python"))
from py3s_codec import Py3sContainer

def main():
    print("=" * 60)
    print(" [*] PyGrassReal 3D Splat (.py3s) Generator Example")
    print("=" * 60)

    output_dir = os.path.dirname(os.path.abspath(__file__))
    sample_file = os.path.join(output_dir, "sample_box.py3s")

    # 1. จำลองข้อมูล Visual 3DGS Payload (ปกติจะมาจากไฟล์ .spz จริง)
    fake_spz = b"PYGRASS_3DGS_SPZ_PAYLOAD_DATA_DEMO" * 50

    # 2. จำลองข้อมูล Low-poly Collision Mesh (ปกติจะมาจากไฟล์ .glb หรือ .fbx)
    fake_collider = b"GLTF_2_0_BINARY_COLLIDER_MESH_DEMO" * 20

    # 3. กำหนดค่า Metadata (Alignment, Rotation, Physics bounce)
    metadata = {
        "format": "py3s",
        "version": "1.0.0",
        "generator": "PyGrassReal-Parametric-Example",
        "asset": {
            "name": "sample_box",
            "pointCount": 1000,
            "bounds": {
                "min": [-1.0, -1.0, 0.0],
                "max": [1.0, 1.0, 2.0]
            }
        },
        "collision": {
            "format": "glb",
            "vertexCount": 24,
            "faceCount": 12,
            "type": "BoxCollider",
            "enablePhysicsBounce": True
        },
        "alignment": {
            "rotation": [0.0, -90.0, 0.0],
            "offset": [0.0, 0.0, 0.0],
            "scale": [-1.0, 1.0, 1.0]
        },
        "rendering": {
            "gamma": 0.7,
            "opacityCutoff": 0.05,
            "splatScale": 1.0
        }
    }

    # 4. Pack ข้อมูลทั้งหมดเป็นไฟล์ .py3s ไฟล์เดียว
    packed_bytes = Py3sContainer.pack(
        spz_bytes=fake_spz,
        collider_bytes=fake_collider,
        metadata_dict=metadata
    )

    with open(sample_file, "wb") as f:
        f.write(packed_bytes)

    print(f"✅ บันทึกไฟล์สำเร็จ: {sample_file}")
    print(f"   ขนาดไฟล์: {len(packed_bytes):,} bytes")
    print(f"   Header size: 128 bytes")
    print("\nทดสอบ Unpack กลับมาตรวจสอบ:")
    container = Py3sContainer.unpack(packed_bytes)
    print(f"   Magic Header Valid: {container.version_major}.{container.version_minor}")
    print(f"   SPZ Data: {len(container.spz_data):,} bytes")
    print(f"   Collider Data: {len(container.collider_data):,} bytes")
    print(f"   Asset Name: {container.metadata['asset']['name']}")
    print("=" * 60)

if __name__ == "__main__":
    main()
