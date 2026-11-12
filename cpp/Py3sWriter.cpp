// Copyright 2026 PyGrassReal AI. All Rights Reserved.

#include "Py3sWriter.h"
#include "Misc/FileHelper.h"

namespace PyGrassReal
{
	bool FPy3sWriter::PackToBuffer(FPy3sContainer& Container, TArray<uint8>& OutBuffer, bool bEnableIntegrity)
	{
		// 1. Prepare Metadata JSON string
		if (Container.MetadataJson.IsEmpty())
		{
			Container.MetadataJson = Container.Metadata.ToJson();
		}

		FTCHARToUTF8 Utf8Converter(*Container.MetadataJson);
		const uint8* MetadataUtf8Ptr = reinterpret_cast<const uint8*>(Utf8Converter.Get());
		const int64 MetadataUtf8Len = Utf8Converter.Length();
		if (MetadataUtf8Len < 0 || MetadataUtf8Len > PY3S_MAX_METADATA_BYTES)
		{
			UE_LOG(LogTemp, Error, TEXT("[PyGrassRealSpz] Rejected PY3S pack: metadata exceeds 8 MB limit."));
			return false;
		}

		// 2. Setup Header offsets & sizes
		constexpr uint64 HeaderSize = sizeof(FPy3sFileHeader); // 128 bytes
		uint64 CurrentOffset = HeaderSize;

		Container.Header = FPy3sFileHeader();
		Container.bIntegrityVerified = false;

		// Section 1: SPZ
		Container.Header.SpzOffset = CurrentOffset;
		Container.Header.SpzSize = Container.SpzData.Num();
		CurrentOffset += Container.Header.SpzSize;

		// Section 2: Collider
		Container.Header.ColliderOffset = CurrentOffset;
		Container.Header.ColliderSize = Container.ColliderData.Num();
		CurrentOffset += Container.Header.ColliderSize;

		// Section 3: Metadata
		Container.Header.MetadataOffset = CurrentOffset;
		Container.Header.MetadataSize = static_cast<uint64>(MetadataUtf8Len);
		CurrentOffset += Container.Header.MetadataSize;

		// Section 4: Thumbnail
		uint32 SectionCount = 3;
		if (Container.ThumbnailData.Num() > 0)
		{
			Container.Header.ThumbnailOffset = CurrentOffset;
			Container.Header.ThumbnailSize = Container.ThumbnailData.Num();
			CurrentOffset += Container.Header.ThumbnailSize;
			SectionCount = 4;
		}
		else
		{
			Container.Header.ThumbnailOffset = 0;
			Container.Header.ThumbnailSize = 0;
		}

		// Section 5: Print 3D Package
		const bool bHasPrint = Container.Print3mfData.Num() > 0;
		if (bHasPrint)
		{
			Container.Header.Print3mfOffset = CurrentOffset;
			Container.Header.Print3mfSize = Container.Print3mfData.Num();
			CurrentOffset += Container.Header.Print3mfSize;
			++SectionCount;
		}
		else
		{
			Container.Header.Print3mfOffset = 0;
			Container.Header.Print3mfSize = 0;
		}
		Container.Header.SectionCount = SectionCount;

		// Unified v2.0 Format Flags
		Container.Header.Flags = PY3S_FLAG_SPZ_ZSTD;
		if (Container.Metadata.CollisionFormat.Equals(TEXT("fbx"), ESearchCase::IgnoreCase))
		{
			Container.Header.Flags |= PY3S_FLAG_COLLIDER_FBX;
		}
		else
		{
			Container.Header.Flags |= PY3S_FLAG_COLLIDER_GLB;
		}

		if (Container.Metadata.CollisionType.Contains(TEXT("convex"), ESearchCase::IgnoreCase)
			|| Container.Metadata.CollisionType.Contains(TEXT("coacd"), ESearchCase::IgnoreCase))
		{
			Container.Header.Flags |= PY3S_FLAG_COLLIDER_CONVEX;
		}
		if (bHasPrint)
		{
			Container.Header.Flags |= PY3S_FLAG_PRINT_3MF | PY3S_FLAG_MFG_PRINT3D_READY;
		}
		if (Container.Metadata.bHasPrintProfile)
		{
			Container.Header.Flags |= PY3S_FLAG_MFG_PRINT3D_READY;
		}
		if (Container.Metadata.bHasAiSystemPrompt)
		{
			Container.Header.Flags |= PY3S_FLAG_AI_SYSTEM_PROMPT;
		}
		if (Container.Metadata.bIsDehydratedSeed)
		{
			Container.Header.Flags |= PY3S_FLAG_STATE_DEHYDRATED_SEED | PY3S_FLAG_AUTO_HYDRATE_ON_MOUNT;
		}
		else if (Container.Metadata.bAutoHydrateOnMount)
		{
			Container.Header.Flags |= PY3S_FLAG_AUTO_HYDRATE_ON_MOUNT;
		}
		if (Container.Metadata.bHasPhysSkin)
		{
			Container.Header.Flags |= PY3S_FLAG_SIM_PHYSSKIN;
		}
		if (Container.Metadata.bHasMagneticMpm)
		{
			Container.Header.Flags |= PY3S_FLAG_SIM_MAGNETIC_MPM;
		}
		if (Container.Metadata.bHanumanParametricAi)
		{
			Container.Header.Flags |= PY3S_FLAG_HANUMAN_PARAMETRIC_AI;
		}
		if (bEnableIntegrity)
		{
			Container.Header.Flags |= PY3S_FLAG_INTEGRITY_CRC32;
		}

		// 3. Allocate and write payload into OutBuffer (Header CRC fields start at 0)
		OutBuffer.SetNumUninitialized(CurrentOffset);
		uint8* DestPtr = OutBuffer.GetData();

		// Write Header with CRC32 = 0 first
		FMemory::Memcpy(DestPtr, &Container.Header, sizeof(FPy3sFileHeader));

		// Write SPZ
		if (Container.Header.SpzSize > 0)
		{
			FMemory::Memcpy(DestPtr + Container.Header.SpzOffset, Container.SpzData.GetData(), Container.Header.SpzSize);
		}

		// Write Collider
		if (Container.Header.ColliderSize > 0)
		{
			FMemory::Memcpy(DestPtr + Container.Header.ColliderOffset, Container.ColliderData.GetData(), Container.Header.ColliderSize);
		}

		// Write Metadata UTF-8
		if (Container.Header.MetadataSize > 0)
		{
			FMemory::Memcpy(DestPtr + Container.Header.MetadataOffset, MetadataUtf8Ptr, Container.Header.MetadataSize);
		}

		// Write Thumbnail
		if (Container.Header.ThumbnailSize > 0)
		{
			FMemory::Memcpy(DestPtr + Container.Header.ThumbnailOffset, Container.ThumbnailData.GetData(), Container.Header.ThumbnailSize);
		}

		// Write Print 3D Package
		if (bHasPrint)
		{
			FMemory::Memcpy(DestPtr + Container.Header.Print3mfOffset, Container.Print3mfData.GetData(), Container.Header.Print3mfSize);
		}

		// 4. Compute and stamp IEEE 802.3 CRC-32 checksums at 0x60..0x67
		if (bEnableIntegrity)
		{
			const uint32 PrintCrc = bHasPrint
				? ComputePy3sCrc32(Container.Print3mfData.GetData(), Container.Print3mfData.Num())
				: 0u;
			const uint32 ContainerCrc = ComputeContainerCrc32(DestPtr, static_cast<int64>(CurrentOffset));
			Container.Header.ContainerCrc32 = ContainerCrc;
			Container.Header.Print3mfCrc32 = PrintCrc;
			FMemory::Memcpy(DestPtr + PY3S_CRC32_FIELD_OFFSET, &ContainerCrc, sizeof(uint32));
			FMemory::Memcpy(DestPtr + PY3S_CRC32_FIELD_OFFSET + sizeof(uint32), &PrintCrc, sizeof(uint32));
			Container.bIntegrityVerified = true;
		}

		return true;
	}

	bool FPy3sWriter::PackToFile(const FString& FilePath, FPy3sContainer& Container, bool bEnableIntegrity)
	{
		TArray<uint8> Buffer;
		if (!PackToBuffer(Container, Buffer, bEnableIntegrity))
		{
			return false;
		}
		return FFileHelper::SaveArrayToFile(Buffer, *FilePath);
	}

	bool FPy3sWriter::Pack(
		const FString& OutputFilePath,
		const uint8* SpzData, int64 SpzSize,
		const uint8* ColliderData, int64 ColliderSize,
		const FPy3sMetadata& Metadata,
		const uint8* ThumbnailData, int64 ThumbnailSize,
		const uint8* Print3mfData, int64 Print3mfSize,
		bool bEnableIntegrity)
	{
		FPy3sContainer Container;
		if (SpzData && SpzSize > 0)
		{
			Container.SpzData.Append(SpzData, SpzSize);
		}
		if (ColliderData && ColliderSize > 0)
		{
			Container.ColliderData.Append(ColliderData, ColliderSize);
		}
		Container.Metadata = Metadata;
		if (ThumbnailData && ThumbnailSize > 0)
		{
			Container.ThumbnailData.Append(ThumbnailData, ThumbnailSize);
		}
		if (Print3mfData && Print3mfSize > 0)
		{
			Container.Print3mfData.Append(Print3mfData, Print3mfSize);
		}

		return PackToFile(OutputFilePath, Container, bEnableIntegrity);
	}
}
