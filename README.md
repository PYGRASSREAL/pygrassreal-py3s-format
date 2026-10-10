# PyGrassReal 3D Splat (`.py3s`) File Format

<div align="center">

[![Specification](https://img.shields.io/badge/Specification-v1.0.0-blue.svg)](SPECIFICATION.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Magic String](https://img.shields.io/badge/Magic-PY3S-orange.svg)](#binary-layout)
[![Engines](https://img.shields.io/badge/Engines-Unreal%205%20%7C%20Three.js%20%7C%20Python-purple.svg)](#implementations)

**The Unified Single-Container Asset Format Combining 3D Gaussian Splatting Visuals with 1:1 Physics Collision.**

[📖 Read Specification](SPECIFICATION.md) • [🐍 Python SDK](python/) • [⚡ C++ Implementation](cpp/) • [🌐 TypeScript / Web](typescript/) • [🏛️ Official Platform](https://pygrassreal.ai)

</div>

---

## 💡 The Problem with 3DGS Assets
Standard 3D Gaussian Splatting formats (`.ply`, `.splat`, `.spz`) represent only visual color clouds with ellipsoidal splats. They **lack physical geometry**, meaning:
- Characters and vehicles pass straight through them like ghosts.
- Developers are forced to manually model separate low-poly colliders (`.fbx` / `.glb`) and painstakingly calibrate scale, rotation, and offsets in the game engine.
- Managing multiple detached files per 3D asset leads to broken references and tedious workflow friction.

## 🚀 The Solution: `.py3s` Single-Container Format
Developed by **PyGrassReal AI**, **`.py3s`** is a unified binary container that bundles:
1. **Visual Layer:** Ultra-compact 3D Gaussian Splatting payload (compatible with `.spz`).
2. **Physics Layer:** Optimized low-poly collision mesh (GLB / UCX convex hulls) for 100% solid navigation and raycasting.
3. **Calibrated Alignment:** Embedded transform matrices (offset, rotation, scale) for instant 1:1 ground-aligned snapping.
4. **Metadata & Thumbnail:** Embedded JSON metadata and preview imagery.

> **Result:** Drag a single `.py3s` file into Unreal Engine 5 or a WebGL viewer, and it renders photorealistically with solid collision physics enabled **instantly in 1 click**.

---

## 📐 Binary Layout Overview

A `.py3s` file consists of a fixed **128-byte Header** followed by 4 payload sections:

```text
┌────────────────────────────────────────────────────────┐
│             PY3S File Header (128 Bytes)               │  Offset 0x00
├────────────────────────────────────────────────────────┤
│          Section 1: SPZ Payload (Visual 3DGS)          │  Offset = SpzOffset (default 0x80)
├────────────────────────────────────────────────────────┤
│          Section 2: Collision Mesh (Physics)           │  Offset = ColliderOffset
├────────────────────────────────────────────────────────┤
│          Section 3: Metadata JSON (UTF-8)              │  Offset = MetadataOffset
├────────────────────────────────────────────────────────┤
│          Section 4: Thumbnail Image (Optional)         │  Offset = ThumbnailOffset
└────────────────────────────────────────────────────────┘
```

### 128-Byte Fixed Header Layout

| Field | Type | Size | Description |
|---|---|---|---|
| `Magic` | `char[4]` | 4 B | Always `"PY3S"` (`0x50 0x59 0x33 0x53`) |
| `VersionMajor` | `uint16` | 2 B | Major version (`1`) |
| `VersionMinor` | `uint16` | 2 B | Minor version (`0`) |
| `Flags` | `uint32` | 4 B | Compression & collider format flags |
| `Reserved1` | `uint32` | 4 B | Reserved for future alignment |
| `SpzOffset` | `uint64` | 8 B | Byte offset to Section 1 (Visual SPZ) |
| `SpzSize` | `uint64` | 8 B | Uncompressed/Compressed SPZ size in bytes |
| `ColliderOffset` | `uint64` | 8 B | Byte offset to Section 2 (Collision Mesh) |
| `ColliderSize` | `uint64` | 8 B | Collision mesh size in bytes |
| `MetadataOffset` | `uint64` | 8 B | Byte offset to Section 3 (JSON Metadata) |
| `MetadataSize` | `uint64` | 8 B | Metadata size in bytes |
| `ThumbnailOffset`| `uint64` | 8 B | Byte offset to Section 4 (Thumbnail) |
| `ThumbnailSize` | `uint64` | 8 B | Thumbnail size in bytes |
| `Reserved` | `uint8[48]` | 48 B | Zero-padded for future extensions |

For comprehensive technical specifications, read [SPECIFICATION.md](SPECIFICATION.md).

---

## 🛠️ Official Implementations

This repository includes open-source reference implementations across multiple platforms:

### 1. Python SDK (`python/`)
Zero-dependency Python implementation for packing, unpacking, and CLI batch operations:

```bash
# Unpack a .py3s file into component parts
python python/py3s_codec.py unpack house.py3s -o ./output/

# Pack SPZ visual and GLB collider into a single .py3s file
python python/py3s_codec.py pack --spz house.spz --collider house_collider.glb --meta metadata.json -o house.py3s

# Inspect file contents and metadata
python python/py3s_codec.py info house.py3s
```

### 2. C++ SDK (`cpp/`)
High-performance C++ codec for game engines (Unreal Engine 5, Unity, Custom OpenGL/DirectX/Vulkan engines):
- [Py3sFormat.h](cpp/Py3sFormat.h): Core structure definitions and endianness validation.
- [Py3sReader.h](cpp/Py3sReader.h) / [Py3sReader.cpp](cpp/Py3sReader.cpp): Streamlined container unpacker.
- [Py3sWriter.h](cpp/Py3sWriter.h) / [Py3sWriter.cpp](cpp/Py3sWriter.cpp): High-speed binary packer.

### 3. TypeScript (`typescript/`)
Web / Three.js codec:
- [py3sCodec.ts](typescript/py3sCodec.ts): Pure TypeScript container unpacker and packer using `DataView` for high-speed browser client execution.

---

## 🎮 Unreal Engine 5 Quickstart

Install the official **PyGrassReal SPZ & PY3S Unreal Plugin**:
1. Drag and drop any `.py3s` file directly into your Unreal Engine **Content Browser**.
2. Drag the imported asset directly into the **Level Viewport**.
3. The actor spawns instantly with:
   - GPU covariance Gaussian Splatting visual layer.
   - Invisible solid UCX collision mesh 1:1 coupled.
   - Characters walk and stand on roofs, decks, and stairs immediately!

---

## 📄 License & Attribution
The `.py3s` format specification, reference codecs, and tools are licensed under the **[MIT License](LICENSE)**.

Developed with ❤️ by **[PyGrassReal AI Team](https://pygrassreal.ai)**.  
*Copyright (c) 2026 PyGrassReal AI. All Rights Reserved.*
