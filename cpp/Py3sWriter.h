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
		 * Packs in-memory container contents into a single .py3s binary buffer.
		 * Updates container Header offsets and sizes accurately.
		 */
		static bool PackToBuffer(FPy3sContainer& Container, TArray<uint8>& OutBuffer);

		/**
		 * Packs in-memory container and writes directly to disk (.py3s).
		 */
		static bool PackToFile(const FString& FilePath, FPy3sContainer& Container);

		/**
		 * Quick helper to pack separate raw buffers into a .py3s file.
		 */
		static bool Pack(
			const FString& OutputFilePath,
			const uint8* SpzData, int64 SpzSize,
			const uint8* ColliderData, int64 ColliderSize,
			const FPy3sMetadata& Metadata,
			const uint8* ThumbnailData = nullptr, int64 ThumbnailSize = 0
		);
	};
}
