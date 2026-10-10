// Copyright 2026 PyGrassReal AI. All Rights Reserved.

#include "Py3sWriter.h"
#include "Misc/FileHelper.h"

namespace PyGrassReal
{
	bool FPy3sWriter::PackToBuffer(FPy3sContainer& Container, TArray<uint8>& OutBuffer)
	{
		// 1. Prepare Metadata JSON string
		if (Container.MetadataJson.IsEmpty())
		{
			Container.MetadataJson = Container.Metadata.ToJson();
		}

		FTCHARToUTF8 Utf8Converter(*Container.MetadataJson);
		const uint8* MetadataUtf8Ptr = reinterpret_cast<const uint8*>(Utf8Converter.Get());
		int64 MetadataUtf8Len = Utf8Converter.Length();

		// 2. Setup Header offsets & sizes
		constexpr uint64 HeaderSize = sizeof(FPy3sFileHeader); // 128 bytes
		uint64 CurrentOffset = HeaderSize;

		Container.Header = FPy3sFileHeader();

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
		Container.Header.MetadataSize = MetadataUtf8Len;
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
		Container.Header.SectionCount = SectionCount;

		// Format Flags
		Container.Header.Flags = PY3S_FLAG_SPZ_ZSTD;
		if (Container.Metadata.CollisionFormat.Equals(TEXT("fbx"), ESearchCase::IgnoreCase))
		{
			Container.Header.Flags |= PY3S_FLAG_COLLIDER_FBX;
		}
		else
		{
			Container.Header.Flags |= PY3S_FLAG_COLLIDER_GLB;
		}

		// 3. Allocate and write payload into OutBuffer
		OutBuffer.SetNumUninitialized(CurrentOffset);
		uint8* DestPtr = OutBuffer.GetData();

		// Write Header
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

		return true;
	}

	bool FPy3sWriter::PackToFile(const FString& FilePath, FPy3sContainer& Container)
	{
		TArray<uint8> Buffer;
		if (!PackToBuffer(Container, Buffer))
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
		const uint8* ThumbnailData, int64 ThumbnailSize)
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

		return PackToFile(OutputFilePath, Container);
	}
}
