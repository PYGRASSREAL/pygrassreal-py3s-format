// Copyright 2026 PyGrassReal AI. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "Dom/JsonObject.h"

namespace PyGrassReal
{
	/** Magic string bytes: 'P', 'Y', '3', 'S' */
	static constexpr uint8 PY3S_MAGIC_BYTES[4] = { 'P', 'Y', '3', 'S' };
	static constexpr uint32 PY3S_MAGIC_UINT32 = 0x53335950; // Little-endian 'PY3S'

	static constexpr uint16 PY3S_VERSION_MAJOR = 2;
	static constexpr uint16 PY3S_VERSION_MINOR = 0;
	static constexpr int64 PY3S_HEADER_SIZE = 128;
	static constexpr int64 PY3S_MAX_METADATA_BYTES = 8LL * 1024LL * 1024LL;
	static constexpr int64 PY3S_CRC32_FIELD_OFFSET = 0x60;
	static constexpr int64 PY3S_CRC32_FIELD_LENGTH = 8;
	static constexpr int64 PY3S_HMAC_TAG_OFFSET = 0x68;
	static constexpr int64 PY3S_HMAC_TAG_LENGTH = 24;

	static constexpr uint32 PY3S_FLAG_NONE = 0x0;
	static constexpr uint32 PY3S_FLAG_SPZ_ZSTD = 0x1;
	static constexpr uint32 PY3S_FLAG_COLLIDER_GLB = 0x2;
	static constexpr uint32 PY3S_FLAG_COLLIDER_FBX = 0x4;
	static constexpr uint32 PY3S_FLAG_PRINT_3MF = 0x8;
	static constexpr uint32 PY3S_FLAG_SIM_STRESS = 0x10;
	static constexpr uint32 PY3S_FLAG_SIM_VORONOI_CRACK = 0x20;
	static constexpr uint32 PY3S_FLAG_SIM_MEGAS_THERMAL = 0x40;
	static constexpr uint32 PY3S_FLAG_SIM_PLANT_WILTING = 0x80;
	static constexpr uint32 PY3S_FLAG_SIM_DIFFWIND = 0x100;
	static constexpr uint32 PY3S_FLAG_SIM_PHYSSKIN = 0x200;
	static constexpr uint32 PY3S_FLAG_SIM_MAGNETIC_MPM = 0x400;
	static constexpr uint32 PY3S_FLAG_SIM_ENLIVENING_GS = 0x800;
	static constexpr uint32 PY3S_FLAG_MFG_PRINT3D_READY = 0x1000;
	static constexpr uint32 PY3S_FLAG_AI_SYSTEM_PROMPT = 0x2000;
	static constexpr uint32 PY3S_FLAG_STATE_DEHYDRATED_SEED = 0x4000;
	static constexpr uint32 PY3S_FLAG_AUTO_HYDRATE_ON_MOUNT = 0x8000;
	static constexpr uint32 PY3S_FLAG_HANUMAN_PARAMETRIC_AI = 0x10000;
	static constexpr uint32 PY3S_FLAG_INTEGRITY_CRC32 = 0x20000;
	static constexpr uint32 PY3S_FLAG_COLLIDER_CONVEX = 0x40000;
	static constexpr uint32 PY3S_FLAG_SECURITY_HMAC = 0x80000;

	/** IEEE 802.3 CRC-32 lookup table (polynomial 0xEDB88320) matching zlib.crc32 and TypeScript codec */
	inline const uint32* GetPy3sCrc32Table()
	{
		static uint32 Table[256] = {};
		static bool bInitialized = []()
		{
			for (uint32 i = 0; i < 256; ++i)
			{
				uint32 Crc = i;
				for (int32 Bit = 0; Bit < 8; ++Bit)
				{
					Crc = (Crc & 1u) ? (0xEDB88320u ^ (Crc >> 1)) : (Crc >> 1);
				}
				Table[i] = Crc;
			}
			return true;
		}();
		(void)bInitialized;
		return Table;
	}

	inline uint32 UpdatePy3sCrc32(uint32 Crc, const uint8* Data, int64 Start, int64 End)
	{
		const uint32* Table = GetPy3sCrc32Table();
		uint32 Current = Crc;
		for (int64 i = Start; i < End; ++i)
		{
			Current = Table[(Current ^ Data[i]) & 0xFFu] ^ (Current >> 8);
		}
		return Current;
	}

	inline uint32 ComputePy3sCrc32(const uint8* Data, int64 Size)
	{
		if (!Data || Size <= 0)
		{
			return 0u;
		}
		return UpdatePy3sCrc32(0xFFFFFFFFu, Data, 0, Size) ^ 0xFFFFFFFFu;
	}

	inline uint32 ComputeContainerCrc32(const uint8* Buffer, int64 BufferSize)
	{
		if (!Buffer || BufferSize < PY3S_HEADER_SIZE)
		{
			return 0u;
		}
		const uint32* Table = GetPy3sCrc32Table();
		uint32 Crc = UpdatePy3sCrc32(0xFFFFFFFFu, Buffer, 0, PY3S_CRC32_FIELD_OFFSET);
		for (int64 i = 0; i < PY3S_CRC32_FIELD_LENGTH; ++i)
		{
			Crc = Table[Crc & 0xFFu] ^ (Crc >> 8);
		}
		Crc = UpdatePy3sCrc32(
			Crc,
			Buffer,
			PY3S_CRC32_FIELD_OFFSET + PY3S_CRC32_FIELD_LENGTH,
			BufferSize
		);
		return Crc ^ 0xFFFFFFFFu;
	}

	#pragma pack(push, 1)
	/**
	 * 128-Byte Binary Header for .py3s Unified v2.0 Container files
	 */
	struct FPy3sFileHeader
	{
		uint8 Magic[4];             // 0x00: "PY3S"
		uint16 VersionMajor;        // 0x04: 2 (v2.0), 1 (legacy)
		uint16 VersionMinor;        // 0x06: 0 (v2.0/v1.0), 1 (v1.1 Print Layer)
		uint32 SectionCount;        // 0x08: Number of active sections (3 to 5)
		uint32 Flags;               // 0x0C: Unified feature, simulation, integrity & security flags
		uint64 SpzOffset;           // 0x10: Byte offset to 3DGS SPZ payload (or Seed proxy)
		uint64 SpzSize;             // 0x18: Size in bytes of SPZ payload
		uint64 ColliderOffset;      // 0x20: Byte offset to Collider mesh payload
		uint64 ColliderSize;        // 0x28: Size in bytes of Collider payload
		uint64 MetadataOffset;      // 0x30: Byte offset to Metadata JSON string
		uint64 MetadataSize;        // 0x38: Size in bytes of Metadata JSON
		uint64 ThumbnailOffset;     // 0x40: Byte offset to Preview Thumbnail (0 if none)
		uint64 ThumbnailSize;       // 0x48: Size in bytes of Thumbnail (0 if none)
		uint64 Print3mfOffset;      // 0x50: Byte offset to embedded Print 3D package (0 if none)
		uint64 Print3mfSize;        // 0x58: Size in bytes of Print 3D package (0 if none)
		uint32 ContainerCrc32;      // 0x60: v2.0 IEEE 802.3 CRC-32 of full container (0x60..0x67 zeroed)
		uint32 Print3mfCrc32;       // 0x64: v2.0 IEEE 802.3 CRC-32 of Print 3D payload (0 if none)
		uint8 HmacTag[24];          // 0x68: Security 192-bit truncated HMAC-SHA256 tag (when 0x80000 set)

		FPy3sFileHeader()
		{
			FMemory::Memzero(this, sizeof(FPy3sFileHeader));
			Magic[0] = 'P';
			Magic[1] = 'Y';
			Magic[2] = '3';
			Magic[3] = 'S';
			VersionMajor = PY3S_VERSION_MAJOR;
			VersionMinor = PY3S_VERSION_MINOR;
		}

		bool IsValid() const
		{
			return Magic[0] == 'P' && Magic[1] == 'Y' && Magic[2] == '3' && Magic[3] == 'S';
		}
	};
	#pragma pack(pop)

	static_assert(sizeof(FPy3sFileHeader) == 128, "FPy3sFileHeader must be exactly 128 bytes");

	/**
	 * High-level parsed Metadata stored inside Section 3 of a .py3s file
	 */
	struct PYGRASSREALSPZ_API FPy3sMetadata
	{
		FString Format = TEXT("py3s");
		FString Version = TEXT("2.0.0");
		FString Generator = TEXT("PyGrassReal");
		FString CreatedAt;

		FString AssetName;
		int32 PointCount = 0;
		FBox Bounds = FBox(EForceInit::ForceInit);

		FString CollisionFormat = TEXT("glb");
		int32 CollisionVertexCount = 0;
		int32 CollisionFaceCount = 0;
		FString CollisionType = TEXT("ConvexHull");
		bool bEnablePhysicsBounce = true;

		FRotator AlignmentRotation = FRotator(0.0f, -90.0f, 0.0f);
		FVector AlignmentOffset = FVector::ZeroVector;
		FVector AlignmentScale = FVector(-1.0f, 1.0f, 1.0f);
		float ScaleRatio = 1.0f;

		float Gamma = 0.7f;
		float OpacityCutoff = 0.05f;
		float SplatScale = 1.0f;

		bool bIsDehydratedSeed = false;
		bool bAutoHydrateOnMount = false;
		bool bHasPrintProfile = false;
		bool bHasAiSystemPrompt = false;
		bool bHasPhysSkin = false;
		bool bHasMagneticMpm = false;
		bool bHanumanParametricAi = false;

		FString StructuralAuditStatus;
		float MinWallMm = 0.0f;
		float StructuralSafetyFactor = 0.0f;

		FString ToJson() const;
		bool FromJson(const FString& JsonStr);
	};

	/**
	 * In-memory Representation of a .py3s Container
	 */
	struct PYGRASSREALSPZ_API FPy3sContainer
	{
		FPy3sFileHeader Header;
		TArray<uint8> SpzData;
		TArray<uint8> ColliderData;
		FString MetadataJson;
		TArray<uint8> ThumbnailData;
		TArray<uint8> Print3mfData;
		FPy3sMetadata Metadata;
		bool bIntegrityVerified = false;

		bool HasSpz() const { return SpzData.Num() > 0; }
		bool HasCollider() const { return ColliderData.Num() > 0; }
		bool HasThumbnail() const { return ThumbnailData.Num() > 0; }
		bool HasPrint3mf() const { return Print3mfData.Num() > 0; }
		bool HasIntegrityChecksum() const { return (Header.Flags & PY3S_FLAG_INTEGRITY_CRC32) != 0; }
		bool HasSecuritySignature() const { return (Header.Flags & PY3S_FLAG_SECURITY_HMAC) != 0; }
		bool IsDehydratedSeed() const { return (Header.Flags & PY3S_FLAG_STATE_DEHYDRATED_SEED) != 0; }
	};
}
