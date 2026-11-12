// Copyright 2026 PyGrassReal AI. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "Py3sFormat.h"

namespace PyGrassReal
{
	class PYGRASSREALSPZ_API FPy3sWriter
	{
	public:
		/**
		 * Packs in-memory container contents into a single Unified v2.0 .py3s binary buffer
		 * with IEEE 802.3 CRC-32 checksums (ContainerCrc32 at 0x60 & Print3mfCrc32 at 0x64).
		 */
		static bool PackToBuffer(FPy3sContainer& Container, TArray<uint8>& OutBuffer, bool bEnableIntegrity = true);

		/**
		 * Packs in-memory container and writes directly to disk (.py3s).
		 */
		static bool PackToFile(const FString& FilePath, FPy3sContainer& Container, bool bEnableIntegrity = true);

		/**
		 * Quick helper to pack separate raw buffers into a v2.0 .py3s file.
		 */
		static bool Pack(
			const FString& OutputFilePath,
			const uint8* SpzData, int64 SpzSize,
			const uint8* ColliderData, int64 ColliderSize,
			const FPy3sMetadata& Metadata,
			const uint8* ThumbnailData = nullptr, int64 ThumbnailSize = 0,
			const uint8* Print3mfData = nullptr, int64 Print3mfSize = 0,
			bool bEnableIntegrity = true
		);
	};
}
