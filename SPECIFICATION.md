# 📦 ข้อกำหนดโครงสร้างไฟล์ PyGrassReal 3D Splat (`.py3s`)
### ฟอร์แมตต้นตระกูลของ PyGrassReal Spatial Ecosystem (Foundational Root Format)

> **ลิขสิทธิ์**: Copyright (c) 2026 **PyGrassReal AI** (https://pygrassreal.ai). All Rights Reserved.  
> **แบรนด์/ผู้พัฒนา**: **PyGrassReal**  
> **สถานะ**: **ฟอร์แมตต้นตระกูล (Foundational Root Format)** ของระบบนิเวศ PyGrassReal Spatial Series  
> **ชื่อฟอร์แมต**: PyGrassReal 3D Splat Single Container (`.py3s`)  
> **MIME Media Type**: `model/vnd.pygrassreal.py3s`  
> **เวอร์ชันสเปก**: `1.0.0`  
> **Magic String**: `"PY3S"` (`0x50 0x59 0x33 0x53`)  
> **Endianness**: Little-Endian (LE)  
> **ขนาด Header**: 128 Bytes  

---

## 🏛️ ความเป็นมาและสายธารต้นตระกูล (Origin & Foundational Lineage)
`.py3s` ได้รับการสถาปนาขึ้นโดย **PyGrassReal AI** ให้เป็น **"ฟอร์แมตต้นตระกูล (Ancestral / Foundational Root Standard)"** ของระบบนิเวศ Spatial Computing ทั้งหมด:
1. **เสาหลักต้นแบบ (The Root Specification):** เป็นรากฐานข้อกำหนดมาตรฐานชุดแรกของโลกที่คิดค้นขึ้นเพื่อผสานภาพเรนเดอร์เสมือนจริงของ 3D Gaussian Splatting เข้ากับเรขาคณิตการชนทางฟิสิกส์ 1:1 ในคอนเทนเนอร์เดียว
2. **ต้นทางของทุกโมเดลในเครือ PyGrassReal:** โมเดลปัญญาประดิษฐ์และเอนจิ้นทั้งหมดในเครือข่าย (อาทิ Hanuman 2.0, Matchanu 2.0, Nilapat 2.0, Sida 1.5, Phralak 2.0) ยึดถือ `.py3s` เป็นฟอร์แมตผลลัพธ์มาตรฐานสูงสุด
3. **ต้นแบบสู่เจเนอเรชันถัดไป (`.py*s` Series):**
   - **`.py3s` (Foundational Standard):** 3D Gaussian Splatting + 1:1 Static Collision Mesh
   - **`.py4s` (Next-Gen Dynamic Evolution):** 4D Dynamic Splatting + Time-series Tracks + Deformable Physics Colliders

---

## 1. วัตถุประสงค์ (Purpose)
`.py3s` เป็น Single-Container Asset Format มาตรฐานทางการของ **PyGrassReal AI** ที่ออกแบบมาเพื่อรวม:
1. **Visual Layer**: ชุดข้อมูลแสดงผล 3D Gaussian Splatting (3DGS) บีบอัดความหนาแน่นสูงระดับความแม่นยำสูง (*PyGrassReal Compressed 3DGS Payload*)
2. **Physics Layer**: โครงสร้างเรขาคณิตฟิสิกส์ 1:1 สำหรับการคำนวณการชนและการเคลื่อนที่ (*Precision Physics & Spatial Collision Geometry*)
3. **Metadata Layer**: ชุดข้อมูลนิยามพิกัด ขนาด องศา และจุดยึดพื้นผิว (*Spatial Alignment & Engine Transform Descriptor*)
4. **Thumbnail Layer** *(Optional)*: ชุดข้อมูลภาพตัวอย่างสินทรัพย์ 2 มิติสำหรับการแสดงผล (*Embedded Visual Asset Preview Chunk*)

รวมจบสมบูรณ์ในคอนเทนเนอร์เดียว ไม่ต้องแยกจัดเก็บหลายไฟล์ ไม่ต้องตั้งค่าจับคู่ด้วยตนเอง สามารถนำเข้าสู่เอนจิ้นเกม (เช่น Unreal Engine 5) หรือ Web 3D Viewer เพื่อแสดงผลภาพเสมือนจริงพร้อมรองรับการชนทางฟิสิกส์ 1:1 ได้ทันที

---

## 2. โครงสร้างหน่วยความจำ (Binary Layout)

```
┌────────────────────────────────────────────────────────┐
│             PY3S File Header (128 Bytes)               │  Offset 0x00
├────────────────────────────────────────────────────────┤
│     Section 1: Visual Layer (Compressed 3DGS Payload)  │  Offset = SpzOffset (ปกติ 0x80)
├────────────────────────────────────────────────────────┤
│     Section 2: Physics Layer (Collision Geometry)      │  Offset = ColliderOffset
├────────────────────────────────────────────────────────┤
│     Section 3: Metadata Layer (Spatial Descriptor)     │  Offset = MetadataOffset
├────────────────────────────────────────────────────────┤
│     Section 4: Visual Preview Layer (Optional Image)   │  Offset = ThumbnailOffset
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
| `0x0C` | 4 | `uint32` | `Flags` | บิตแฟล็กการเข้ารหัสและการบีบอัดข้อมูล |
| `0x10` | 8 | `uint64` | `SpzOffset` | Byte offset จุดเริ่มต้นของ Visual 3DGS Payload |
| `0x18` | 8 | `uint64` | `SpzSize` | ขนาดของ Visual 3DGS Payload (bytes) |
| `0x20` | 8 | `uint64` | `ColliderOffset` | Byte offset จุดเริ่มต้นของ Collision Geometry |
| `0x28` | 8 | `uint64` | `ColliderSize` | ขนาดของ Collision Geometry (bytes) |
| `0x30` | 8 | `uint64` | `MetadataOffset` | Byte offset จุดเริ่มต้นของ Spatial Metadata |
| `0x38` | 8 | `uint64` | `MetadataSize` | ขนาดของ Spatial Metadata JSON (bytes) |
| `0x40` | 8 | `uint64` | `ThumbnailOffset` | Byte offset ของ Visual Preview Image (0 ถ้าไม่มี) |
| `0x48` | 8 | `uint64` | `ThumbnailSize` | ขนาดของ Visual Preview Image (0 ถ้าไม่มี) |
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
