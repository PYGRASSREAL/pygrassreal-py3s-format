// Copyright 2026 PyGrassReal AI. All Rights Reserved.

#include "Py3sReader.h"
#include "Misc/FileHelper.h"

namespace PyGrassReal
{
	bool FPy3sReader::IsPy3sBuffer(const uint8* Buffer, int64 BufferSize)
	{
		if (!Buffer || BufferSize < static_cast<int64>(sizeof(FPy3sFileHeader)))
		{
			return false;
		}

		return (Buffer[0] == 'P' && Buffer[1] == 'Y' && Buffer[2] == '3' && Buffer[3] == 'S');
	}

	bool FPy3sReader::UnpackFromBuffer(const uint8* Buffer, int64 BufferSize, FPy3sContainer& OutContainer)
	{
		if (!IsPy3sBuffer(Buffer, BufferSize))
		{
			UE_LOG(LogTemp, Error, TEXT("[PyGrassRealSpz] Buffer is not a valid PY3S format."));
			return false;
		}

		// 1. Read and validate Header
		FMemory::Memcpy(&OutContainer.Header, Buffer, sizeof(FPy3sFileHeader));

		if (OutContainer.Header.VersionMajor > PY3S_VERSION_MAJOR)
		{
			UE_LOG(LogTemp, Error, TEXT("[PyGrassRealSpz] Unsupported PY3S version: %u.%u (supported <= %u.%u)"),
				OutContainer.Header.VersionMajor, OutContainer.Header.VersionMinor,
				PY3S_VERSION_MAJOR, PY3S_VERSION_MINOR);
			return false;
		}

		// 2. Validate and extract Section 1: SPZ Payload
		OutContainer.SpzData.Empty();
		if (OutContainer.Header.SpzSize > 0)
		{
			if (OutContainer.Header.SpzOffset + OutContainer.Header.SpzSize > static_cast<uint64>(BufferSize))
			{
				UE_LOG(LogTemp, Error, TEXT("[PyGrassRealSpz] Corrupted PY3S: SPZ offset/size exceeds buffer bounds."));
				return false;
			}
			OutContainer.SpzData.SetNumUninitialized(OutContainer.Header.SpzSize);
			FMemory::Memcpy(OutContainer.SpzData.GetData(), Buffer + OutContainer.Header.SpzOffset, OutContainer.Header.SpzSize);
		}

		// 3. Validate and extract Section 2: Collider Payload
		OutContainer.ColliderData.Empty();
		if (OutContainer.Header.ColliderSize > 0)
		{
			if (OutContainer.Header.ColliderOffset + OutContainer.Header.ColliderSize > static_cast<uint64>(BufferSize))
			{
				UE_LOG(LogTemp, Error, TEXT("[PyGrassRealSpz] Corrupted PY3S: Collider offset/size exceeds buffer bounds."));
				return false;
			}
			OutContainer.ColliderData.SetNumUninitialized(OutContainer.Header.ColliderSize);
			FMemory::Memcpy(OutContainer.ColliderData.GetData(), Buffer + OutContainer.Header.ColliderOffset, OutContainer.Header.ColliderSize);
		}

		// 4. Validate and extract Section 3: Metadata JSON
		OutContainer.MetadataJson.Empty();
		if (OutContainer.Header.MetadataSize > 0)
		{
			if (OutContainer.Header.MetadataOffset + OutContainer.Header.MetadataSize > static_cast<uint64>(BufferSize))
			{
				UE_LOG(LogTemp, Error, TEXT("[PyGrassRealSpz] Corrupted PY3S: Metadata offset/size exceeds buffer bounds."));
				return false;
			}
			const char* Utf8Ptr = reinterpret_cast<const char*>(Buffer + OutContainer.Header.MetadataOffset);
			FUTF8ToTCHAR TCharConverter(Utf8Ptr, OutContainer.Header.MetadataSize);
			OutContainer.MetadataJson = FString(TCharConverter.Get());
			OutContainer.Metadata.FromJson(OutContainer.MetadataJson);
		}

		// 5. Validate and extract Section 4: Thumbnail
		OutContainer.ThumbnailData.Empty();
		if (OutContainer.Header.ThumbnailSize > 0 && OutContainer.Header.ThumbnailOffset > 0)
		{
			if (OutContainer.Header.ThumbnailOffset + OutContainer.Header.ThumbnailSize <= static_cast<uint64>(BufferSize))
			{
				OutContainer.ThumbnailData.SetNumUninitialized(OutContainer.Header.ThumbnailSize);
				FMemory::Memcpy(OutContainer.ThumbnailData.GetData(), Buffer + OutContainer.Header.ThumbnailOffset, OutContainer.Header.ThumbnailSize);
			}
		}

		UE_LOG(LogTemp, Log, TEXT("[PyGrassRealSpz] Successfully unpacked PY3S: SPZ=%lld B, Collider=%lld B, Metadata=%lld B"),
			OutContainer.Header.SpzSize, OutContainer.Header.ColliderSize, OutContainer.Header.MetadataSize);

		return true;
	}

	bool FPy3sReader::UnpackFromFile(const FString& FilePath, FPy3sContainer& OutContainer)
	{
		TArray<uint8> Buffer;
		if (!FFileHelper::LoadFileToArray(Buffer, *FilePath))
		{
			UE_LOG(LogTemp, Error, TEXT("[PyGrassRealSpz] Failed to read PY3S file: %s"), *FilePath);
			return false;
		}

		return UnpackFromBuffer(Buffer.GetData(), Buffer.Num(), OutContainer);
	}
}
