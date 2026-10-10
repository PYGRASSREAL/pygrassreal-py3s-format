// Copyright 2026 PyGrassReal AI. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "Py3sFormat.h"

namespace PyGrassReal
{
	class PYGRASSREALSPZ_API FPy3sReader
	{
	public:
		/**
		 * Quickly checks whether a memory buffer begins with the "PY3S" magic header.
		 */
		static bool IsPy3sBuffer(const uint8* Buffer, int64 BufferSize);

		/**
		 * Unpacks a in-memory .py3s binary buffer into a structured FPy3sContainer.
		 */
		static bool UnpackFromBuffer(const uint8* Buffer, int64 BufferSize, FPy3sContainer& OutContainer);

		/**
		 * Loads a .py3s file from disk and unpacks it into OutContainer.
		 */
		static bool UnpackFromFile(const FString& FilePath, FPy3sContainer& OutContainer);
	};
}
