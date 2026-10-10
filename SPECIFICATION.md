# 📦 ข้อกำหนดโครงสร้างไฟล์ PyGrassReal 3D Splat (`.py3s`)

> **ลิขสิทธิ์**: Copyright (c) 2026 **PyGrassReal AI** (https://pygrassreal.ai). All Rights Reserved.  
> **แบรนด์/ผู้พัฒนา**: **PyGrassReal**  
> **ชื่อฟอร์แมต**: PyGrassReal 3D Splat Single Container (`.py3s`)  
> **MIME Media Type**: `model/vnd.pygrassreal.py3s`  
> **เวอร์ชันสเปก**: `1.0.0`  
> **Magic String**: `"PY3S"` (`0x50 0x59 0x33 0x53`)  
> **Endianness**: Little-Endian (LE)  
> **ขนาด Header**: 128 Bytes  

---

## 1. วัตถุประสงค์ (Purpose)
`.py3s` เป็น Single-Container Asset Format ที่ออกแบบมาเพื่อรวม:
1. **Visual Layer**: 3D Gaussian Splatting (`.spz`)
2. **Physics Layer**: Low-poly Collision Mesh (`.glb` หรือ `.fbx` ที่มี UCX Convex Hulls)
3. **Metadata Layer**: JSON เก็บข้อมูล Alignment, Scale, Offset, Bounds, และพารามิเตอร์การเรนเดอร์
4. **Thumbnail Layer** *(Optional)*: รูปพรีวิว WebP/PNG สำหรับ Content Browser และ Store

ไฟล์เดียวจบ ไม่ต้องแยกไฟล์ ไม่ต้องจับคู่ด้วยมือ ลากลง Unreal Engine 5 หรือ Web 3D Viewer ใช้งานได้ทันที 100%

---

## 2. โครงสร้างหน่วยความจำ (Binary Layout)

```
┌────────────────────────────────────────────────────────┐
│             PY3S File Header (128 Bytes)               │  Offset 0x00
├────────────────────────────────────────────────────────┤
│          Section 1: SPZ Payload (Visual 3DGS)          │  Offset = SpzOffset (ปกติ 0x80)
├────────────────────────────────────────────────────────┤
│          Section 2: Collision Mesh (Physics)           │  Offset = ColliderOffset
├────────────────────────────────────────────────────────┤
│          Section 3: Metadata (UTF-8 JSON)              │  Offset = MetadataOffset
├────────────────────────────────────────────────────────┤
│          Section 4: Thumbnail (WebP/PNG) [ถ้ามี]       │  Offset = ThumbnailOffset
└────────────────────────────────────────────────────────┘
```

---

## 3. ตารางโครงสร้าง Header (128 Bytes)

| Offset (Hex) | ขนาด (Bytes) | ชนิดข้อมูล | ชื่อฟิลด์ | คำอธิบาย |
|---|---|---|---|---|
| `0x00` | 4 | `char[4]` | `Magic` | ต้องเป็น `"PY3S"` (`0x50 0x59 0x33 0x53`) |
| `0x04` | 2 | `uint16` | `VersionMajor` | เวอร์ชันหลัก (ปัจจุบัน = 1) |
| `0x06` | 2 | `uint16` | `VersionMinor` | เวอร์ชันย่อย (ปัจจุบัน = 0) |
| `0x08` | 4 | `uint32` | `SectionCount` | จำนวน sections (ปกติ = 3 หรือ 4) |
| `0x0C` | 4 | `uint32` | `Flags` | บิตแฟล็ก (0x1=ZSTD, 0x2=GLB, 0x4=FBX) |
| `0x10` | 8 | `uint64` | `SpzOffset` | Byte offset จุดเริ่มต้นของ SPZ section |
| `0x18` | 8 | `uint64` | `SpzSize` | ขนาดของ SPZ payload (bytes) |
| `0x20` | 8 | `uint64` | `ColliderOffset` | Byte offset จุดเริ่มต้นของ Collider section |
| `0x28` | 8 | `uint64` | `ColliderSize` | ขนาดของ Collider mesh (bytes) |
| `0x30` | 8 | `uint64` | `MetadataOffset` | Byte offset จุดเริ่มต้นของ Metadata section |
| `0x38` | 8 | `uint64` | `MetadataSize` | ขนาดของ Metadata JSON (bytes) |
| `0x40` | 8 | `uint64` | `ThumbnailOffset` | Byte offset ของ Thumbnail (0 ถ้าไม่มี) |
| `0x48` | 8 | `uint64` | `ThumbnailSize` | ขนาดของ Thumbnail (0 ถ้าไม่มี) |
| `0x50` | 48 | `uint8[48]` | `Reserved` | สงวนไว้สำหรับส่วนขยายอนาคต (zero padding) |

---

## 4. โครงสร้าง JSON Metadata (Section 3)

```json
{
  "format": "py3s",
  "version": "1.0.0",
  "generator": "PyGrassReal-Parametric",
  "created": "2026-10-10T14:30:00.000Z",
  "asset": {
    "name": "matchanu1.5-3dgs-1791204338620",
    "pointCount": 485231,
    "bounds": {
      "min": [-2.5, -0.1, -3.0],
      "max": [2.5, 5.2, 3.0]
    }
  },
  "collision": {
    "format": "glb",
    "vertexCount": 1284,
    "faceCount": 2456,
    "type": "ConvexHull",
    "enablePhysicsBounce": true
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
```

---

## 5. การต่อยอดในอนาคต (Roadmap)
- **`.py3s`**: 3D Splatting + 3D Physics Mesh (Static assets)
- **`.py4s`**: 4D Dynamic Splatting + Animated Deformable Collision + Time-series Tracks
