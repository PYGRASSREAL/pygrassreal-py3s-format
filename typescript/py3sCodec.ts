/**
 * PyGrassReal 3D Splat (.py3s) Unified v2.0 Web & TypeScript Codec
 * Single-container binary format combining:
 *   - Section 1: 3D Gaussian Splatting payload (.spz)
 *   - Section 2: 1:1 Physics collision geometry (.glb / .fbx)
 *   - Section 3: Spatial, simulation, Print 3D & AI Copilot metadata (UTF-8 JSON)
 *   - Section 4: Optional 2D preview thumbnail (.webp / .png)
 *   - Section 5: Optional Print 3D manufacturing package (.3mf ZIP/OPC)
 * Supports v1.0 / v1.1 backward compatibility and v2.0 CRC-32 integrity verification.
 */

export const PY3S_HEADER_MAGIC = 'PY3S';
export const PY3S_HEADER_SIZE = 128;
export const PY3S_VERSION_MAJOR = 2;
export const PY3S_VERSION_MINOR = 0;

export const PY3S_FLAG_NONE = 0x0;
export const PY3S_FLAG_SPZ_ZSTD = 0x1;
export const PY3S_FLAG_COLLIDER_GLB = 0x2;
export const PY3S_FLAG_COLLIDER_FBX = 0x4;
export const PY3S_FLAG_PRINT_3MF = 0x8;
export const PY3S_FLAG_SIM_STRESS = 0x10;
export const PY3S_FLAG_SIM_VORONOI_CRACK = 0x20;
export const PY3S_FLAG_SIM_MEGAS_THERMAL = 0x40;
export const PY3S_FLAG_SIM_PLANT_WILTING = 0x80;
export const PY3S_FLAG_SIM_DIFFWIND = 0x100;
export const PY3S_FLAG_SIM_PHYSSKIN = 0x200;
export const PY3S_FLAG_SIM_MAGNETIC_MPM = 0x400;
export const PY3S_FLAG_SIM_ENLIVENING_GS = 0x800;
export const PY3S_FLAG_MFG_PRINT3D_READY = 0x1000;
export const PY3S_FLAG_AI_SYSTEM_PROMPT = 0x2000;
export const PY3S_FLAG_STATE_DEHYDRATED_SEED = 0x4000;
export const PY3S_FLAG_AUTO_HYDRATE_ON_MOUNT = 0x8000;
export const PY3S_FLAG_HANUMAN_PARAMETRIC_AI = 0x10000;
export const PY3S_FLAG_INTEGRITY_CRC32 = 0x20000;
export const PY3S_FLAG_COLLIDER_CONVEX = 0x40000;
export const PY3S_FLAG_SECURITY_HMAC = 0x80000;

export const PY3S_MAX_METADATA_BYTES = 8 * 1024 * 1024;
export const PY3S_MAX_METADATA_DEPTH = 24;
export const PY3S_MAX_ZIP_ARCHIVE_BYTES = 128 * 1024 * 1024;
export const PY3S_MAX_ZIP_ENTRIES = 256;
export const PY3S_MAX_ZIP_UNCOMPRESSED_BYTES = 256 * 1024 * 1024;
export const PY3S_MAX_ZIP_RATIO = 100;

const CRC32_CHECKSUM_FIELD_OFFSET = 0x60;
const CRC32_CHECKSUM_FIELD_LENGTH = 8; // 0x60..0x63 ContainerCrc32, 0x64..0x67 Print3mfCrc32
const HMAC_TAG_OFFSET = 0x68;
const HMAC_TAG_LENGTH = 24; // 0x68..0x7F (192-bit truncated HMAC-SHA256)
const DANGEROUS_OBJECT_KEYS = new Set(['__proto__', 'constructor', 'prototype']);

const CRC32_TABLE = (() => {
  const table = new Uint32Array(256);
  for (let i = 0; i < 256; i++) {
    let crc = i;
    for (let bit = 0; bit < 8; bit++) {
      crc = (crc & 1) !== 0 ? (0xedb88320 ^ (crc >>> 1)) : (crc >>> 1);
    }
    table[i] = crc >>> 0;
  }
  return table;
})();

function updateCrc32(crc: number, bytes: Uint8Array, start = 0, end = bytes.byteLength): number {
  let current = crc;
  for (let i = start; i < end; i++) {
    current = CRC32_TABLE[(current ^ bytes[i]) & 0xff] ^ (current >>> 8);
  }
  return current;
}

/** Computes IEEE 802.3 unsigned 32-bit CRC-32 matching Python zlib.crc32. */
export function computePy3sCrc32(bytes: Uint8Array): number {
  return (updateCrc32(0xffffffff, bytes) ^ 0xffffffff) >>> 0;
}

function computeContainerCrc32(bytes: Uint8Array): number {
  let crc = updateCrc32(0xffffffff, bytes, 0, CRC32_CHECKSUM_FIELD_OFFSET);
  for (let i = 0; i < CRC32_CHECKSUM_FIELD_LENGTH; i++) {
    crc = CRC32_TABLE[crc & 0xff] ^ (crc >>> 8);
  }
  crc = updateCrc32(crc, bytes, CRC32_CHECKSUM_FIELD_OFFSET + CRC32_CHECKSUM_FIELD_LENGTH, bytes.byteLength);
  return (crc ^ 0xffffffff) >>> 0;
}

function sanitizeMetadataValue(value: unknown, depth = 0): unknown {
  if (depth > PY3S_MAX_METADATA_DEPTH) {
    throw new Error('PY3S metadata exceeds maximum nesting depth');
  }
  if (value === null || typeof value !== 'object') {
    return value;
  }
  if (Array.isArray(value)) {
    return value.map((item) => sanitizeMetadataValue(item, depth + 1));
  }
  const source = value as Record<string, unknown>;
  const clean: Record<string, unknown> = {};
  for (const key of Object.keys(source)) {
    if (DANGEROUS_OBJECT_KEYS.has(key)) continue;
    Object.defineProperty(clean, key, {
      value: sanitizeMetadataValue(source[key], depth + 1),
      enumerable: true,
      writable: true,
      configurable: true,
    });
  }
  return clean;
}

function normalizeSecretKeyBytes(secretKey: string | Uint8Array): Uint8Array {
  const keyBytes = typeof secretKey === 'string' ? new TextEncoder().encode(secretKey) : secretKey;
  if (!keyBytes.byteLength) {
    throw new Error('PY3S HMAC secret key cannot be empty');
  }
  return new Uint8Array(keyBytes);
}

async function computeHmacTagBytes(containerBytes: Uint8Array, secretKey: string | Uint8Array): Promise<Uint8Array> {
  const subtle = globalThis.crypto?.subtle;
  if (!subtle) {
    throw new Error('Web Crypto subtle API is unavailable for PY3S HMAC verification');
  }
  const keyBytes = normalizeSecretKeyBytes(secretKey);
  const keyBuffer = new Uint8Array(keyBytes).buffer;
  const cryptoKey = await subtle.importKey(
    'raw',
    keyBuffer,
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign'],
  );
  // Zero 0x60..0x7F (CRC32 + HMAC tag slots) while hashing so CRC32 updates never invalidate the HMAC.
  const signingInput = new Uint8Array(containerBytes);
  signingInput.fill(0, CRC32_CHECKSUM_FIELD_OFFSET, PY3S_HEADER_SIZE);
  const sigBuffer = await subtle.sign('HMAC', cryptoKey, signingInput.buffer);
  return new Uint8Array(sigBuffer, 0, HMAC_TAG_LENGTH);
}

function constantTimeEqual(a: Uint8Array, b: Uint8Array): boolean {
  if (a.byteLength !== b.byteLength) return false;
  let diff = 0;
  for (let i = 0; i < a.byteLength; i++) {
    diff |= a[i] ^ b[i];
  }
  return diff === 0;
}

/**
 * Inspects a ZIP/OPC archive's Central Directory without decompressing it,
 * blocking Zip Bombs, excessive entry counts, and Zip Slip traversal paths.
 */
export function validateSafeZipBytes(bytes: Uint8Array): void {
  if (bytes.byteLength < 22 || bytes.byteLength > PY3S_MAX_ZIP_ARCHIVE_BYTES) {
    throw new Error(`Invalid or oversized Print 3D ZIP archive (${bytes.byteLength} bytes)`);
  }
  if (bytes[0] !== 0x50 || bytes[1] !== 0x4b || bytes[2] !== 0x03 || bytes[3] !== 0x04) {
    throw new Error('Print 3D payload is not a valid ZIP archive');
  }

  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const searchFloor = Math.max(0, bytes.byteLength - 22 - 65535);
  let eocdOffset = -1;
  for (let i = bytes.byteLength - 22; i >= searchFloor; i--) {
    if (view.getUint32(i, true) === 0x06054b50) {
      eocdOffset = i;
      break;
    }
  }
  if (eocdOffset < 0) {
    throw new Error('Print 3D ZIP missing End of Central Directory record');
  }

  const totalEntries = view.getUint16(eocdOffset + 10, true);
  const cdSize = view.getUint32(eocdOffset + 12, true);
  const cdOffset = view.getUint32(eocdOffset + 16, true);
  if (totalEntries === 0xffff || cdOffset === 0xffffffff || cdSize === 0xffffffff) {
    throw new Error('ZIP64 Print 3D archives are rejected for security bounds enforcement');
  }
  if (totalEntries > PY3S_MAX_ZIP_ENTRIES) {
    throw new Error(`Print 3D archive exceeds maximum entry limit (${totalEntries} > ${PY3S_MAX_ZIP_ENTRIES})`);
  }
  if (cdOffset > bytes.byteLength || cdSize > bytes.byteLength - cdOffset) {
    throw new Error('Print 3D ZIP Central Directory exceeds buffer bounds');
  }

  const textDecoder = new TextDecoder('utf-8');
  let cursor = cdOffset;
  let totalUncompressed = 0;
  for (let idx = 0; idx < totalEntries; idx++) {
    if (cursor + 46 > cdOffset + cdSize || view.getUint32(cursor, true) !== 0x02014b50) {
      throw new Error('Corrupted Print 3D ZIP Central Directory entry');
    }
    const compressedSize = view.getUint32(cursor + 20, true);
    const uncompressedSize = view.getUint32(cursor + 24, true);
    const nameLen = view.getUint16(cursor + 28, true);
    const extraLen = view.getUint16(cursor + 30, true);
    const commentLen = view.getUint16(cursor + 32, true);
    const entrySize = 46 + nameLen + extraLen + commentLen;
    if (cursor + entrySize > cdOffset + cdSize) {
      throw new Error('Truncated Print 3D ZIP entry header');
    }

    const entryName = textDecoder.decode(bytes.subarray(cursor + 46, cursor + 46 + nameLen));
    if (
      !entryName ||
      entryName.includes('\0') ||
      entryName.startsWith('/') ||
      entryName.startsWith('\\') ||
      /^[A-Za-z]:/.test(entryName) ||
      /(?:^|[\\/])\.\.(?:$|[\\/])/.test(entryName)
    ) {
      throw new Error(`Rejected unsafe path inside Print 3D ZIP: ${entryName}`);
    }

    if (
      uncompressedSize > 10 * 1024 * 1024 &&
      uncompressedSize / Math.max(1, compressedSize) > PY3S_MAX_ZIP_RATIO
    ) {
      throw new Error(`Rejected suspected Zip Bomb entry inside Print 3D archive: ${entryName}`);
    }
    totalUncompressed += uncompressedSize;
    if (totalUncompressed > PY3S_MAX_ZIP_UNCOMPRESSED_BYTES) {
      throw new Error('Print 3D archive exceeds maximum safe uncompressed byte limit');
    }
    cursor += entrySize;
  }
}

export function isPy3sBuffer(buf: ArrayBuffer | ArrayBufferView | null | undefined): boolean {
  if (!buf) return false;
  const byteLength = 'byteLength' in buf ? buf.byteLength : 0;
  if (byteLength < 4) return false;
  const uint8 = 'buffer' in buf
    ? new Uint8Array(buf.buffer, buf.byteOffset, Math.min(4, buf.byteLength))
    : new Uint8Array((buf as ArrayBuffer).slice(0, 4));
  return uint8[0] === 0x50 && uint8[1] === 0x59 && uint8[2] === 0x33 && uint8[3] === 0x53; // 'PY3S'
}

export interface Py3sPhysSkinData {
  latentVector?: number[];
  anchorCount?: number;
  continuousFieldResolution?: [number, number, number];
  jacobianBounds?: { min: number; max: number };
  rigFree?: boolean;
}

export interface Py3sMagneticMpmData {
  magneticSusceptibilityChi?: number;
  saturationMagnetizationMs?: number;
  dipoleInteractionRadius?: number;
  ferrofluidViscosity?: number;
  surfaceTensionGamma?: number;
  rosensweigSpikeThreshold?: number;
}

export interface Py3sAlignment {
  origin?: string;
  scaleRatio?: number;
  rotation?: [number, number, number]; // [Pitch, Yaw, Roll]
  offset?: [number, number, number];   // [X, Y, Z]
  scale?: [number, number, number];    // [X, Y, Z]
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
    colliderFlipped?: boolean;
    pipelineVersion?: string;
  };
  physSkin?: Py3sPhysSkinData;
  magneticMpm?: Py3sMagneticMpmData;
  alignment?: Py3sAlignment;
  rendering?: {
    gamma?: number;
    opacityCutoff?: number;
    splatScale?: number;
  };
  printing?: {
    format: '3mf';
    unit: 'millimeter';
    heightMm: number;
    source: 'reconstructed-mesh' | 'local-print-cache';
    validation: string;
    cacheKey?: string;
    print3mfBytes?: number;
    // Topology checks do not establish minimum thickness or mechanical strength.
    requiresSlicerReview: true;
  };
  [key: string]: unknown;
}

export interface Py3sContainerData {
  spzData: Uint8Array;
  colliderData?: Uint8Array;
  metadata: Py3sMetadata;
  thumbnailData?: Uint8Array;
  print3mfData?: Uint8Array;
}

export interface Py3sPackOptions {
  /** Force enabling or disabling CRC-32 integrity fields (defaults to true for v2.0). */
  integrityChecksum?: boolean;
  /**
   * Pack with v1.x binary header (VersionMajor = 1, clean reserved bytes, core v1 flags)
   * for Unreal Engine 5 / Unity v1.x plugin compatibility while preserving Section 3 JSON metadata.
   */
  compatibleV1?: boolean;
}

export interface Py3sHeaderInfo {
  versionMajor: number;
  versionMinor: number;
  sectionCount: number;
  flags: number;
  hasIntegrityChecksum: boolean;
  hasSecuritySignature: boolean;
  containerCrc32: number;
  print3mfCrc32: number;
  sections: {
    spz: { offset: number; size: number };
    collider: { offset: number; size: number };
    metadata: { offset: number; size: number };
    thumbnail: { offset: number; size: number };
    print3mf: { offset: number; size: number };
  };
}

function hasV2FeatureFields(metadata: Py3sMetadata): boolean {
  return Boolean(
    metadata.physSkin ||
    metadata.phys_skin ||
    metadata.magneticMpm ||
    metadata.magnetic_mpm ||
    metadata.enliveningGs ||
    metadata.enlivening_gs ||
    metadata.stress ||
    metadata.stressSimulation ||
    metadata.voronoi ||
    metadata.fractureEngine ||
    metadata.thermal ||
    metadata.megas ||
    metadata.thermalDynamics ||
    metadata.wilting ||
    metadata.biologicalSimulation ||
    metadata.diffwind ||
    metadata.aiAgentContext ||
    metadata.hanumanParametric ||
    metadata.isSeed ||
    metadata.dehydrated ||
    metadata.telemetryProfile
  );
}

function resolveFlags(data: Py3sContainerData, enableIntegrityChecksum: boolean, compatibleV1 = false): number {
  const meta = data.metadata;
  const isFbx = meta.collision?.format?.toLowerCase() === 'fbx';
  let flags = PY3S_FLAG_SPZ_ZSTD | (isFbx ? PY3S_FLAG_COLLIDER_FBX : PY3S_FLAG_COLLIDER_GLB);
  const printBytes = data.print3mfData;

  if (compatibleV1) {
    if (printBytes && printBytes.byteLength > 0) {
      flags |= PY3S_FLAG_PRINT_3MF;
    }
    if ((meta.telemetryProfile as { autoHydrateOnMount?: boolean } | undefined)?.autoHydrateOnMount) {
      flags |= PY3S_FLAG_AUTO_HYDRATE_ON_MOUNT;
    }
    return flags >>> 0;
  }

  if (printBytes && printBytes.byteLength > 0) {
    flags |= PY3S_FLAG_PRINT_3MF | PY3S_FLAG_MFG_PRINT3D_READY;
  }
  if (meta.collision?.type && /convex|coacd/i.test(meta.collision.type)) {
    flags |= PY3S_FLAG_COLLIDER_CONVEX;
  }
  if (meta.stress || meta.stressSimulation) flags |= PY3S_FLAG_SIM_STRESS;
  if (meta.voronoi || meta.fractureEngine) flags |= PY3S_FLAG_SIM_VORONOI_CRACK;
  if (meta.thermal || meta.megas || meta.thermalDynamics) flags |= PY3S_FLAG_SIM_MEGAS_THERMAL;
  if (meta.wilting || meta.biologicalSimulation) flags |= PY3S_FLAG_SIM_PLANT_WILTING;
  if (meta.diffwind) flags |= PY3S_FLAG_SIM_DIFFWIND;
  if (meta.physSkin || meta.phys_skin) flags |= PY3S_FLAG_SIM_PHYSSKIN;
  if (meta.magneticMpm || meta.magnetic_mpm) flags |= PY3S_FLAG_SIM_MAGNETIC_MPM;
  if (meta.enliveningGs || meta.enlivening_gs) flags |= PY3S_FLAG_SIM_ENLIVENING_GS;
  if (meta.manufacturing || meta.print3d || meta.printing || meta.printProfile) flags |= PY3S_FLAG_MFG_PRINT3D_READY;
  if (meta.systemPrompt || meta.agentPrompt || meta.aiAgentContext) flags |= PY3S_FLAG_AI_SYSTEM_PROMPT;
  if (meta.isSeed || meta.dehydrated || (meta.telemetryProfile as { isDehydratedSeed?: boolean } | undefined)?.isDehydratedSeed) {
    flags |= PY3S_FLAG_STATE_DEHYDRATED_SEED | PY3S_FLAG_AUTO_HYDRATE_ON_MOUNT;
  }
  if (meta.hanumanParametric || (meta.aiAgentContext as { orchestratedBy?: string } | undefined)?.orchestratedBy) {
    flags |= PY3S_FLAG_HANUMAN_PARAMETRIC_AI;
  }
  if (enableIntegrityChecksum) {
    flags |= PY3S_FLAG_INTEGRITY_CRC32;
  }
  return flags >>> 0;
}

export class Py3sCodec {
  /**
   * Inspects the 128-byte binary header without decoding JSON metadata.
   */
  public static inspectHeader(buffer: ArrayBuffer | Uint8Array): Py3sHeaderInfo {
    const bytes = buffer instanceof Uint8Array ? buffer : new Uint8Array(buffer);
    if (bytes.byteLength < PY3S_HEADER_SIZE) {
      throw new Error(`Invalid PY3S buffer: size ${bytes.byteLength} < ${PY3S_HEADER_SIZE}`);
    }
    if (bytes[0] !== 0x50 || bytes[1] !== 0x59 || bytes[2] !== 0x33 || bytes[3] !== 0x53) {
      throw new Error('Not a valid PY3S container (header magic mismatch)');
    }
    const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
    const versionMajor = view.getUint16(4, true);
    if (versionMajor > PY3S_VERSION_MAJOR) {
      throw new Error(`Unsupported PY3S version: ${versionMajor} > ${PY3S_VERSION_MAJOR}`);
    }
    const versionMinor = view.getUint16(6, true);
    const sectionCount = view.getUint32(8, true);
    const flags = view.getUint32(12, true);
    const hasPrint = (flags & PY3S_FLAG_PRINT_3MF) !== 0;
    const hasIntegrityChecksum = (flags & PY3S_FLAG_INTEGRITY_CRC32) !== 0;
    const hasSecuritySignature = (flags & PY3S_FLAG_SECURITY_HMAC) !== 0;

    return {
      versionMajor,
      versionMinor,
      sectionCount,
      flags,
      hasIntegrityChecksum,
      hasSecuritySignature,
      containerCrc32: hasIntegrityChecksum ? view.getUint32(CRC32_CHECKSUM_FIELD_OFFSET, true) : 0,
      print3mfCrc32: hasIntegrityChecksum ? view.getUint32(CRC32_CHECKSUM_FIELD_OFFSET + 4, true) : 0,
      sections: {
        spz: { offset: Number(view.getBigUint64(16, true)), size: Number(view.getBigUint64(24, true)) },
        collider: { offset: Number(view.getBigUint64(32, true)), size: Number(view.getBigUint64(40, true)) },
        metadata: { offset: Number(view.getBigUint64(48, true)), size: Number(view.getBigUint64(56, true)) },
        thumbnail: { offset: Number(view.getBigUint64(64, true)), size: Number(view.getBigUint64(72, true)) },
        print3mf: {
          offset: hasPrint ? Number(view.getBigUint64(80, true)) : 0,
          size: hasPrint ? Number(view.getBigUint64(88, true)) : 0,
        },
      },
    };
  }

  /**
   * Packs SPZ, Collider, Metadata, optional Thumbnail and optional Print 3MF into a .py3s container.
   * Defaults to v2.0 with CRC-32 integrity checksums when metadata declares v2.x or v2 features;
   * preserves v1.0 / v1.1 header versions when explicitly tagged for legacy compatibility.
   */
  public static pack(data: Py3sContainerData, options?: Py3sPackOptions): Uint8Array {
    const textEncoder = new TextEncoder();
    const metaBytes = textEncoder.encode(JSON.stringify(data.metadata));
    if (metaBytes.byteLength > PY3S_MAX_METADATA_BYTES) {
      throw new Error(`PY3S metadata exceeds maximum limit (${metaBytes.byteLength} > ${PY3S_MAX_METADATA_BYTES})`);
    }

    const spzBytes = data.spzData;
    const colliderBytes = data.colliderData ?? new Uint8Array(0);
    const thumbBytes = data.thumbnailData ?? new Uint8Array(0);
    const printBytes = data.print3mfData ?? new Uint8Array(0);

    const compatibleV1 = options?.compatibleV1 === true;
    const versionString = data.metadata.version || '';
    const isExplicitV1 = compatibleV1 || (/^1\./.test(versionString) && !hasV2FeatureFields(data.metadata) && options?.integrityChecksum !== true);
    const isV2 = !isExplicitV1;
    const versionMajor = isV2 ? PY3S_VERSION_MAJOR : 1;
    const versionMinor = isV2 ? PY3S_VERSION_MINOR : (printBytes.byteLength > 0 ? 1 : 0);
    const enableIntegrity = compatibleV1 ? (options?.integrityChecksum === true) : (options?.integrityChecksum ?? isV2);

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

    const printOffset = printBytes.byteLength ? currentOffset : 0;
    currentOffset += printBytes.byteLength;
    if (printBytes.byteLength) sectionCount += 1;

    const totalSize = currentOffset;
    const output = new Uint8Array(totalSize);
    const view = new DataView(output.buffer, output.byteOffset, output.byteLength);

    // 1. Magic "PY3S"
    output[0] = 0x50; // 'P'
    output[1] = 0x59; // 'Y'
    output[2] = 0x33; // '3'
    output[3] = 0x53; // 'S'

    // 2. Version
    view.setUint16(4, versionMajor, true);
    view.setUint16(6, versionMinor, true);

    // 3. Section count & unified bit flags
    view.setUint32(8, sectionCount, true);
    const flags = resolveFlags(data, enableIntegrity, compatibleV1);
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
    view.setBigUint64(80, BigInt(printOffset), true);
    view.setBigUint64(88, BigInt(printBytes.byteLength), true);

    // 5. Copy payloads
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
    if (printBytes.byteLength > 0) {
      output.set(printBytes, printOffset);
    }

    // 6. Stamp CRC-32 integrity checksums into header 0x60..0x67 when enabled
    if (enableIntegrity) {
      const containerCrc = computeContainerCrc32(output);
      const printCrc = printBytes.byteLength > 0 ? computePy3sCrc32(printBytes) : 0;
      view.setUint32(CRC32_CHECKSUM_FIELD_OFFSET, containerCrc, true);
      view.setUint32(CRC32_CHECKSUM_FIELD_OFFSET + 4, printCrc, true);
    }

    return output;
  }

  /**
   * Unpacks and validates a .py3s container (supports v1.0, v1.1, and v2.0 with CRC-32 verification).
   */
  public static unpack(buffer: ArrayBuffer | Uint8Array): Py3sContainerData {
    const bytes = buffer instanceof Uint8Array ? buffer : new Uint8Array(buffer);
    const header = Py3sCodec.inspectHeader(bytes);
    const {
      flags,
      hasIntegrityChecksum,
      containerCrc32,
      print3mfCrc32,
      sections: { spz, collider, metadata: metaSec, thumbnail, print3mf },
    } = header;

    const sectionPairs: [number, number][] = [
      [spz.offset, spz.size],
      [collider.offset, collider.size],
      [metaSec.offset, metaSec.size],
      [thumbnail.offset, thumbnail.size],
      [print3mf.offset, print3mf.size],
    ];
    const occupied: [number, number][] = [];
    for (const [offset, size] of sectionPairs) {
      if (!Number.isSafeInteger(offset) || !Number.isSafeInteger(size) || size < 0 ||
          (size > 0 && (offset < PY3S_HEADER_SIZE || offset > bytes.byteLength - size))) {
        throw new Error('Invalid PY3S section range');
      }
      if (size > 0) occupied.push([offset, offset + size]);
    }
    occupied.sort((a, b) => a[0] - b[0]);
    if (occupied.some((range, i) => i > 0 && range[0] < occupied[i - 1][1])) {
      throw new Error('Overlapping PY3S sections');
    }
    const hasPrint = (flags & PY3S_FLAG_PRINT_3MF) !== 0;
    if (hasPrint && !print3mf.size) throw new Error('Missing PY3S print payload');

    if (hasIntegrityChecksum) {
      const actualContainerCrc = computeContainerCrc32(bytes);
      if (actualContainerCrc !== containerCrc32) {
        throw new Error('PY3S integrity check failed: container CRC32 mismatch');
      }
    }

    const spzData = bytes.slice(spz.offset, spz.offset + spz.size);
    const colliderData = collider.size > 0 ? bytes.slice(collider.offset, collider.offset + collider.size) : undefined;

    let metadata: Py3sMetadata;
    if (metaSec.size > 0) {
      if (metaSec.size > PY3S_MAX_METADATA_BYTES) {
        throw new Error(`PY3S metadata exceeds maximum safe size (${metaSec.size} > ${PY3S_MAX_METADATA_BYTES})`);
      }
      const metaBytes = bytes.slice(metaSec.offset, metaSec.offset + metaSec.size);
      const textDecoder = new TextDecoder('utf-8');
      metadata = sanitizeMetadataValue(JSON.parse(textDecoder.decode(metaBytes))) as Py3sMetadata;
    } else {
      metadata = {
        format: 'py3s',
        version: '1.0.0',
        asset: { name: 'unnamed' },
      };
    }

    const thumbnailData = thumbnail.size > 0 && thumbnail.offset > 0
      ? bytes.slice(thumbnail.offset, thumbnail.offset + thumbnail.size)
      : undefined;
    const print3mfData = print3mf.size ? bytes.slice(print3mf.offset, print3mf.offset + print3mf.size) : undefined;

    if (hasIntegrityChecksum && print3mfData && computePy3sCrc32(print3mfData) !== print3mfCrc32) {
      throw new Error('PY3S integrity check failed: Print 3D payload CRC32 mismatch');
    }

    return {
      spzData,
      colliderData,
      metadata,
      thumbnailData,
      print3mfData,
    };
  }

  /**
   * Signs a valid .py3s buffer with a 192-bit HMAC-SHA256 tag (stored at header 0x68..0x7F)
   * and updates its CRC-32 header checksum so unauthenticated readers can still verify CRC-32.
   */
  public static async signContainer(
    buffer: ArrayBuffer | Uint8Array,
    secretKey: string | Uint8Array,
  ): Promise<Uint8Array> {
    const input = buffer instanceof Uint8Array ? buffer : new Uint8Array(buffer);
    Py3sCodec.unpack(input);
    const signed = new Uint8Array(input);
    const view = new DataView(signed.buffer, signed.byteOffset, signed.byteLength);
    const updatedFlags = (view.getUint32(12, true) | PY3S_FLAG_SECURITY_HMAC) >>> 0;
    view.setUint32(12, updatedFlags, true);

    const tag = await computeHmacTagBytes(signed, secretKey);
    signed.set(tag, HMAC_TAG_OFFSET);

    if ((updatedFlags & PY3S_FLAG_INTEGRITY_CRC32) !== 0) {
      view.setUint32(CRC32_CHECKSUM_FIELD_OFFSET, computeContainerCrc32(signed), true);
    }
    return signed;
  }

  /**
   * Verifies the 192-bit HMAC-SHA256 signature and header/payload integrity.
   */
  public static async verifySignature(
    buffer: ArrayBuffer | Uint8Array,
    secretKey: string | Uint8Array,
  ): Promise<boolean> {
    try {
      const bytes = buffer instanceof Uint8Array ? buffer : new Uint8Array(buffer);
      const header = Py3sCodec.inspectHeader(bytes);
      if (!header.hasSecuritySignature) {
        return false;
      }
      Py3sCodec.unpack(bytes);
      const expectedTag = await computeHmacTagBytes(bytes, secretKey);
      const actualTag = bytes.subarray(HMAC_TAG_OFFSET, HMAC_TAG_OFFSET + HMAC_TAG_LENGTH);
      return constantTimeEqual(actualTag, expectedTag);
    } catch {
      return false;
    }
  }

  /**
   * Convenience helper: packs a v2.0 container with CRC-32 enabled and stamps an HMAC-SHA256 signature.
   */
  public static async packSigned(
    data: Py3sContainerData,
    secretKey: string | Uint8Array,
    options?: Py3sPackOptions,
  ): Promise<Uint8Array> {
    const packed = Py3sCodec.pack(data, { integrityChecksum: true, ...options });
    return Py3sCodec.signContainer(packed, secretKey);
  }

  /**
   * Unpacks a .py3s container only after cryptographic HMAC-SHA256 verification succeeds.
   */
  public static async unpackVerified(
    buffer: ArrayBuffer | Uint8Array,
    secretKey: string | Uint8Array,
  ): Promise<Py3sContainerData> {
    const bytes = buffer instanceof Uint8Array ? buffer : new Uint8Array(buffer);
    const isValid = await Py3sCodec.verifySignature(bytes, secretKey);
    if (!isValid) {
      throw new Error('PY3S security verification failed: invalid or missing HMAC signature');
    }
    return Py3sCodec.unpack(bytes);
  }
}
