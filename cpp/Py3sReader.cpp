// Copyright 2026 PyGrassReal AI. All Rights Reserved.

#include "Py3sReader.h"
#include "Misc/FileHelper.h"

namespace PyGrassReal
{
	namespace
	{
		struct FPy3sSectionSpan
		{
			uint64 Start = 0;
			uint64 End = 0;
		};

		bool IsValidSectionRange(uint64 Offset, uint64 Size, uint64 TotalSize)
		{
			if (Size == 0)
			{
				return true;
			}
			return Offset >= static_cast<uint64>(PY3S_HEADER_SIZE)
				&& Offset <= TotalSize
				&& Size <= TotalSize - Offset;
		}
	}

	bool FPy3sReader::IsPy3sBuffer(const uint8* Buffer, int64 BufferSize)
	{
		if (!Buffer || BufferSize < static_cast<int64>(sizeof(FPy3sFileHeader)))
		{
			return false;
		}

		return (Buffer[0] == 'P' && Buffer[1] == 'Y' && Buffer[2] == '3' && Buffer[3] == 'S');
	}

	bool FPy3sReader::VerifyCrc32(const uint8* Buffer, int64 BufferSize)
	{
		if (!IsPy3sBuffer(Buffer, BufferSize))
		{
			return false;
		}

		FPy3sFileHeader Header;
		FMemory::Memcpy(&Header, Buffer, sizeof(FPy3sFileHeader));
		if ((Header.Flags & PY3S_FLAG_INTEGRITY_CRC32) == 0)
		{
			return false;
		}

		const uint32 ActualContainerCrc = ComputeContainerCrc32(Buffer, BufferSize);
		if (ActualContainerCrc != Header.ContainerCrc32)
		{
			return false;
		}

		const bool bHasPrint = (Header.Flags & PY3S_FLAG_PRINT_3MF) != 0;
		if (bHasPrint && Header.Print3mfSize > 0)
		{
			const uint64 TotalSize = static_cast<uint64>(BufferSize);
			if (!IsValidSectionRange(Header.Print3mfOffset, Header.Print3mfSize, TotalSize))
			{
				return false;
			}
			const uint32 ActualPrintCrc = ComputePy3sCrc32(
				Buffer + Header.Print3mfOffset,
				static_cast<int64>(Header.Print3mfSize)
			);
			if (ActualPrintCrc != Header.Print3mfCrc32)
			{
				return false;
			}
		}

		return true;
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
		OutContainer.bIntegrityVerified = false;

		if (OutContainer.Header.VersionMajor > PY3S_VERSION_MAJOR)
		{
			UE_LOG(LogTemp, Error, TEXT("[PyGrassRealSpz] Unsupported PY3S version: %u.%u (supported <= %u.%u)"),
				OutContainer.Header.VersionMajor, OutContainer.Header.VersionMinor,
				PY3S_VERSION_MAJOR, PY3S_VERSION_MINOR);
			return false;
		}

		const uint64 TotalSize = static_cast<uint64>(BufferSize);
		const bool bHasPrintFlag = (OutContainer.Header.Flags & PY3S_FLAG_PRINT_3MF) != 0;
		const uint64 PrintOff = bHasPrintFlag ? OutContainer.Header.Print3mfOffset : 0;
		const uint64 PrintSz = bHasPrintFlag ? OutContainer.Header.Print3mfSize : 0;

		if (bHasPrintFlag && PrintSz == 0)
		{
			UE_LOG(LogTemp, Error, TEXT("[PyGrassRealSpz] Corrupted PY3S: missing Print 3D payload for PY3S_FLAG_PRINT_3MF."));
			return false;
		}

		const uint64 Offsets[5] = {
			OutContainer.Header.SpzOffset,
			OutContainer.Header.ColliderOffset,
			OutContainer.Header.MetadataOffset,
			OutContainer.Header.ThumbnailOffset,
			PrintOff
		};
		const uint64 Sizes[5] = {
			OutContainer.Header.SpzSize,
			OutContainer.Header.ColliderSize,
			OutContainer.Header.MetadataSize,
			OutContainer.Header.ThumbnailSize,
			PrintSz
		};

		FPy3sSectionSpan Spans[5];
		int32 SpanCount = 0;
		for (int32 i = 0; i < 5; ++i)
		{
			if (Sizes[i] > 0)
			{
				if (!IsValidSectionRange(Offsets[i], Sizes[i], TotalSize))
				{
					UE_LOG(LogTemp, Error, TEXT("[PyGrassRealSpz] Corrupted PY3S: section range %d exceeds bounds."), i + 1);
					return false;
				}
				Spans[SpanCount++] = { Offsets[i], Offsets[i] + Sizes[i] };
			}
		}

		for (int32 i = 0; i < SpanCount - 1; ++i)
		{
			for (int32 j = i + 1; j < SpanCount; ++j)
			{
				if (Spans[j].Start < Spans[i].Start)
				{
					const FPy3sSectionSpan Temp = Spans[i];
					Spans[i] = Spans[j];
					Spans[j] = Temp;
				}
			}
		}
		for (int32 i = 1; i < SpanCount; ++i)
		{
			if (Spans[i].Start < Spans[i - 1].End)
			{
				UE_LOG(LogTemp, Error, TEXT("[PyGrassRealSpz] Corrupted PY3S: overlapping binary sections."));
				return false;
			}
		}

		if (OutContainer.Header.MetadataSize > static_cast<uint64>(PY3S_MAX_METADATA_BYTES))
		{
			UE_LOG(LogTemp, Error, TEXT("[PyGrassRealSpz] Rejected PY3S: metadata size exceeds 8 MB safety limit."));
			return false;
		}

		const bool bHasIntegrity = (OutContainer.Header.Flags & PY3S_FLAG_INTEGRITY_CRC32) != 0;
		if (bHasIntegrity)
		{
			const uint32 ActualContainerCrc = ComputeContainerCrc32(Buffer, BufferSize);
			if (ActualContainerCrc != OutContainer.Header.ContainerCrc32)
			{
				UE_LOG(LogTemp, Error, TEXT("[PyGrassRealSpz] PY3S integrity check failed: ContainerCrc32 mismatch (expected %u, got %u)."),
					OutContainer.Header.ContainerCrc32, ActualContainerCrc);
				return false;
			}
		}

		// 2. Validate and extract Section 1: SPZ Payload
		OutContainer.SpzData.Empty();
		if (OutContainer.Header.SpzSize > 0)
		{
			OutContainer.SpzData.SetNumUninitialized(OutContainer.Header.SpzSize);
			FMemory::Memcpy(OutContainer.SpzData.GetData(), Buffer + OutContainer.Header.SpzOffset, OutContainer.Header.SpzSize);
		}

		// 3. Validate and extract Section 2: Collider Payload
		OutContainer.ColliderData.Empty();
		if (OutContainer.Header.ColliderSize > 0)
		{
			OutContainer.ColliderData.SetNumUninitialized(OutContainer.Header.ColliderSize);
			FMemory::Memcpy(OutContainer.ColliderData.GetData(), Buffer + OutContainer.Header.ColliderOffset, OutContainer.Header.ColliderSize);
		}

		// 4. Validate and extract Section 3: Metadata JSON
		OutContainer.MetadataJson.Empty();
		if (OutContainer.Header.MetadataSize > 0)
		{
			const char* Utf8Ptr = reinterpret_cast<const char*>(Buffer + OutContainer.Header.MetadataOffset);
			FUTF8ToTCHAR TCharConverter(Utf8Ptr, static_cast<int32>(OutContainer.Header.MetadataSize));
			OutContainer.MetadataJson = FString(TCharConverter.Length(), TCharConverter.Get());
			OutContainer.Metadata.FromJson(OutContainer.MetadataJson);
		}

		// 5. Validate and extract Section 4: Thumbnail
		OutContainer.ThumbnailData.Empty();
		if (OutContainer.Header.ThumbnailSize > 0 && OutContainer.Header.ThumbnailOffset > 0)
		{
			OutContainer.ThumbnailData.SetNumUninitialized(OutContainer.Header.ThumbnailSize);
			FMemory::Memcpy(OutContainer.ThumbnailData.GetData(), Buffer + OutContainer.Header.ThumbnailOffset, OutContainer.Header.ThumbnailSize);
		}

		// 6. Validate and extract Section 5: Print 3D Package
		OutContainer.Print3mfData.Empty();
		if (PrintSz > 0)
		{
			if (bHasIntegrity)
			{
				const uint32 ActualPrintCrc = ComputePy3sCrc32(Buffer + PrintOff, static_cast<int64>(PrintSz));
				if (ActualPrintCrc != OutContainer.Header.Print3mfCrc32)
				{
					UE_LOG(LogTemp, Error, TEXT("[PyGrassRealSpz] PY3S integrity check failed: Print3mfCrc32 mismatch."));
					return false;
				}
			}
			OutContainer.Print3mfData.SetNumUninitialized(PrintSz);
			FMemory::Memcpy(OutContainer.Print3mfData.GetData(), Buffer + PrintOff, PrintSz);
		}

		OutContainer.bIntegrityVerified = bHasIntegrity;

		UE_LOG(LogTemp, Log, TEXT("[PyGrassRealSpz] Successfully unpacked PY3S v%u.%u (CRC32=%s): SPZ=%llu B, Collider=%llu B, Print=%llu B"),
			OutContainer.Header.VersionMajor, OutContainer.Header.VersionMinor,
			bHasIntegrity ? TEXT("PASS") : TEXT("LEGACY"),
			OutContainer.Header.SpzSize, OutContainer.Header.ColliderSize, PrintSz);

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
