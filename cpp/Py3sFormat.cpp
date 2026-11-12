// Copyright 2026 PyGrassReal AI. All Rights Reserved.

#include "Py3sFormat.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"
#include "Serialization/JsonReader.h"
#include "Misc/DateTime.h"

namespace PyGrassReal
{
	FString FPy3sMetadata::ToJson() const
	{
		TSharedRef<FJsonObject> RootObject = MakeShared<FJsonObject>();

		RootObject->SetStringField(TEXT("format"), Format);
		RootObject->SetStringField(TEXT("version"), Version);
		RootObject->SetStringField(TEXT("generator"), Generator);
		RootObject->SetStringField(TEXT("created"), CreatedAt.IsEmpty() ? FDateTime::UtcNow().ToIso8601() : CreatedAt);

		// Asset
		TSharedRef<FJsonObject> AssetObject = MakeShared<FJsonObject>();
		AssetObject->SetStringField(TEXT("name"), AssetName);
		AssetObject->SetNumberField(TEXT("pointCount"), PointCount);

		TSharedRef<FJsonObject> BoundsObject = MakeShared<FJsonObject>();
		TArray<TSharedPtr<FJsonValue>> MinArr;
		MinArr.Add(MakeShared<FJsonValueNumber>(Bounds.Min.X));
		MinArr.Add(MakeShared<FJsonValueNumber>(Bounds.Min.Y));
		MinArr.Add(MakeShared<FJsonValueNumber>(Bounds.Min.Z));
		BoundsObject->SetArrayField(TEXT("min"), MinArr);

		TArray<TSharedPtr<FJsonValue>> MaxArr;
		MaxArr.Add(MakeShared<FJsonValueNumber>(Bounds.Max.X));
		MaxArr.Add(MakeShared<FJsonValueNumber>(Bounds.Max.Y));
		MaxArr.Add(MakeShared<FJsonValueNumber>(Bounds.Max.Z));
		BoundsObject->SetArrayField(TEXT("max"), MaxArr);

		AssetObject->SetObjectField(TEXT("bounds"), BoundsObject);
		RootObject->SetObjectField(TEXT("asset"), AssetObject);

		// Collision
		TSharedRef<FJsonObject> CollisionObject = MakeShared<FJsonObject>();
		CollisionObject->SetStringField(TEXT("format"), CollisionFormat);
		CollisionObject->SetNumberField(TEXT("vertexCount"), CollisionVertexCount);
		CollisionObject->SetNumberField(TEXT("faceCount"), CollisionFaceCount);
		CollisionObject->SetStringField(TEXT("type"), CollisionType);
		CollisionObject->SetBoolField(TEXT("enablePhysicsBounce"), bEnablePhysicsBounce);
		RootObject->SetObjectField(TEXT("collision"), CollisionObject);

		// Alignment
		TSharedRef<FJsonObject> AlignmentObject = MakeShared<FJsonObject>();
		AlignmentObject->SetNumberField(TEXT("scaleRatio"), ScaleRatio);
		TArray<TSharedPtr<FJsonValue>> RotArr;
		RotArr.Add(MakeShared<FJsonValueNumber>(AlignmentRotation.Pitch));
		RotArr.Add(MakeShared<FJsonValueNumber>(AlignmentRotation.Yaw));
		RotArr.Add(MakeShared<FJsonValueNumber>(AlignmentRotation.Roll));
		AlignmentObject->SetArrayField(TEXT("rotation"), RotArr);

		TArray<TSharedPtr<FJsonValue>> OffsetArr;
		OffsetArr.Add(MakeShared<FJsonValueNumber>(AlignmentOffset.X));
		OffsetArr.Add(MakeShared<FJsonValueNumber>(AlignmentOffset.Y));
		OffsetArr.Add(MakeShared<FJsonValueNumber>(AlignmentOffset.Z));
		AlignmentObject->SetArrayField(TEXT("offset"), OffsetArr);

		TArray<TSharedPtr<FJsonValue>> ScaleArr;
		ScaleArr.Add(MakeShared<FJsonValueNumber>(AlignmentScale.X));
		ScaleArr.Add(MakeShared<FJsonValueNumber>(AlignmentScale.Y));
		ScaleArr.Add(MakeShared<FJsonValueNumber>(AlignmentScale.Z));
		AlignmentObject->SetArrayField(TEXT("scale"), ScaleArr);

		RootObject->SetObjectField(TEXT("alignment"), AlignmentObject);

		// Rendering
		TSharedRef<FJsonObject> RenderObject = MakeShared<FJsonObject>();
		RenderObject->SetNumberField(TEXT("gamma"), Gamma);
		RenderObject->SetNumberField(TEXT("opacityCutoff"), OpacityCutoff);
		RenderObject->SetNumberField(TEXT("splatScale"), SplatScale);
		RootObject->SetObjectField(TEXT("rendering"), RenderObject);

		// v2.0 NASA Seed & Auto-Hydration Telemetry
		if (bIsDehydratedSeed)
		{
			RootObject->SetBoolField(TEXT("isSeed"), true);
			RootObject->SetBoolField(TEXT("dehydrated"), true);
		}
		if (bIsDehydratedSeed || bAutoHydrateOnMount)
		{
			TSharedRef<FJsonObject> TelemetryObj = MakeShared<FJsonObject>();
			TelemetryObj->SetBoolField(TEXT("isDehydratedSeed"), bIsDehydratedSeed);
			TelemetryObj->SetBoolField(TEXT("autoHydrateOnMount"), bIsDehydratedSeed || bAutoHydrateOnMount);
			RootObject->SetObjectField(TEXT("telemetryProfile"), TelemetryObj);
		}

		// v2.0 Wall/FEA Structural Preflight Audit
		if (!StructuralAuditStatus.IsEmpty())
		{
			TSharedRef<FJsonObject> AuditObj = MakeShared<FJsonObject>();
			AuditObj->SetStringField(TEXT("status"), StructuralAuditStatus);
			AuditObj->SetNumberField(TEXT("minWallMm"), MinWallMm);
			AuditObj->SetNumberField(TEXT("safetyFactor"), StructuralSafetyFactor);
			RootObject->SetObjectField(TEXT("structuralAudit"), AuditObj);
		}

		if (bHanumanParametricAi)
		{
			RootObject->SetBoolField(TEXT("hanumanParametric"), true);
		}

		FString OutputString;
		TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&OutputString);
		FJsonSerializer::Serialize(RootObject, Writer);
		return OutputString;
	}

	bool FPy3sMetadata::FromJson(const FString& JsonStr)
	{
		if (JsonStr.IsEmpty())
		{
			return false;
		}

		TSharedPtr<FJsonObject> RootObject;
		TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(JsonStr);
		if (!FJsonSerializer::Deserialize(Reader, RootObject) || !RootObject.IsValid())
		{
			return false;
		}

		RootObject->TryGetStringField(TEXT("format"), Format);
		RootObject->TryGetStringField(TEXT("version"), Version);
		RootObject->TryGetStringField(TEXT("generator"), Generator);
		RootObject->TryGetStringField(TEXT("created"), CreatedAt);

		// Asset
		const TSharedPtr<FJsonObject>* AssetObjPtr = nullptr;
		if (RootObject->TryGetObjectField(TEXT("asset"), AssetObjPtr) && AssetObjPtr->IsValid())
		{
			(*AssetObjPtr)->TryGetStringField(TEXT("name"), AssetName);
			(*AssetObjPtr)->TryGetNumberField(TEXT("pointCount"), PointCount);

			const TSharedPtr<FJsonObject>* BoundsObjPtr = nullptr;
			if ((*AssetObjPtr)->TryGetObjectField(TEXT("bounds"), BoundsObjPtr) && BoundsObjPtr->IsValid())
			{
				const TArray<TSharedPtr<FJsonValue>>* MinArrPtr = nullptr;
				if ((*BoundsObjPtr)->TryGetArrayField(TEXT("min"), MinArrPtr) && MinArrPtr->Num() >= 3)
				{
					Bounds.Min = FVector((*MinArrPtr)[0]->AsNumber(), (*MinArrPtr)[1]->AsNumber(), (*MinArrPtr)[2]->AsNumber());
				}
				const TArray<TSharedPtr<FJsonValue>>* MaxArrPtr = nullptr;
				if ((*BoundsObjPtr)->TryGetArrayField(TEXT("max"), MaxArrPtr) && MaxArrPtr->Num() >= 3)
				{
					Bounds.Max = FVector((*MaxArrPtr)[0]->AsNumber(), (*MaxArrPtr)[1]->AsNumber(), (*MaxArrPtr)[2]->AsNumber());
				}
				Bounds.IsValid = true;
			}
		}

		// Collision
		const TSharedPtr<FJsonObject>* ColObjPtr = nullptr;
		if (RootObject->TryGetObjectField(TEXT("collision"), ColObjPtr) && ColObjPtr->IsValid())
		{
			(*ColObjPtr)->TryGetStringField(TEXT("format"), CollisionFormat);
			(*ColObjPtr)->TryGetNumberField(TEXT("vertexCount"), CollisionVertexCount);
			(*ColObjPtr)->TryGetNumberField(TEXT("faceCount"), CollisionFaceCount);
			(*ColObjPtr)->TryGetStringField(TEXT("type"), CollisionType);
			(*ColObjPtr)->TryGetBoolField(TEXT("enablePhysicsBounce"), bEnablePhysicsBounce);
		}

		// Alignment
		const TSharedPtr<FJsonObject>* AlignObjPtr = nullptr;
		if (RootObject->TryGetObjectField(TEXT("alignment"), AlignObjPtr) && AlignObjPtr->IsValid())
		{
			AlignmentRotation = FRotator::ZeroRotator;
			AlignmentOffset = FVector::ZeroVector;
			AlignmentScale = FVector::OneVector;

			const TArray<TSharedPtr<FJsonValue>>* RotArrPtr = nullptr;
			if ((*AlignObjPtr)->TryGetArrayField(TEXT("rotation"), RotArrPtr) && RotArrPtr->Num() >= 3)
			{
				AlignmentRotation = FRotator(
					(*RotArrPtr)[0]->AsNumber(),
					(*RotArrPtr)[1]->AsNumber(),
					(*RotArrPtr)[2]->AsNumber()
				);
			}

			const TArray<TSharedPtr<FJsonValue>>* OffsetArrPtr = nullptr;
			if ((*AlignObjPtr)->TryGetArrayField(TEXT("offset"), OffsetArrPtr) && OffsetArrPtr->Num() >= 3)
			{
				AlignmentOffset = FVector(
					(*OffsetArrPtr)[0]->AsNumber(),
					(*OffsetArrPtr)[1]->AsNumber(),
					(*OffsetArrPtr)[2]->AsNumber()
				);
			}

			const TArray<TSharedPtr<FJsonValue>>* ScaleArrPtr = nullptr;
			if ((*AlignObjPtr)->TryGetArrayField(TEXT("scale"), ScaleArrPtr) && ScaleArrPtr->Num() >= 3)
			{
				AlignmentScale = FVector(
					(*ScaleArrPtr)[0]->AsNumber(),
					(*ScaleArrPtr)[1]->AsNumber(),
					(*ScaleArrPtr)[2]->AsNumber()
				);
			}

			double RatioVal = 1.0;
			if ((*AlignObjPtr)->TryGetNumberField(TEXT("scaleRatio"), RatioVal) && RatioVal > 0.0)
			{
				ScaleRatio = static_cast<float>(RatioVal);
			}
			else if (RootObject->TryGetNumberField(TEXT("scaleRatio"), RatioVal) && RatioVal > 0.0)
			{
				ScaleRatio = static_cast<float>(RatioVal);
			}
		}

		if (ScaleRatio <= 1.0f && JsonStr.Contains(TEXT("scaleRatio")))
		{
			int32 FoundIdx = JsonStr.Find(TEXT("scaleRatio"));
			if (FoundIdx != INDEX_NONE)
			{
				int32 ColonIdx = JsonStr.Find(TEXT(":"), ESearchCase::IgnoreCase, ESearchDir::FromStart, FoundIdx);
				if (ColonIdx != INDEX_NONE)
				{
					FString Sub = JsonStr.Mid(ColonIdx + 1, 32);
					float ParsedVal = FCString::Atof(*Sub);
					if (ParsedVal > 0.0f)
					{
						ScaleRatio = ParsedVal;
					}
				}
			}
		}

		// Rendering
		const TSharedPtr<FJsonObject>* RenderObjPtr = nullptr;
		if (RootObject->TryGetObjectField(TEXT("rendering"), RenderObjPtr) && RenderObjPtr->IsValid())
		{
			double Val = 0.0;
			if ((*RenderObjPtr)->TryGetNumberField(TEXT("gamma"), Val)) Gamma = static_cast<float>(Val);
			if ((*RenderObjPtr)->TryGetNumberField(TEXT("opacityCutoff"), Val)) OpacityCutoff = static_cast<float>(Val);
			if ((*RenderObjPtr)->TryGetNumberField(TEXT("splatScale"), Val)) SplatScale = static_cast<float>(Val);
		}

		// v2.0 NASA Seed, Print 3D, Structural Audit & AI/Simulation Feature Flags
		bool bSeedFlag = false;
		if (RootObject->TryGetBoolField(TEXT("isSeed"), bSeedFlag) && bSeedFlag)
		{
			bIsDehydratedSeed = true;
			bAutoHydrateOnMount = true;
		}
		bool bDehydratedFlag = false;
		if (RootObject->TryGetBoolField(TEXT("dehydrated"), bDehydratedFlag) && bDehydratedFlag)
		{
			bIsDehydratedSeed = true;
			bAutoHydrateOnMount = true;
		}

		const TSharedPtr<FJsonObject>* TelemetryObjPtr = nullptr;
		if (RootObject->TryGetObjectField(TEXT("telemetryProfile"), TelemetryObjPtr) && TelemetryObjPtr->IsValid())
		{
			bool bTempSeed = false;
			if ((*TelemetryObjPtr)->TryGetBoolField(TEXT("isDehydratedSeed"), bTempSeed) && bTempSeed)
			{
				bIsDehydratedSeed = true;
			}
			bool bTempHydrate = false;
			if ((*TelemetryObjPtr)->TryGetBoolField(TEXT("autoHydrateOnMount"), bTempHydrate) && bTempHydrate)
			{
				bAutoHydrateOnMount = true;
			}
		}

		bHasPrintProfile = RootObject->HasField(TEXT("printProfile")) || RootObject->HasField(TEXT("printing"));
		bHasAiSystemPrompt = RootObject->HasField(TEXT("systemPrompt"))
			|| RootObject->HasField(TEXT("agentPrompt"))
			|| RootObject->HasField(TEXT("aiAgentContext"));
		bHasPhysSkin = RootObject->HasField(TEXT("physSkin")) || RootObject->HasField(TEXT("phys_skin"));
		bHasMagneticMpm = RootObject->HasField(TEXT("magneticMpm")) || RootObject->HasField(TEXT("magnetic_mpm"));

		bool bHanuman = false;
		if (RootObject->TryGetBoolField(TEXT("hanumanParametric"), bHanuman) && bHanuman)
		{
			bHanumanParametricAi = true;
		}
		const TSharedPtr<FJsonObject>* AiCtxObjPtr = nullptr;
		if (RootObject->TryGetObjectField(TEXT("aiAgentContext"), AiCtxObjPtr) && AiCtxObjPtr->IsValid())
		{
			if ((*AiCtxObjPtr)->HasField(TEXT("orchestratedBy")))
			{
				bHanumanParametricAi = true;
			}
		}

		const TSharedPtr<FJsonObject>* AuditObjPtr = nullptr;
		if (RootObject->TryGetObjectField(TEXT("structuralAudit"), AuditObjPtr) && AuditObjPtr->IsValid())
		{
			(*AuditObjPtr)->TryGetStringField(TEXT("status"), StructuralAuditStatus);
			double WallVal = 0.0;
			if ((*AuditObjPtr)->TryGetNumberField(TEXT("minWallMm"), WallVal))
			{
				MinWallMm = static_cast<float>(WallVal);
			}
			double SfVal = 0.0;
			if ((*AuditObjPtr)->TryGetNumberField(TEXT("safetyFactor"), SfVal))
			{
				StructuralSafetyFactor = static_cast<float>(SfVal);
			}
		}

		return true;
	}
}

