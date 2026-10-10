/**
 * PyGrassReal 3D Splat (.py3s) Web & TypeScript Codec
 * Unified container for 3D Gaussian Splatting (3DGS) Visuals + Precision Physics Collision Geometry + Spatial Metadata
 * Official Reference Implementation by PyGrassReal AI (https://pygrassreal.ai)
 */

export const PY3S_HEADER_MAGIC = 'PY3S';
export const PY3S_HEADER_SIZE = 128;
export const PY3S_VERSION_MAJOR = 1;
export const PY3S_VERSION_MINOR = 0;

export const PY3S_FLAG_NONE = 0x0;
export const PY3S_FLAG_SPZ_ZSTD = 0x1;
export const PY3S_FLAG_COLLIDER_GLB = 0x2;
export const PY3S_FLAG_COLLIDER_FBX = 0x4;

export interface Py3sAlignment {
  rotation: [number, number, number]; // [Pitch, Yaw, Roll]
  offset: [number, number, number];   // [X, Y, Z]
  scale: [number, number, number];    // [X, Y, Z]
}

export interface Py3sMetadata {
  format: 'py3s';
  version: string;
  generator?: string;
  created?: string;
  asset: {
    name: string;
    pointCount?: number;
    bounds?: {
      min: [number, number, number];
      max: [number, number, number];
    };
  };
  collision?: {
    format: 'glb' | 'fbx';
    vertexCount?: number;
    faceCount?: number;
    type?: string;
    enablePhysicsBounce?: boolean;
  };
  alignment?: Py3sAlignment;
  rendering?: {
    gamma?: number;
    opacityCutoff?: number;
    splatScale?: number;
  };
  [key: string]: unknown;
}

export interface Py3sContainerData {
  spzData: Uint8Array;
  colliderData?: Uint8Array;
  metadata: Py3sMetadata;
  thumbnailData?: Uint8Array;
}

export class Py3sCodec {
  /**
   * Packs SPZ, Collider, Metadata, and optional Thumbnail into a single .py3s binary buffer.
   */
  public static pack(data: Py3sContainerData): Uint8Array {
    const textEncoder = new TextEncoder();
    const metaBytes = textEncoder.encode(JSON.stringify(data.metadata));

    const spzBytes = data.spzData;
    const colliderBytes = data.colliderData ?? new Uint8Array(0);
    const thumbBytes = data.thumbnailData ?? new Uint8Array(0);

    let currentOffset = PY3S_HEADER_SIZE;

    const spzOffset = BigInt(currentOffset);
    const spzSize = BigInt(spzBytes.byteLength);
    currentOffset += spzBytes.byteLength;

    const colOffset = BigInt(currentOffset);
    const colSize = BigInt(colliderBytes.byteLength);
    currentOffset += colliderBytes.byteLength;

    const metaOffset = BigInt(currentOffset);
    const metaSize = BigInt(metaBytes.byteLength);
    currentOffset += metaBytes.byteLength;

    let thumbOffset = BigInt(0);
    let thumbSize = BigInt(0);
    let sectionCount = 3;

    if (thumbBytes.byteLength > 0) {
      thumbOffset = BigInt(currentOffset);
      thumbSize = BigInt(thumbBytes.byteLength);
      currentOffset += thumbBytes.byteLength;
      sectionCount = 4;
    }

    const totalSize = currentOffset;
    const output = new Uint8Array(totalSize);
    const view = new DataView(output.buffer, output.byteOffset, output.byteLength);

    // 1. Magic "PY3S"
    output[0] = 0x50; // 'P'
    output[1] = 0x59; // 'Y'
    output[2] = 0x33; // '3'
    output[3] = 0x53; // 'S'

    // 2. Version
    view.setUint16(4, PY3S_VERSION_MAJOR, true);
    view.setUint16(6, PY3S_VERSION_MINOR, true);

    // 3. Section count & flags
    view.setUint32(8, sectionCount, true);
    const isFbx = data.metadata.collision?.format?.toLowerCase() === 'fbx';
    const flags = PY3S_FLAG_SPZ_ZSTD | (isFbx ? PY3S_FLAG_COLLIDER_FBX : PY3S_FLAG_COLLIDER_GLB);
    view.setUint32(12, flags, true);

    // 4. Offsets and sizes (uint64 little endian)
    view.setBigUint64(16, spzOffset, true);
    view.setBigUint64(24, spzSize, true);
    view.setBigUint64(32, colOffset, true);
    view.setBigUint64(40, colSize, true);
    view.setBigUint64(48, metaOffset, true);
    view.setBigUint64(56, metaSize, true);
    view.setBigUint64(64, thumbOffset, true);
    view.setBigUint64(72, thumbSize, true);

    // 5. Reserved bytes (0x50 to 0x7F = 48 bytes) are already 0.

    // 6. Copy payloads
    if (spzBytes.byteLength > 0) {
      output.set(spzBytes, Number(spzOffset));
    }
    if (colliderBytes.byteLength > 0) {
      output.set(colliderBytes, Number(colOffset));
    }
    if (metaBytes.byteLength > 0) {
      output.set(metaBytes, Number(metaOffset));
    }
    if (thumbBytes.byteLength > 0) {
      output.set(thumbBytes, Number(thumbOffset));
    }

    return output;
  }

  /**
   * Unpacks a .py3s binary buffer into constituent components.
   */
  public static unpack(buffer: ArrayBuffer | Uint8Array): Py3sContainerData {
    const bytes = buffer instanceof Uint8Array ? buffer : new Uint8Array(buffer);
    if (bytes.byteLength < PY3S_HEADER_SIZE) {
      throw new Error(`Invalid PY3S buffer: size ${bytes.byteLength} < ${PY3S_HEADER_SIZE}`);
    }

    const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);

    // Validate Magic
    if (
      bytes[0] !== 0x50 || // 'P'
      bytes[1] !== 0x59 || // 'Y'
      bytes[2] !== 0x33 || // '3'
      bytes[3] !== 0x53    // 'S'
    ) {
      throw new Error('Not a valid PY3S container (header magic mismatch)');
    }

    const versionMajor = view.getUint16(4, true);
    if (versionMajor > PY3S_VERSION_MAJOR) {
      throw new Error(`Unsupported PY3S version: ${versionMajor} > ${PY3S_VERSION_MAJOR}`);
    }

    const spzOffset = Number(view.getBigUint64(16, true));
    const spzSize = Number(view.getBigUint64(24, true));
    const colOffset = Number(view.getBigUint64(32, true));
    const colSize = Number(view.getBigUint64(40, true));
    const metaOffset = Number(view.getBigUint64(48, true));
    const metaSize = Number(view.getBigUint64(56, true));
    const thumbOffset = Number(view.getBigUint64(64, true));
    const thumbSize = Number(view.getBigUint64(72, true));

    // Slice SPZ payload
    const spzData = bytes.slice(spzOffset, spzOffset + spzSize);

    // Slice Collider payload
    const colliderData = colSize > 0 ? bytes.slice(colOffset, colOffset + colSize) : undefined;

    // Decode Metadata
    let metadata: Py3sMetadata;
    if (metaSize > 0) {
      const metaBytes = bytes.slice(metaOffset, metaOffset + metaSize);
      const textDecoder = new TextDecoder('utf-8');
      metadata = JSON.parse(textDecoder.decode(metaBytes)) as Py3sMetadata;
    } else {
      metadata = {
        format: 'py3s',
        version: '1.0.0',
        asset: { name: 'unnamed' },
      };
    }

    // Slice Thumbnail
    const thumbnailData = thumbSize > 0 && thumbOffset > 0 ? bytes.slice(thumbOffset, thumbOffset + thumbSize) : undefined;

    return {
      spzData,
      colliderData,
      metadata,
      thumbnailData,
    };
  }
}
