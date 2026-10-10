# IANA MIME Media Type Registration Template

This document contains the ready-to-submit application template for registering the `.py3s` media type with **IANA (Internet Assigned Numbers Authority)** under the Vendor Tree (`vnd.`).

Submit URL: https://www.iana.org/form/media-types

---

```text
Type name: model

Subtype name: vnd.pygrassreal.py3s

Required parameters: N/A

Optional parameters: N/A

Encoding considerations: binary

Security considerations:
The .py3s format is a passive binary container encapsulating 3D Gaussian Splatting data, 3D polygonal mesh geometry, JSON metadata, and optional raster thumbnails. It contains no executable scripts, macros, or bytecode. Decoders should enforce bounds checking on offsets and sizes specified in the 128-byte fixed header.

Interoperability considerations:
Designed for cross-platform 3D visualization, virtual reality, architectural modeling, and game engines (Unreal Engine 5, WebGL/Three.js, Unity). Endianness is explicitly defined as Little-Endian.

Published specification:
https://github.com/PyGrassReal/pygrassreal-py3s-format/blob/main/SPECIFICATION.md

Applications that use this media type:
PyGrassReal AI Studio, Unreal Engine 5 PyGrassReal Plugin, Web Three.js PyGrassReal Viewers, and 3D Gaussian Splatting conversion pipelines.

Fragment identifier considerations: N/A

Additional information:
 Magic number(s): 0x50 0x59 0x33 0x53 ("PY3S") at offset 0
 File extension(s): .py3s
 Macintosh file type code(s): PY3S

Person & email to address for further information:
Name: PyGrassReal AI Team
Email: admin@pygrassreal.ai
Organization: PyGrassReal AI (https://pygrassreal.ai)

Intended usage: COMMON

Restrictions on usage: None

Author: PyGrassReal AI Team

Change controller: PyGrassReal AI
```
