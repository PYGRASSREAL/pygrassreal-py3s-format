// Copyright 2026 PyGrassReal AI. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "Dom/JsonObject.h"

namespace PyGrassReal
{
	/** Magic string bytes: 'P', 'Y', '3', 'S' */
	static constexpr uint8 PY3S_MAGIC_BYTES[4] = { 'P', 'Y', '3', 'S' };
	static constexpr uint32 PY3S_MAGIC_UINT32 = 0x53335950; // Little-endian 'PY3S'

	static constexpr uint16 PY3S_VERSION_MAJOR = 1;
	static constexpr uint16 PY3S_VERSION_MINOR = 0;

	static constexpr uint32 PY3S_FLAG_NONE = 0x0;
	static constexpr uint32 PY3S_FLAG_SPZ_ZSTD = 0x1;
	static constexpr uint32 PY3S_FLAG_COLLIDER_GLB = 0x2;
	static constexpr uint32 PY3S_FLAG_COLLIDER_FBX = 0x4;

	#pragma pack(push, 1)
	/**
	 * 128-Byte Binary Header for .py3s Container files
	 */
	struct FPy3sFileHeader
	{
		uint8 Magic[4];             // 0x00: "PY3S"
		uint16 VersionMajor;        // 0x04: 1
		uint16 VersionMinor;        // 0x06: 0
		uint32 SectionCount;        // 0x08: Number of active sections (usually 3 or 4)
		uint32 Flags;               // 0x0C: Format flags
		uint64 SpzOffset;           // 0x10: Byte offset to 3DGS SPZ payload
		uint64 SpzSize;             // 0x18: Size in bytes of SPZ payload
		uint64 ColliderOffset;      // 0x20: Byte offset to Collider mesh payload
		uint64 ColliderSize;        // 0x28: Size in bytes of Collider payload
		uint64 MetadataOffset;      // 0x30: Byte offset to Metadata JSON string
		uint64 MetadataSize;        // 0x38: Size in bytes of Metadata JSON
		uint64 ThumbnailOffset;     // 0x40: Byte offset to Preview Thumbnail (0 if none)
		uint64 ThumbnailSize;       // 0x48: Size in bytes of Thumbnail (0 if none)
		uint8 Reserved[48];         // 0x50: 48 bytes reserved for future extensions (e.g. py4s timelines, LODs)

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
		FString Version = TEXT("1.0.0");
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

		float Gamma = 0.7f;
		float OpacityCutoff = 0.05f;
		float SplatScale = 1.0f;

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
		FPy3sMetadata Metadata;

		bool HasSpz() const { return SpzData.Num() > 0; }
		bool HasCollider() const { return ColliderData.Num() > 0; }
		bool HasThumbnail() const { return ThumbnailData.Num() > 0; }
	};
}
