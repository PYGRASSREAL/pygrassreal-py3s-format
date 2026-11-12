#!/usr/bin/env python3
# Copyright (c) 2026 PyGrassReal AI. All Rights Reserved.
# Brand: PyGrassReal (https://pygrassreal.ai)
# Specification: PyGrassReal 3D Splat Unified Container Asset Format (.py3s) v2.0
"""
PyGrassReal 3D Splat (.py3s) Unified v2.0 Codec & CLI Tool
Official Reference Implementation by PyGrassReal AI.
Supports v1.0, v1.1 (Print 3MF), and Unified v2.0 with CRC-32 Integrity Verification.
"""

import argparse
import hashlib
import hmac
import io
import json
import os
import re
import struct
import sys
import zipfile
import zlib
from typing import Any, Dict, Optional, Tuple, Union

HEADER_MAGIC = b"PY3S"
HEADER_FORMAT = "<4sHHIIQQQQQQQQQQII24s"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
assert HEADER_SIZE == 128, f"Header size must be 128 bytes, got {HEADER_SIZE}"

VERSION_MAJOR = 2
VERSION_MINOR = 0

FLAG_NONE = 0x0
FLAG_SPZ_ZSTD = 0x1
FLAG_COLLIDER_GLB = 0x2
FLAG_COLLIDER_FBX = 0x4
FLAG_PRINT_3MF = 0x8
FLAG_SIM_STRESS = 0x10
FLAG_SIM_VORONOI_CRACK = 0x20
FLAG_SIM_MEGAS_THERMAL = 0x40
FLAG_SIM_PLANT_WILTING = 0x80
FLAG_SIM_DIFFWIND = 0x100
FLAG_SIM_PHYSSKIN = 0x200
FLAG_SIM_MAGNETIC_MPM = 0x400
FLAG_SIM_ENLIVENING_GS = 0x800
FLAG_MFG_PRINT3D_READY = 0x1000
FLAG_AI_SYSTEM_PROMPT = 0x2000
FLAG_STATE_DEHYDRATED_SEED = 0x4000
FLAG_AUTO_HYDRATE_ON_MOUNT = 0x8000
FLAG_HANUMAN_PARAMETRIC_AI = 0x10000
FLAG_INTEGRITY_CRC32 = 0x20000
FLAG_COLLIDER_CONVEX = 0x40000
FLAG_SECURITY_HMAC = 0x80000

CRC32_FIELD_OFFSET = 0x60
CRC32_FIELD_LENGTH = 8
HMAC_TAG_OFFSET = 0x68
HMAC_TAG_LENGTH = 24

MAX_METADATA_BYTES = 8 * 1024 * 1024
MAX_METADATA_DEPTH = 24
MAX_ZIP_ARCHIVE_BYTES = 128 * 1024 * 1024
MAX_ZIP_ENTRIES = 256
MAX_ZIP_UNCOMPRESSED_BYTES = 256 * 1024 * 1024
MAX_ZIP_RATIO = 100

DANGEROUS_OBJECT_KEYS = frozenset({"__proto__", "constructor", "prototype"})
XML_ENTITY_DIRECTIVE_RE = re.compile(rb"<!(?:DOCTYPE|ENTITY)\b", re.IGNORECASE)
SAFE_FILENAME_TOKEN_RE = re.compile(r"[^A-Za-z0-9._-]+")
WINDOWS_DRIVE_PREFIX_RE = re.compile(r"^[A-Za-z]:")


def compute_crc32(data: bytes) -> int:
    return zlib.crc32(data) & 0xFFFFFFFF


def compute_container_crc32(buffer: bytes) -> int:
    crc = zlib.crc32(buffer[:CRC32_FIELD_OFFSET], 0)
    crc = zlib.crc32(b"\x00" * CRC32_FIELD_LENGTH, crc)
    crc = zlib.crc32(buffer[CRC32_FIELD_OFFSET + CRC32_FIELD_LENGTH:], crc)
    return crc & 0xFFFFFFFF


def _has_v2_features(metadata: Dict[str, Any]) -> bool:
    v2_keys = (
        "physSkin", "phys_skin",
        "magneticMpm", "magnetic_mpm",
        "enliveningGs", "enlivening_gs",
        "stress", "stressSimulation",
        "voronoi", "fractureEngine",
        "thermal", "megas", "thermalDynamics",
        "wilting", "biologicalSimulation",
        "diffwind",
        "aiAgentContext",
        "hanumanParametric",
        "isSeed", "dehydrated", "telemetryProfile",
    )
    return any(bool(metadata.get(key)) for key in v2_keys)


def _resolve_flags(
    metadata: Dict[str, Any],
    print_3mf_bytes: bytes,
    enable_integrity: bool,
    compatible_v1: bool = False,
) -> int:
    col_format = str(metadata.get("collision", {}).get("format", "glb")).lower()
    flags = FLAG_SPZ_ZSTD | (FLAG_COLLIDER_FBX if col_format == "fbx" else FLAG_COLLIDER_GLB)

    if compatible_v1:
        if print_3mf_bytes:
            flags |= FLAG_PRINT_3MF
        telemetry = metadata.get("telemetryProfile")
        if isinstance(telemetry, dict) and telemetry.get("autoHydrateOnMount", False):
            flags |= FLAG_AUTO_HYDRATE_ON_MOUNT
        return flags & 0xFFFFFFFF

    if print_3mf_bytes:
        flags |= FLAG_PRINT_3MF | FLAG_MFG_PRINT3D_READY
    col_type = str(metadata.get("collision", {}).get("type", ""))
    if "convex" in col_type.lower() or "coacd" in col_type.lower():
        flags |= FLAG_COLLIDER_CONVEX

    if metadata.get("stress") or metadata.get("stressSimulation"):
        flags |= FLAG_SIM_STRESS
    if metadata.get("voronoi") or metadata.get("fractureEngine"):
        flags |= FLAG_SIM_VORONOI_CRACK
    if metadata.get("thermal") or metadata.get("megas") or metadata.get("thermalDynamics"):
        flags |= FLAG_SIM_MEGAS_THERMAL
    if metadata.get("wilting") or metadata.get("biologicalSimulation"):
        flags |= FLAG_SIM_PLANT_WILTING
    if metadata.get("diffwind"):
        flags |= FLAG_SIM_DIFFWIND
    if metadata.get("physSkin") or metadata.get("phys_skin"):
        flags |= FLAG_SIM_PHYSSKIN
    if metadata.get("magneticMpm") or metadata.get("magnetic_mpm"):
        flags |= FLAG_SIM_MAGNETIC_MPM
    if metadata.get("enliveningGs") or metadata.get("enlivening_gs"):
        flags |= FLAG_SIM_ENLIVENING_GS
    if (
        metadata.get("manufacturing")
        or metadata.get("print3d")
        or metadata.get("printing")
        or metadata.get("printProfile")
    ):
        flags |= FLAG_MFG_PRINT3D_READY
    if metadata.get("systemPrompt") or metadata.get("agentPrompt") or metadata.get("aiAgentContext"):
        flags |= FLAG_AI_SYSTEM_PROMPT
    telemetry = metadata.get("telemetryProfile")
    is_seed = (
        metadata.get("isSeed", False)
        or metadata.get("dehydrated", False)
        or (isinstance(telemetry, dict) and telemetry.get("isDehydratedSeed", False))
    )
    if is_seed:
        flags |= FLAG_STATE_DEHYDRATED_SEED | FLAG_AUTO_HYDRATE_ON_MOUNT
    ai_ctx = metadata.get("aiAgentContext")
    if metadata.get("hanumanParametric", False) or (isinstance(ai_ctx, dict) and ai_ctx.get("orchestratedBy")):
        flags |= FLAG_HANUMAN_PARAMETRIC_AI
    if enable_integrity:
        flags |= FLAG_INTEGRITY_CRC32
    return flags


def sanitize_filename_token(raw_value: Any, default: str = "py3s_asset", max_len: int = 80) -> str:
    """Restricts untrusted metadata names to a safe single filename token."""
    text = str(raw_value or "").replace("\x00", "").strip()
    leaf = re.split(r"[/\\]+", text)[-1] if text else ""
    cleaned = SAFE_FILENAME_TOKEN_RE.sub("_", leaf).replace("..", "_").strip("._")
    if not cleaned or cleaned in (".", ".."):
        return default
    return cleaned[:max_len]


def sanitize_extension(raw_ext: Any, default: str = "glb") -> str:
    """Restricts untrusted file extension metadata to short lowercase alphanumeric characters."""
    cleaned = re.sub(r"[^a-z0-9]", "", str(raw_ext or "").lower())
    if not cleaned or len(cleaned) > 8:
        return default
    return cleaned


def _sanitize_metadata(value: Any, depth: int = 0) -> Any:
    if depth > MAX_METADATA_DEPTH:
        raise ValueError("PY3S metadata exceeds maximum nesting depth")
    if isinstance(value, list):
        return [_sanitize_metadata(item, depth + 1) for item in value]
    if isinstance(value, dict):
        clean: Dict[str, Any] = {}
        for k, v in value.items():
            key_str = str(k)
            if key_str in DANGEROUS_OBJECT_KEYS:
                continue
            clean[key_str] = _sanitize_metadata(v, depth + 1)
        return clean
    return value


def _normalize_secret_key(secret_key: Union[str, bytes]) -> bytes:
    key_bytes = secret_key.encode("utf-8") if isinstance(secret_key, str) else bytes(secret_key)
    if not key_bytes:
        raise ValueError("PY3S HMAC secret key cannot be empty")
    return key_bytes


def _compute_hmac_tag(container_bytes: bytes, secret_key: Union[str, bytes]) -> bytes:
    """Computes truncated 192-bit HMAC-SHA256 over container bytes with 0x60..0x7F zeroed."""
    key_bytes = _normalize_secret_key(secret_key)
    signing_input = bytearray(container_bytes)
    signing_input[CRC32_FIELD_OFFSET:HEADER_SIZE] = b"\x00" * (HEADER_SIZE - CRC32_FIELD_OFFSET)
    return hmac.new(key_bytes, bytes(signing_input), hashlib.sha256).digest()[:HMAC_TAG_LENGTH]


def validate_safe_zip_bytes(data: bytes, require_3mf_model: bool = True) -> None:
    """Validates ZIP archive structure before full consumption to prevent Zip Bombs, Zip Slip, and XXE."""
    if len(data) < 22 or len(data) > MAX_ZIP_ARCHIVE_BYTES:
        raise ValueError(f"Invalid or oversized Print 3D ZIP archive ({len(data)} bytes)")
    if not data.startswith(b"PK\x03\x04"):
        raise ValueError("Print 3D payload is not a valid ZIP archive")

    try:
        with zipfile.ZipFile(io.BytesIO(data), "r") as zf:
            infos = zf.infolist()
            if not infos or len(infos) > MAX_ZIP_ENTRIES:
                raise ValueError(f"Unsafe Print 3D ZIP entry count ({len(infos)})")

            total_uncompressed = 0
            has_3mf_model = False

            for info in infos:
                name = info.filename
                if (
                    not name
                    or "\x00" in name
                    or name.startswith("/")
                    or name.startswith("\\")
                    or WINDOWS_DRIVE_PREFIX_RE.match(name)
                ):
                    raise ValueError(f"Unsafe ZIP entry path (Zip Slip blocked): {name}")

                segments = re.split(r"[/\\]", name)
                if any(seg == ".." for seg in segments):
                    raise ValueError(f"Unsafe ZIP traversal entry (Zip Slip blocked): {name}")

                if info.file_size < 0 or info.compress_size < 0:
                    raise ValueError(f"Invalid negative ZIP entry size: {name}")

                total_uncompressed += info.file_size
                if total_uncompressed > MAX_ZIP_UNCOMPRESSED_BYTES:
                    raise ValueError("Print 3D ZIP uncompressed payload exceeds safety limit")

                if info.file_size > 10 * 1024 * 1024:
                    if info.compress_size == 0 or (info.file_size / info.compress_size) > MAX_ZIP_RATIO:
                        raise ValueError(f"Suspicious Print 3D ZIP compression ratio for entry: {name}")

                norm_name = name.replace("\\", "/")
                if norm_name == "3D/3dmodel.model":
                    has_3mf_model = True

                if norm_name.lower().endswith((".model", ".xml", ".rels")):
                    with zf.open(info, "r") as entry_stream:
                        head_chunk = entry_stream.read(16384)
                        if XML_ENTITY_DIRECTIVE_RE.search(head_chunk):
                            raise ValueError(f"Unsafe XML directive detected in Print 3D archive entry: {name}")

            if require_3mf_model and not has_3mf_model:
                raise ValueError("3MF archive has no 3D/3dmodel.model")
    except zipfile.BadZipFile as exc:
        raise ValueError(f"Invalid Print 3D ZIP archive: {exc}") from exc


class Py3sContainer:
    def __init__(self) -> None:
        self.version_major: int = VERSION_MAJOR
        self.version_minor: int = VERSION_MINOR
        self.flags: int = FLAG_SPZ_ZSTD | FLAG_COLLIDER_GLB
        self.spz_data: bytes = b""
        self.collider_data: bytes = b""
        self.metadata: Dict[str, Any] = {}
        self.thumbnail_data: bytes = b""
        self.print_3mf_data: bytes = b""
        self.container_crc32: int = 0
        self.print_3mf_crc32: int = 0
        self.hmac_tag: bytes = b""
        self.has_security_signature: bool = False

    @classmethod
    def pack(
        cls,
        spz_bytes: bytes,
        collider_bytes: bytes,
        metadata_dict: Dict[str, Any],
        thumbnail_bytes: bytes = b"",
        print_3mf_bytes: bytes = b"",
        integrity_checksum: Optional[bool] = None,
        secret_key: Optional[Union[str, bytes]] = None,
        compatible_v1: bool = False,
    ) -> bytes:
        meta_json = json.dumps(metadata_dict, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        if len(meta_json) > MAX_METADATA_BYTES:
            raise ValueError(f"PY3S metadata exceeds maximum safe size ({len(meta_json)} > {MAX_METADATA_BYTES})")

        version_str = str(metadata_dict.get("version", ""))
        is_explicit_v1 = (
            compatible_v1
            or (
                version_str.startswith("1.")
                and not _has_v2_features(metadata_dict)
                and integrity_checksum is not True
            )
        )
        is_v2 = not is_explicit_v1
        version_major = VERSION_MAJOR if is_v2 else 1
        version_minor = VERSION_MINOR if is_v2 else (1 if print_3mf_bytes else 0)
        enable_integrity = bool(integrity_checksum) if compatible_v1 else (is_v2 if integrity_checksum is None else bool(integrity_checksum))

        current_offset = HEADER_SIZE
        spz_offset = current_offset
        spz_size = len(spz_bytes)
        current_offset += spz_size

        collider_offset = current_offset
        collider_size = len(collider_bytes)
        current_offset += collider_size

        meta_offset = current_offset
        meta_size = len(meta_json)
        current_offset += meta_size

        section_count = 3
        thumb_offset = 0
        thumb_size = 0
        if thumbnail_bytes:
            thumb_offset = current_offset
            thumb_size = len(thumbnail_bytes)
            current_offset += thumb_size
            section_count = 4

        print_offset = current_offset if print_3mf_bytes else 0
        print_size = len(print_3mf_bytes)
        if print_3mf_bytes:
            section_count += 1

        flags = _resolve_flags(metadata_dict, print_3mf_bytes, enable_integrity, compatible_v1=compatible_v1)
        payload = spz_bytes + collider_bytes + meta_json + thumbnail_bytes + print_3mf_bytes

        header_zero = struct.pack(
            HEADER_FORMAT,
            HEADER_MAGIC,
            version_major,
            version_minor,
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
            print_offset,
            print_size,
            0,
            0,
            b"\x00" * 24,
        )
        raw = header_zero + payload
        if not enable_integrity:
            return cls.sign_container(raw, secret_key) if secret_key is not None else raw

        container_crc = compute_container_crc32(raw)
        print_crc = compute_crc32(print_3mf_bytes) if print_3mf_bytes else 0
        output = bytearray(raw)
        struct.pack_into("<II", output, CRC32_FIELD_OFFSET, container_crc, print_crc)
        packed = bytes(output)
        if secret_key is not None:
            return cls.sign_container(packed, secret_key)
        return packed

    @classmethod
    def unpack(
        cls,
        buffer: bytes,
        secret_key: Optional[Union[str, bytes]] = None,
        require_signature: bool = False,
    ) -> "Py3sContainer":
        if len(buffer) < HEADER_SIZE:
            raise ValueError(f"Buffer too small: {len(buffer)} < {HEADER_SIZE}")

        (
            magic,
            v_maj,
            v_min,
            _sec_count,
            flags,
            spz_off,
            spz_sz,
            col_off,
            col_sz,
            meta_off,
            meta_sz,
            thumb_off,
            thumb_sz,
            print_off_raw,
            print_sz_raw,
            container_crc32,
            print_crc32,
            hmac_tag,
        ) = struct.unpack_from(HEADER_FORMAT, buffer, 0)

        if magic != HEADER_MAGIC:
            raise ValueError(f"Invalid PY3S magic header: {magic}")
        if v_maj > VERSION_MAJOR:
            raise ValueError(f"Unsupported PY3S major version: {v_maj}")

        has_print = bool(flags & FLAG_PRINT_3MF)
        print_off = print_off_raw if has_print else 0
        print_sz = print_sz_raw if has_print else 0

        sections = [
            (spz_off, spz_sz),
            (col_off, col_sz),
            (meta_off, meta_sz),
            (thumb_off, thumb_sz),
            (print_off, print_sz),
        ]
        occupied = []
        for offset, size in sections:
            if size and (offset < HEADER_SIZE or offset + size > len(buffer)):
                raise ValueError("Invalid PY3S section range")
            if size:
                occupied.append((offset, offset + size))
        occupied.sort()
        if any(occupied[i][0] < occupied[i - 1][1] for i in range(1, len(occupied))):
            raise ValueError("Overlapping PY3S sections")
        if has_print and not print_sz:
            raise ValueError("Missing PY3S print payload")

        has_integrity = bool(flags & FLAG_INTEGRITY_CRC32)
        if has_integrity and compute_container_crc32(buffer) != container_crc32:
            raise ValueError("PY3S integrity check failed: container CRC32 mismatch")

        has_signature = bool(flags & FLAG_SECURITY_HMAC)
        container = cls()
        container.version_major = v_maj
        container.version_minor = v_min
        container.flags = flags
        container.container_crc32 = container_crc32 if has_integrity else 0
        container.print_3mf_crc32 = print_crc32 if has_integrity else 0
        container.has_security_signature = has_signature
        container.hmac_tag = hmac_tag if has_signature else b""

        if require_signature:
            if not has_signature:
                raise ValueError("PY3S security verification failed: missing HMAC signature")
            if secret_key is None:
                raise ValueError("PY3S security verification failed: secret key is required")

        if secret_key is not None and (require_signature or has_signature):
            if not has_signature:
                raise ValueError("PY3S security verification failed: missing HMAC signature")
            expected_tag = _compute_hmac_tag(buffer, secret_key)
            if not hmac.compare_digest(hmac_tag, expected_tag):
                raise ValueError("PY3S security verification failed: invalid HMAC signature")

        if spz_sz > 0:
            container.spz_data = buffer[spz_off : spz_off + spz_sz]
        if col_sz > 0:
            container.collider_data = buffer[col_off : col_off + col_sz]
        if meta_sz > 0:
            if meta_sz > MAX_METADATA_BYTES:
                raise ValueError(f"PY3S metadata exceeds maximum safe size ({meta_sz} > {MAX_METADATA_BYTES})")
            meta_json = buffer[meta_off : meta_off + meta_sz].decode("utf-8")
            try:
                parsed_meta = json.loads(meta_json)
            except RecursionError as exc:
                raise ValueError("PY3S metadata exceeds maximum nesting depth") from exc
            if not isinstance(parsed_meta, dict):
                raise ValueError("PY3S metadata root must be a JSON object")
            container.metadata = _sanitize_metadata(parsed_meta)
        if thumb_sz > 0 and thumb_off > 0:
            container.thumbnail_data = buffer[thumb_off : thumb_off + thumb_sz]
        if print_sz > 0:
            container.print_3mf_data = buffer[print_off : print_off + print_sz]
            if has_integrity and compute_crc32(container.print_3mf_data) != print_crc32:
                raise ValueError("PY3S integrity check failed: Print 3D payload CRC32 mismatch")

        return container

    @classmethod
    def sign_container(cls, buffer: bytes, secret_key: Union[str, bytes]) -> bytes:
        """Stamps a 192-bit HMAC-SHA256 tag (0x68..0x7F) and refreshes ContainerCrc32."""
        cls.unpack(buffer)
        signed = bytearray(buffer)
        current_flags = struct.unpack_from("<I", signed, 12)[0]
        updated_flags = (current_flags | FLAG_SECURITY_HMAC) & 0xFFFFFFFF
        struct.pack_into("<I", signed, 12, updated_flags)

        tag = _compute_hmac_tag(bytes(signed), secret_key)
        signed[HMAC_TAG_OFFSET : HMAC_TAG_OFFSET + HMAC_TAG_LENGTH] = tag

        if updated_flags & FLAG_INTEGRITY_CRC32:
            struct.pack_into("<I", signed, CRC32_FIELD_OFFSET, compute_container_crc32(bytes(signed)))
        return bytes(signed)

    @classmethod
    def verify_signature(cls, buffer: bytes, secret_key: Union[str, bytes]) -> bool:
        """Verifies magic, bounds, CRC-32, metadata safety, and constant-time HMAC-SHA256 tag."""
        try:
            cls.unpack(buffer, secret_key=secret_key, require_signature=True)
            return True
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError, struct.error):
            return False

    @classmethod
    def pack_signed(
        cls,
        spz_bytes: bytes,
        collider_bytes: bytes,
        metadata_dict: Dict[str, Any],
        secret_key: Union[str, bytes],
        thumbnail_bytes: bytes = b"",
        print_3mf_bytes: bytes = b"",
    ) -> bytes:
        """Packs a v2.0 container with CRC-32 enabled and signs it with HMAC-SHA256."""
        return cls.pack(
            spz_bytes,
            collider_bytes,
            metadata_dict,
            thumbnail_bytes=thumbnail_bytes,
            print_3mf_bytes=print_3mf_bytes,
            integrity_checksum=True,
            secret_key=secret_key,
        )

    @classmethod
    def unpack_verified(cls, buffer: bytes, secret_key: Union[str, bytes]) -> "Py3sContainer":
        """Unpacks a .py3s container only after HMAC-SHA256 verification passes."""
        return cls.unpack(buffer, secret_key=secret_key, require_signature=True)


def _safe_join_confined(base_dir: str, filename: str) -> str:
    base_abs = os.path.abspath(base_dir)
    target_abs = os.path.abspath(os.path.join(base_abs, filename))
    if os.path.commonpath([base_abs, target_abs]) != base_abs:
        raise ValueError(f"Unsafe confined output path rejected: {filename}")
    return target_abs


def cmd_pack(args: argparse.Namespace) -> None:
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

    metadata: Dict[str, Any]
    if args.metadata and os.path.exists(args.metadata):
        if os.path.getsize(args.metadata) > MAX_METADATA_BYTES:
            raise ValueError(f"PY3S metadata file exceeds maximum safe size ({MAX_METADATA_BYTES} bytes)")
        with open(args.metadata, "r", encoding="utf-8") as f:
            raw_meta = json.load(f)
        if not isinstance(raw_meta, dict):
            raise ValueError("PY3S metadata root must be a JSON object")
        metadata = _sanitize_metadata(raw_meta)
    else:
        col_ext = sanitize_extension(os.path.splitext(args.collider)[1].lstrip(".")) if args.collider else "glb"
        metadata = {
            "format": "py3s",
            "version": "2.0.0",
            "generator": "py3s-codec-cli",
            "asset": {
                "name": sanitize_filename_token(os.path.splitext(os.path.basename(args.output))[0]),
                "pointCount": 0,
            },
            "collision": {
                "format": col_ext,
                "enablePhysicsBounce": True,
            },
            "alignment": {
                "rotation": [0.0, -90.0, 0.0],
                "offset": [0.0, 0.0, 0.0],
                "scale": [-1.0, 1.0, 1.0],
            },
        }

    thumb_data = b""
    if args.thumbnail and os.path.exists(args.thumbnail):
        with open(args.thumbnail, "rb") as f:
            thumb_data = f.read()

    print_data = b""
    if args.print_3mf:
        with open(args.print_3mf, "rb") as f:
            print_data = f.read()
        validate_safe_zip_bytes(print_data, require_3mf_model=True)

    secret_key = getattr(args, "secret_key", None)
    packed = Py3sContainer.pack(
        spz_data,
        collider_data,
        metadata,
        thumb_data,
        print_data,
        secret_key=secret_key,
    )
    with open(args.output, "wb") as f:
        f.write(packed)

    print(f"[OK] Packed into '{args.output}' ({len(packed):,} bytes)")
    print(f"   - SPZ       : {len(spz_data):,} bytes")
    print(f"   - Collider  : {len(collider_data):,} bytes")
    print(f"   - Metadata  : {len(json.dumps(metadata)):,} bytes")
    if thumb_data:
        print(f"   - Thumbnail : {len(thumb_data):,} bytes")
    if print_data:
        print(f"   - Print 3MF : {len(print_data):,} bytes")
    if secret_key:
        print("   - HMAC-SHA256 : SIGNED (192-bit)")


def cmd_unpack(args: argparse.Namespace) -> None:
    with open(args.input, "rb") as f:
        buffer = f.read()

    container = Py3sContainer.unpack(
        buffer,
        secret_key=getattr(args, "secret_key", None),
        require_signature=bool(getattr(args, "require_signature", False)),
    )
    out_dir = args.outdir or os.path.splitext(args.input)[0] + "_extracted"
    os.makedirs(out_dir, exist_ok=True)
    safe_base = sanitize_filename_token(os.path.splitext(os.path.basename(args.input))[0], default="py3s_asset")

    if container.spz_data:
        spz_path = _safe_join_confined(out_dir, f"{safe_base}.spz")
        with open(spz_path, "wb") as f:
            f.write(container.spz_data)
        print(f"   Extracted SPZ: {spz_path} ({len(container.spz_data):,} bytes)")

    if container.collider_data:
        col_fmt = sanitize_extension(container.metadata.get("collision", {}).get("format", "glb"), default="glb")
        col_path = _safe_join_confined(out_dir, f"{safe_base}_collider.{col_fmt}")
        with open(col_path, "wb") as f:
            f.write(container.collider_data)
        print(f"   Extracted Collider: {col_path} ({len(container.collider_data):,} bytes)")

    if container.metadata:
        meta_path = _safe_join_confined(out_dir, f"{safe_base}_metadata.json")
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(container.metadata, f, indent=2, ensure_ascii=False)
        print(f"   Extracted Metadata: {meta_path}")

    if container.thumbnail_data:
        thumb_path = _safe_join_confined(out_dir, f"{safe_base}_thumb.webp")
        with open(thumb_path, "wb") as f:
            f.write(container.thumbnail_data)
        print(f"   Extracted Thumbnail: {thumb_path}")

    if container.print_3mf_data:
        validate_safe_zip_bytes(container.print_3mf_data, require_3mf_model=False)
        print_path = _safe_join_confined(out_dir, f"{safe_base}_print.3mf")
        with open(print_path, "wb") as f:
            f.write(container.print_3mf_data)
        print(f"   Extracted Print 3MF: {print_path}")

    print(f"[OK] Finished extracting '{args.input}' into '{out_dir}/'")


def cmd_info(args: argparse.Namespace) -> None:
    with open(args.input, "rb") as f:
        buffer = f.read()

    secret_key = getattr(args, "secret_key", None)
    container = Py3sContainer.unpack(
        buffer,
        secret_key=secret_key,
        require_signature=bool(getattr(args, "require_signature", False)),
    )
    print("==================================================")
    print(f" PY3S Container Info: {args.input}")
    print("==================================================")
    print(f" Version      : {container.version_major}.{container.version_minor}")
    print(f" Flags        : {hex(container.flags)}")
    print(f" CRC-32 Check : {'PASS (' + hex(container.container_crc32) + ')' if container.flags & FLAG_INTEGRITY_CRC32 else 'Legacy (unsigned)'}")
    hmac_status = "SIGNED (" + ("VERIFIED" if secret_key else "key not supplied") + ")" if container.has_security_signature else "Unsigned"
    print(f" HMAC-SHA256  : {hmac_status}")
    print(f" File Size    : {len(buffer):,} bytes")
    print(f" SPZ Payload  : {len(container.spz_data):,} bytes")
    print(f" Collider Mesh: {len(container.collider_data):,} bytes")
    print(f" Thumbnail    : {len(container.thumbnail_data):,} bytes")
    print(f" Print 3MF    : {len(container.print_3mf_data):,} bytes")
    print(" Metadata     :")
    print(json.dumps(container.metadata, indent=2, ensure_ascii=False))


def main() -> None:
    parser = argparse.ArgumentParser(description="PyGrassReal 3D Splat (.py3s) Unified v2.0 Codec CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_pack = subparsers.add_parser("pack", help="Pack Visual Splat + Collision Mesh + Metadata into .py3s")
    p_pack.add_argument("--splat", "--spz", dest="splat", required=True, help="Path to input 3DGS visual splat file")
    p_pack.add_argument("--collider", required=False, help="Path to input collision geometry mesh")
    p_pack.add_argument("--metadata", required=False, help="Path to custom metadata .json")
    p_pack.add_argument("--thumbnail", required=False, help="Path to thumbnail preview image")
    p_pack.add_argument("--print-3mf", required=False, help="Path to a prepared print .3mf to embed")
    p_pack.add_argument("--secret-key", required=False, help="Optional HMAC-SHA256 secret key to sign container")
    p_pack.add_argument("-o", "--output", required=True, help="Path to output .py3s file")
    p_pack.set_defaults(func=cmd_pack)

    p_unpack = subparsers.add_parser("unpack", help="Unpack .py3s file into constituent files")
    p_unpack.add_argument("input", help="Path to input .py3s file")
    p_unpack.add_argument("-d", "--outdir", help="Directory to output extracted files")
    p_unpack.add_argument("--secret-key", required=False, help="HMAC-SHA256 secret key to verify signature")
    p_unpack.add_argument("--require-signature", action="store_true", help="Reject unsigned or unverified containers")
    p_unpack.set_defaults(func=cmd_unpack)

    p_info = subparsers.add_parser("info", help="Inspect & verify .py3s container")
    p_info.add_argument("input", help="Path to input .py3s file")
    p_info.add_argument("--secret-key", required=False, help="HMAC-SHA256 secret key to verify signature")
    p_info.add_argument("--require-signature", action="store_true", help="Reject unsigned or unverified containers")
    p_info.set_defaults(func=cmd_info)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
