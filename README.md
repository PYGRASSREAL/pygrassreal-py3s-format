<div align="center">

<a href="https://pygrassreal.ai">
  <img src="https://raw.githubusercontent.com/PYGRASSREAL/pygrassreal-py3s-format/main/assets/logo.png" alt="PyGrassReal Logo" width="220" />
</a>

# PyGrassReal 3D Splat (`.py3s`) File Format
### The Foundational Root Asset Format of the PyGrassReal Ecosystem

[![Specification](https://img.shields.io/badge/Specification-v1.0.0-blue.svg)](SPECIFICATION.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Copyright DIP](https://img.shields.io/badge/Copyright%20DIP-No.%20%E0%B8%A71.001520-success.svg)](docs/DIP_Copyright_Certificate_483001.pdf)
[![IANA Media Type](https://img.shields.io/badge/IANA%20MIME-Pending%20Review%20(%231461427)-yellow.svg)](SPECIFICATION.md#iana-media-type-registration)
[![Magic String](https://img.shields.io/badge/Magic-PY3S-orange.svg)](#binary-layout)
[![Engines](https://img.shields.io/badge/Engines-Unreal%205%20%7C%20Unity%20%7C%20Three.js%20%7C%20Python-purple.svg)](#implementations)
[![Lineage](https://img.shields.io/badge/Lineage-PyGrassReal%20Foundational%20Root-gold.svg)](#-foundational-lineage-of-pygrassreal)

**The Official Foundational Single-Container Asset Standard Combining 3D Gaussian Splatting Visuals with 1:1 Physics Collision.**

[📖 Read Specification](SPECIFICATION.md) • [🐍 Python SDK](python/) • [⚡ C++ Implementation](cpp/) • [🌐 TypeScript / Web](typescript/) • [🏛️ Official Platform](https://pygrassreal.ai)

</div>

---

## 🏛️ Foundational Lineage of PyGrassReal
`.py3s` is established as the **Foundational Root Format (Ancestral Standard of the Spatial Computing Ecosystem)** conceived, engineered, and standardized by **PyGrassReal AI**:
- **The Core Parent Standard:** Conceived as the world's first single-container architecture uniting dense 3DGS photorealism with 1:1 solid physics collision.
- **Universal Engine Standard:** Serves as the primary output standard across all PyGrassReal AI generative models (*Hanuman 2.0, Matchanu 2.0, Nilapat 2.0, Sida 1.5, Phralak 2.0*).
- **Evolutionary Root (`.py*s` Series):** Forms the parent foundation for the upcoming generational extensions, including `.py4s` (4D dynamic splats & deformable physics).

---

## 💡 The Spatial Computing Challenge
Traditional 3D Gaussian Splatting technologies generate photorealistic radiance fields, but suffer from a critical flaw: **they are purely visual, massive in file size (often 50-200MB+ per object in raw PLY), and completely lack physical presence**.
- **Ghost Assets:** Without physical geometry, game characters, vehicles, and physics actors pass straight through 3DGS scenes.
- **Workflow Fragmentation:** Developers are forced to generate separate disconnected collision models, leading to desynchronized scaling, broken offsets, and laborious manual alignment in game engines.
- **Bandwidth & Storage Bloat:** Raw PLY/SPLAT files create severe transmission and memory bottlenecks on web viewports, mobile devices, and runtime streaming.

## 🚀 The PyGrassReal Innovation: Native Single-Container Standard
Developed and standardized by **PyGrassReal AI**, the **`.py3s`** format solves this industry-wide bottleneck by encapsulating high-fidelity visual splatting and discrete collision geometry into a unified, ultra-lightweight binary container:

1. **Visual Layer (Ultra-Lightweight):** High-density, precision-quantized 3D Gaussian Splatting payload (*Zstd Compressed 3DGS Payload*). Reduces raw PLY volume by up to **90%** (typically down to **3–5 MB**), enabling real-time streaming and instant memory residency.
2. **Physics Layer:** Precision collision geometry and convex hulls (*Embedded Spatial Collision Mesh*) for 100% solid navigation, raycasting, and character locomotion.
3. **Calibrated Alignment:** Embedded transform matrices (offset, rotation, scale) for instant 1:1 ground-aligned snapping.
4. **Metadata & Preview:** Embedded spatial metadata descriptor and visual asset preview.

> **1-Click Engine Ready:** Drag a single `.py3s` file into Unreal Engine 5, Unity, or Web 3D Viewers — it renders photorealistically with solid collision physics enabled **instantly with zero manual calibration**.

---

## 📐 Binary Layout Overview

A `.py3s` file consists of a fixed **128-byte Header** followed by 4 payload sections:

```text
┌────────────────────────────────────────────────────────┐
│             PY3S File Header (128 Bytes)               │  Offset 0x00
├────────────────────────────────────────────────────────┤
│     Section 1: Visual Layer (Compressed 3DGS Payload)  │  Offset = SpzOffset (default 0x80)
├────────────────────────────────────────────────────────┤
│     Section 2: Physics Layer (Collision Geometry)      │  Offset = ColliderOffset
├────────────────────────────────────────────────────────┤
│     Section 3: Metadata Layer (Spatial Descriptor)     │  Offset = MetadataOffset
├────────────────────────────────────────────────────────┤
│     Section 4: Visual Preview Layer (Optional Image)   │  Offset = ThumbnailOffset
└────────────────────────────────────────────────────────┘
```

### 128-Byte Fixed Header Layout

| Field | Type | Size | Description |
|---|---|---|---|
| `Magic` | `char[4]` | 4 B | Always `"PY3S"` (`0x50 0x59 0x33 0x53`) |
| `VersionMajor` | `uint16` | 2 B | Major version (`1`) |
| `VersionMinor` | `uint16` | 2 B | Minor version (`0`) |
| `Flags` | `uint32` | 4 B | Payload encoding and compression flags |
| `Reserved1` | `uint32` | 4 B | Reserved for future alignment |
| `SpzOffset` | `uint64` | 8 B | Byte offset to Section 1 (Visual 3DGS Payload) |
| `SpzSize` | `uint64` | 8 B | Visual 3DGS Payload size in bytes |
| `ColliderOffset` | `uint64` | 8 B | Byte offset to Section 2 (Collision Geometry) |
| `ColliderSize` | `uint64` | 8 B | Collision geometry size in bytes |
| `MetadataOffset` | `uint64` | 8 B | Byte offset to Section 3 (Spatial Metadata JSON) |
| `MetadataSize` | `uint64` | 8 B | Metadata size in bytes |
| `ThumbnailOffset`| `uint64` | 8 B | Byte offset to Section 4 (Visual Preview Image) |
| `ThumbnailSize` | `uint64` | 8 B | Visual Preview size in bytes |
| `Reserved` | `uint8[48]` | 48 B | Zero-padded for future extensions |

For comprehensive technical specifications, read [SPECIFICATION.md](SPECIFICATION.md).

---

## 🛠️ Official Implementations

This repository includes open-source reference implementations across multiple platforms:

### 1. Python SDK (`python/`)
Zero-dependency Python implementation for packing, unpacking, and CLI batch operations:

```bash
# Unpack a .py3s container into component layers
python python/py3s_codec.py unpack model.py3s -o ./output/

# Pack visual splat and collision geometry into a single .py3s container
python python/py3s_codec.py pack --splat visual.bin --collider collision.bin --metadata metadata.json -o model.py3s

# Inspect file contents and metadata
python python/py3s_codec.py info model.py3s
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

Install the official **PyGrassReal Unreal Engine Plugin**:
1. Drag and drop any `.py3s` file directly into your Unreal Engine **Content Browser**.
2. Drag the imported asset directly into the **Level Viewport**.
3. The actor spawns instantly with:
   - Real-time GPU Gaussian Splatting visual layer.
   - Invisible solid collision mesh coupled 1:1 with sub-millimeter precision.
   - Characters walk and stand on roofs, decks, and stairs immediately!

---

## 🏛️ Intellectual Property & Standardization Status

The `.py3s` file format specification and software implementation are officially recorded by the Department of Intellectual Property (DIP) and undergoing global standardization:

| Authority / Standard Body | Identifier / Record | Status | Document |
|---|---|---|---|
| **Department of Intellectual Property (DIP)** | **Record No. ว1.001520** (App No. 483001) | **Officially Approved & Recorded** | [📄 View Certificate PDF](docs/DIP_Copyright_Certificate_483001.pdf) |
| **Internet Assigned Numbers Authority (IANA)** | **MIME:** `model/vnd.pygrassreal.py3s` | **Submitted / Under Review** (`Ticket #1461427`) | [📖 Registration Spec](SPECIFICATION.md#iana-media-type-registration) |
| **Creator & Rights Holder** | **PyGrassReal AI** | **Exclusive Proprietary & Commercial Rights** | [🌐 pygrassreal.ai](https://pygrassreal.ai) |

<div align="center">
  <br />
  <a href="docs/DIP_Copyright_Certificate_483001.pdf">
    <img src="docs/DIP_Copyright_Certificate_483001.png" alt="Official DIP Copyright Certificate (ว1.001520)" width="440" style="border: 1px solid #444; border-radius: 6px; box-shadow: 0 4px 12px rgba(0,0,0,0.3);" />
  </a>
  <p><em>Official Department of Intellectual Property (DIP) Certificate of Copyright Recordation (No. ว1.001520 / Application No. 483001)</em></p>
  <p><a href="docs/DIP_Copyright_Certificate_483001.pdf">📥 Download Official Certificate (PDF)</a></p>
</div>

---

## 📜 License & Attribution
The `.py3s` format specification, reference codecs, and tools are licensed under the **[MIT License](LICENSE)**.

Developed with ❤️ by **[PyGrassReal AI Team](https://pygrassreal.ai)**.  
*Copyright (c) 2026 PyGrassReal AI. All Rights Reserved.*

