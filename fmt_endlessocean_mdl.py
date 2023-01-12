from inc_noesis import *

# If you need a script that parses the materials and more, but not the skeleton data, visit https://github.com/NiV-L-A/Endless-Ocean-Files-Converter

#///////////////////////////////////////////////////////////////////////
#
# Endless Ocean 1 & 2 .mdl Noesis Plugin
# Version: 0.1
# GitHub: https://github.com/NiV-L-A/fmt_endlessocean_mdl
# Author: NiV-L-A
# Special thanks to Hiroshi, Joschka and the people at the XeNTaX discord server
# *If you have any issues, join this discord server and contact NiV-L-A: https://discord.gg/4hmcsmPMDG - Endless Ocean Wiki Server
#
#///////////////////////////////////////////////////////////////////////
#
# Table Of Contents:
# (1) Changelog
# (2) Notes
# (3) Settings
#
#///////////////////////////////////////////////////////////////////////
#
# (1) Changelog
#
# Version 0.1 (12/01/2023)
#	- Initial Version
#
#///////////////////////////////////////////////////////////////////////
#
# (2) Notes
#
# !!! Mainly written to understand how the skeleton and the animations work !!!
#	The script is intended to be used for .mdl that have skeleton data.
#	Can load most skeletons and most animations.
#	Loading .mdl files that do not have skeleton data will either give an error or result in an incorrect parsing.
#		If you need a script that parses the materials and more, but not the skeleton data, visit https://github.com/NiV-L-A/Endless-Ocean-Files-Converter
# The values in MOT.Data.TRSPoseValues seems to not be read by the game. Breakpoints do not get hit and changing the values in GAME.DAT does not seem to cause any effect.
#
#///////////////////////////////////////////////////////////////////////
#
# (3) Settings
#							#Default value and description:
FlipWeights				= 1 #1 - Flip sign bit of the first weight for each vertex, if negative.
LoadAnim				= 1 #1 - Loads animation
LoadAnimTrans			= 1 #1 - Loads the animation's translation channel
LoadAnimRot				= 1 #1 - Loads the animation's rotation channel
LoadAnimScale			= 1 #1 - Loads the animation's scale channel

PrintMeshCount			= 0 #0 - Prints the mesh count
PrintMOTCount			= 0 #0 - Prints the .mot (animations) count
PrintAnimInfo			= 0 #0 - Prints information about each animation
PrintFinalWeightsIdx	= 0 #0 - Prints, as an array of bytes, the remapped weights indices
PrintFinalBones			= 0 #0 - Prints a list of the bones. Index, name, parent name, matrix
PrintAnimBones			= 0 #0 - Prints information about each bone for each animation
#
#///////////////////////////////////////////////////////////////////////

# global variables:
# global VDLOffLocal
# global MD2
# global MD3
# global HiListType
# global MOLOffLocal
# global MOTOffLocal

def registerNoesisTypes():
	handle = noesis.register("Endless Ocean 1 & 2", ".mdl")
	noesis.setHandlerTypeCheck(handle, noepyCheckType)
	noesis.logPopup()
	noesis.setHandlerLoadModel(handle, noepyLoadModel)
	return 1
	
def noepyCheckType(data):
	return 1

def noepyLoadModel(data, mdlList):
	print("")
	ctx = rapi.rpgCreateContext()
	bs = NoeBitStream(data, NOE_LITTLEENDIAN)
	rapi.rpgSetOption(noesis.RPGOPT_TRIWINDBACKWARD,1)
	rapi.rpgSetOption(noesis.RPGOPT_BIGENDIAN,1)
	Header = Header_t(bs)
	MOLFound = 0
	bones = []
	animationList = []
	PName = ""
	if PrintMeshCount == 1:
		print("MeshCount: " + str(Header.CountsOffs.MeshCount))
	if PrintMOTCount == 1:
		print("MOTCount: " + str(Header.CountsOffs.MotFilesCount))
	for i in range(0, Header.RFHeader.FileCount):
		if Header.RFHeader.Files[i].IsInFile == 1:
			if Header.RFHeader.Files[i].FileType == 0:
				VDL = ParseVDL(bs, Header.RFHeader.Files[i], Header.CountsOffs.ObjectsCount, Header.CountsOffs.MeshCount, Header.MeshInfo)
			elif Header.RFHeader.Files[i].FileType == 7:
				MOL = ParseMOL(bs, Header.RFHeader.Files[i])
				MOLFound = 1
				
	#Flip sign bit of the first weight for each vertex, if negative. 0b10000000
	if FlipWeights == 1:
		for i in range(0, Header.CountsOffs.MeshCount):
			if Header.MeshInfo[i].MeshType == 0x50:
				for j in range(0, VDL.Mesh[i].SkelData.Header.VtxCount):
					if (VDL.Mesh[i].SkelData.Weights[j * 0x10] & 0x80) == 0x80:
						VDL.Mesh[i].SkelData.Weights[j * 0x10] ^= 0x80
					
	#Swap obj's mat43 with bone's mat43. todo: optimize it to only do *that* bone once
	for i in range(0, Header.CountsOffs.MeshCount):
		if Header.MeshInfo[i].MeshType == 0x50:
			for j in range(0, Header.MeshInfo[i].BoneCount):
				CurrBoneName = VDL.Mesh[i].SkelData.Bones[j]
				index = next((k for k, item in enumerate(VDL.HiList.Object) if item.Name == CurrBoneName), None)
				if index != None:
					VDL.HiList.Object[index].Mat43 = VDL.Mesh[i].SkelData.Mat[j]

	#Get PName and create bones
	for i in range(0, Header.CountsOffs.ObjectsCount):
		CurrPrevObjID = VDL.HiList.Object[i].PrevObjID
		if CurrPrevObjID != -1:
			PName = VDL.HiList.Object[CurrPrevObjID].Name
		bones.append(NoeBone(i, VDL.HiList.Object[i].Name, VDL.HiList.Object[i].Mat43, PName, None))
	
	#WeightsIdx remap
	for i in range(0, Header.CountsOffs.MeshCount):
		if Header.MeshInfo[i].MeshType == 0x50:
			WeightRemapDict = {}
			for WIdx in VDL.Mesh[i].SkelData.WeightsIdx:
				if WIdx not in WeightRemapDict and WIdx != 0xFF:
					idx = next((index for (index, d) in enumerate(bones) if d.name == VDL.Mesh[i].SkelData.Bones[WIdx]), None)
					WeightRemapDict.update({WIdx:idx})
			for j in range(0, len(VDL.Mesh[i].SkelData.WeightsIdx)):
				curr = VDL.Mesh[i].SkelData.WeightsIdx[j]
				if curr == 0xFF or WeightRemapDict[curr] == None:
					continue
				VDL.Mesh[i].SkelData.WeightsIdx[j] = WeightRemapDict[curr]

	#PrintFinalBones
	if PrintFinalBones == 1:
		print("FinalBones:")
		for i in range(0, len(bones)):
			print(bones[i].index, bones[i].name, bones[i].parentName)
			PrintRoundMat43(bones[i].getMatrix())
			print("")
	
	#PrintFinalWeightsIdx
	if PrintFinalWeightsIdx == 1:
		print("PrintFinalWeightsIdx")
		for i in range(0, Header.CountsOffs.MeshCount):
			print("Mesh:", i)
			PrintHexArray2(VDL.Mesh[i].SkelData.WeightsIdx)
		
	#Binds
	for i in range(0, Header.CountsOffs.MeshCount):
		if Header.MeshInfo[i].MeshType == 0x50:
			rapi.rpgBindBoneIndexBufferOfs(VDL.Mesh[i].SkelData.WeightsIdx,noesis.RPGEODATA_UBYTE, 4, 0, 4)
			rapi.rpgBindBoneWeightBufferOfs(VDL.Mesh[i].SkelData.Weights, noesis.RPGEODATA_FLOAT, 0x10, 0, 4)
		rapi.rpgBindPositionBufferOfs(VDL.Mesh[i].MeshData.VtxBuff, noesis.RPGEODATA_FLOAT, VDL.Mesh[i].MeshHeader.VtxStride, 0)
		for j in range(0, Header.MeshInfo[i].IdxSectionsCount): #For every index section
			for k in range(0, len(VDL.Mesh[i].MeshData.Indices[j].Idxs)): #For every draw call
				cnt = VDL.Mesh[i].MeshData.Indices[j].cntList[k]
				VDL.Mesh[i].MeshData.Indices[j].Idxs[k] = noesis.deinterleaveBytes(VDL.Mesh[i].MeshData.Indices[j].Idxs[k], 0, VDL.Mesh[i].MeshHeader.VtxIndex - 1, VDL.Mesh[i].MeshData.FragmentSize)
				if VDL.Mesh[i].MeshHeader.VtxIndex == 3:
					if Header.MeshInfo[i].InfoIdx[j].Optimization == 4:
						rapi.rpgCommitTriangles(VDL.Mesh[i].MeshData.Indices[j].Idxs[k], noesis.RPGEODATA_USHORT, cnt, noesis.RPGEO_TRIANGLE_STRIP, 1)
					else:
						rapi.rpgCommitTriangles(VDL.Mesh[i].MeshData.Indices[j].Idxs[k], noesis.RPGEODATA_USHORT, cnt, noesis.RPGEO_TRIANGLE, 1)
				else:
					if Header.MeshInfo[i].InfoIdx[j].Optimization == 4:
						rapi.rpgCommitTriangles(VDL.Mesh[i].MeshData.Indices[j].Idxs[k], noesis.RPGEODATA_UBYTE, cnt, noesis.RPGEO_TRIANGLE_STRIP, 1)
					else:
						rapi.rpgCommitTriangles(VDL.Mesh[i].MeshData.Indices[j].Idxs[k], noesis.RPGEODATA_UBYTE, cnt, noesis.RPGEO_TRIANGLE, 1)
	
	#Animation
	if LoadAnim == 1 and MOLFound == 1:
		if PrintAnimInfo == 1:
			print("PrintAnimInfo")
		for i in range(0, MOL.CountsOffs.MOTFilesCount):
			if PrintAnimInfo == 1:
				print("MOT", i, "\t" + str(MOL.RFHeader.Files[i].FileName))
			if MOL.RFHeader.Files[i].IsInFile == 0:
				print("MOT", i, "\t", MOL.RFHeader.Files[i].FileName, "\tnot in file, ignoring...")
				continue
			MOT = ParseMOT(bs, MOL.RFHeader.Files[i], MOL, i)
			if PrintAnimInfo == 1:
				print("\tLength in frames:", MOT.Header.LenInFrames, "\tBoneCount:", MOT.Header.BoneCount)
				print("\tBoneTransCount:", MOT.Header.BoneTransCount, "\tKeyFramesTransCount:", MOT.Header.KeyFramesTransCount)
				print("\tBoneRotCount:", MOT.Header.BoneRotCount, "\t\tKeyFramesRotCount:", MOT.Header.KeyFramesRotCount)
				print("\tBoneScaleCount:", MOT.Header.BoneScaleCount, "\t\tKeyFramesScaleCount:", MOT.Header.KeyFramesScaleCount)
			if PrintAnimBones == 1:
				print("PrintAnimBones")
			BoneRemapToHiListIDDict = {}
			BoneIdxsDict = {}
			keyFramedBoneList = []
			Count = 0
			#Swap local MOL bone ID with HiList's ID.
			#Get Count for each *used* bone (thanks arika)
			for j in range(0, MOT.Header.BoneCount):
				CurrIdx = MOL.MOTInfo[i].BoneRemap[j]
				if CurrIdx in BoneRemapToHiListIDDict: #not present, skip
					continue
				CurrBoneName = MOL.Bones[CurrIdx]
				idx = next((index for (index, d) in enumerate(bones) if d.name == CurrBoneName), None)
				BoneRemapToHiListIDDict.update({CurrIdx:idx})
				BoneIdxsDict.update({Count:CurrIdx})
				if idx == None: #duplicates, skip
					continue
				Count += 1
				keyFramedBoneList.append(NoeKeyFramedBone(idx))
			#For every bone
			for j in range(0, MOT.Header.BoneCount):
				posNoeKeyFramedValues = []
				rotNoeKeyFramedValues = []
				scaleNoeKeyFramedValues = []
				CurrIdxBoneRemap = MOL.MOTInfo[i].BoneRemap[j]
				CurrIdxIdx = MOL.MOTInfo[i].Idx[CurrIdxBoneRemap]
				CurrTRSPoseIdxID = MOT.Data.TRSPoseIdx[CurrIdxIdx].ID
				CurrHiListID = BoneRemapToHiListIDDict.get(CurrIdxBoneRemap)
				if CurrHiListID == None:
					if PrintAnimBones == 1:
						print("Bone not found, ignoring: ", MOL.Bones[CurrIdxBoneRemap])
					continue
				if PrintAnimBones == 1:
					print("BoneName:", MOL.Bones[CurrIdxBoneRemap])
					print("\tIdxBoneRemap:", hex(CurrIdxBoneRemap))
					print("\tkeyFramedBoneList[x]:", hex(list(BoneIdxsDict.keys())[list(BoneIdxsDict.values()).index(CurrIdxBoneRemap)]))
					print("\tCurrIdxIdx:", hex(CurrIdxIdx))
					print("\tCurrTRSPoseIdxID:", hex(CurrTRSPoseIdxID))
					print("\tCurrHiListID:", hex(CurrHiListID))
				if (CurrTRSPoseIdxID & 1) == 1: #Bone has translation channel
					if LoadAnimTrans == 1 and MOL.SemanticFlags[CurrIdxBoneRemap] & 0x10 == 0x10: #Confirmation
						for k in range(0, MOT.Header.KeyFramesTransCount):
							posNoeKeyFramedValues.append(NoeKeyFramedValue(MOT.Data.TransKeyFrames[k],MOT.Data.Trans[k + MOT.Data.TRSPoseIdx[MOL.MOTInfo[i].Idx[MOL.MOTInfo[i].BoneRemap[j]]].Trans]))
						keyFramedBoneList[list(BoneIdxsDict.keys())[list(BoneIdxsDict.values()).index(CurrIdxBoneRemap)]].setTranslation(posNoeKeyFramedValues, noesis.NOEKF_TRANSLATION_VECTOR_3)
					MOT.Data.TRSPoseIdx[MOL.MOTInfo[i].Idx[MOL.MOTInfo[i].BoneRemap[j]]].ID -= 1
				elif (CurrTRSPoseIdxID & 2) == 2: #Bone has rotation channel
					if LoadAnimRot == 1 and MOL.SemanticFlags[CurrIdxBoneRemap] & 0x20 == 0x20: #Confirmation
						for k in range(0, MOT.Header.KeyFramesRotCount):
							rotNoeKeyFramedValues.append(NoeKeyFramedValue(MOT.Data.RotKeyFrames[k], MOT.Data.Rot[k + MOT.Data.TRSPoseIdx[MOL.MOTInfo[i].Idx[MOL.MOTInfo[i].BoneRemap[j]]].Rot]))
						keyFramedBoneList[list(BoneIdxsDict.keys())[list(BoneIdxsDict.values()).index(CurrIdxBoneRemap)]].setRotation(rotNoeKeyFramedValues, noesis.NOEKF_ROTATION_QUATERNION_4)
					MOT.Data.TRSPoseIdx[MOL.MOTInfo[i].Idx[MOL.MOTInfo[i].BoneRemap[j]]].ID -= 2
				elif (CurrTRSPoseIdxID & 4) == 4: #Bone has scale channel
					if LoadAnimScale == 1 and MOL.SemanticFlags[CurrIdxBoneRemap] & 0x40 == 0x40: #Confirmation
						for k in range(0, MOT.Header.KeyFramesScaleCount):
							scaleNoeKeyFramedValues.append(NoeKeyFramedValue(MOT.Data.ScaleKeyFrames[k],MOT.Data.Scale[k + MOT.Data.TRSPoseIdx[MOL.MOTInfo[i].Idx[MOL.MOTInfo[i].BoneRemap[j]]].Scale]))
						keyFramedBoneList[list(BoneIdxsDict.keys())[list(BoneIdxsDict.values()).index(CurrIdxBoneRemap)]].setScale(scaleNoeKeyFramedValues, noesis.NOEKF_SCALE_VECTOR_3)
					MOT.Data.TRSPoseIdx[MOL.MOTInfo[i].Idx[MOL.MOTInfo[i].BoneRemap[j]]].ID -= 4
			anim = NoeKeyFramedAnim(MOL.RFHeader.Files[i].FileName, bones, keyFramedBoneList, MOT.Header.Framerate)
			animationList.append(anim)
	rapi.rpgClearBufferBinds()
	try:
		mdl = rapi.rpgConstructModel()
	except:
		mdl = NoeModel()
	mdl.setBones(bones)
	if LoadAnim == 1:
		mdl.setAnims(animationList)
	#else:
	rapi.setPreviewOption("setAngOfs", "0 0 90")
	mdlList.append(mdl)
	return 1

#mdl general structure
#Header
#	RFHeader
#		MagicRF
#		MagicRFVersion
#		MagicRFType
#		MagicRFTypeVersion
#		FileCount
#		FilesListSize
#		Flag
#		HeaderSize
#		Files[]
#			FileName
#			FileSize
#			FileOff
#			unkFlags
#			FileType
#			unk1
#			IsInFile
#			unk2
#	CountsOffs
#		unk1
#		unk2
#		ObjectsCount
#		TDLFilesRefCount
#		MatCount
#		MeshCount
#		MeshWithBoneCount
#		MotFilesCount
#		MatOff
#		HiListType
#		UnkVDLSectionCount
#		MatInfoCount
#		UnkVDLSectionInfoOff
#		MatsInfoOff
#		MatsIndexOff[]
#		UnkVDLSectionOffs[]
#	MatMD2[]
#		TextureIdx
#		unk1
#		unk2
#		unk3
#	MatInfo[]
#		Off
#		TextureCount
#		unk1
#		ProgIdx
#		unk2
#	MatMD3[]
#		TextureIdx
#		unk1
#		TextureIdx2
#		unk2
#	MeshInfo[]
#		unk1
#		MeshType
#		unk2
#		unk3
#		IdxSectionsCount
#		AlwaysZero
#		AlwaysFF
#		unk4
#		Origin
#		AxisMin
#		AxisMax
#		MeshHeaderOff
#		MeshSize
#		BoneCount
#		unk5
#		SkelDataOff
#		InfoIdx[]
#			MatIdx
#			unk1
#			Optimization
#			unk2
#			unk3
#			Off
#VDL
#	HiList (Hierarchy List)
#		ObjectsCount
#		LODCount
#		HiListOff
#		HiListSize
#		Object[]
#			unk1
#			unk2
#			unk3
#			Code
#			Level
#			TranspFlag
#			Idx
#			Trans
#			Rot
#			Scale
#			Name
#		LODs[]
#			unk1
#			Name
#	Mesh[]
#		SkelData
#			Header
#				Size
#				WeightsIdxOff
#				WeightsOff
#				VtxCount
#			Bones[]
#			Mat[]
#			Weights()
#			WeightsIdx()
#		MeshHeader
#			VtxOff
#			NormOff
#			LightOff
#			UvOff
#			Uv2Off
#			MaybeUv3Off
#			MaybeUv4Off
#			IdxOff
#			VtxCount
#			NormCount
#			LightCount
#			UvCount
#			Uv2Count
#			MaybeUv3Count
#			MaybeUv4Count
#			MaxCount
#			unk1
#			IdxSizeFlags
#			unk2
#			unk3
#			IdxStride
#			IsStrideExtended
#			UvMapsCount
#			VtxStride
#			NormStride
#			LightStride
#			UvStride
#			VtxIndex
#			NormIndex
#			LightIndex
#			UvIndex
#			Uv2Index
#		MeshData
#			VtxBuff
#			NormBuff
#			UvBuff
#			Uv2Buff
#			FragmentSize
#			Indices[]
#				Idxs[]
#MOL
#	RFHeader
#		MagicRF
#		MagicRFVersion
#		MagicRFType
#		MagicRFTypeVersion
#		FileCount
#		FilesListSize
#		Flag
#		HeaderSize
#		Files[]
#			FileName
#			FileSize
#			FileOff
#			unkFlags
#			FileType
#			unk1
#			IsInFile
#			unk2
#	CountsOffs
#		MOTFilesCount
#		BoneCount
#		BoneNamesOff
#		MOTInfoOff
#		SemanticFlagsOff
#	Bones[]
#	MOTInfo[]
#		MOTInfoOffs
#			unk1
#			BoneRemapOff
#			IdxOff
#		BoneRemap[]
#		Idx[]
#	SemanticFlags[]
#MOT
#	Header
#		Magic
#		Size
#		Framerate
#		LenInFrames
#		TRSPoseIdxCount
#
#		TRSPoseValuesCount
#		BoneCount
#		TRSPoseIdxOff
#		TRSPoseValuesOff
#		BoneTransCount
#		KeyFramesTransCount
#
#		TransBufferOff
#		TransKeyFramesOff
#		BoneRotCount
#		KeyFramesRotCount
#		RotBufferOff
#
#		RotKeyFramesOff
#		BoneScaleCount
#		KeyFramesScaleCount
#		ScaleBufferOff
#		ScaleKeyFramesOff
#	Data
#		Trans[]
#		Rot[]
#		Scale[]
#		TRSPoseValues[]
#		TRSPoseIdx[]
#			ID
#			Trans
#			Rot
#			Scale
#		TransKeyFrames[]
#		RotKeyFrames[]
#		ScaleKeyFrames[]

def PrintHexArray(arr):
	for i in range(0, int(len(arr))):
		if i % 0x10 == 0:
			print("")
			print("[0x" + format(i, '08X') + "]\t", end="")
		print(format(arr[i], '02X'), end=" ")
	print("")
	return 1

def PrintHexArray2(arr):
	for i in range(0, int(len(arr))):
		if i % 0x10 == 0:
			print("\n", end="")
			print("[0x" + format(i, '08X') + "]\t", end="")
		print(format(arr[i], '02X'), end=" ")
		if i % 4 == 3:
			print("| ", end="")
	print("")
	return 1

def PrintMat43(Mat): #4 rows, 3 cols
	for i in range(0, 4):
		print(str(Mat[i][0]) + " " + str(Mat[i][1]) + " " + str(Mat[i][2]))
	#print(str(Mat[3][0]) + " " + str(Mat[3][1]) + " " + str(Mat[3][2]))
	return 1
	
def PrintRoundMat43(Mat): #4 rows, 3 cols
	for i in range(0, 4):
		print(str(round(Mat[i][0], 3)) + " " + str(round(Mat[i][1], 3)) + " " + str(round(Mat[i][2], 3)))
	#print(str(Mat[3][0]) + " " + str(Mat[3][1]) + " " + str(Mat[3][2]))
	return 1
	
def PrintMat44(Mat): #4 rows, 4 cols
	for i in range(0, 4):
		print(str(Mat[i][0]) + " " + str(Mat[i][1]) + " " + str(Mat[i][2]) + " " + str(Mat[i][3]))
	return 1
	
def PrintRoundMat44(Mat): #4 rows, 4 cols
	for i in range(0, 4):
		print(str(round(Mat[i][0], 3)) + " " + str(round(Mat[i][1], 3)) + " " + str(round(Mat[i][2], 3)) + " " + str(round(Mat[i][3], 3)))
	return 1

def getString(bs):
	string = noeStrFromBytes(bs.readBytes(0x10), "ASCII")
	string = string.split("\x00")[0]
	return string	

def ParseVDL(bs, v, ObjectsCount, MeshCount, MeshInfo):
	global VDLOffLocal
	VDLOffLocal = v.FileOff
	bs.seek(VDLOffLocal)
	VDL = VDL_t(bs, ObjectsCount, MeshCount, MeshInfo)	
	return VDL

def ParseMOL(bs, v):
	global MOLOffLocal
	MOLOffLocal = v.FileOff
	bs.seek(MOLOffLocal)
	MOL = MOL_t(bs)
	return MOL
	
def ParseMOT(bs, v, MOL, i):
	global MOTOffLocal
	MOTOffLocal = v.FileOff + MOLOffLocal
	bs.seek(MOTOffLocal)
	MOT = MOT_t(bs)
	bs.seek(MOLOffLocal + MOL.MOTInfo[i].MOTInfoOffs.BoneRemapOff)
	MOL.MOTInfo[i].BoneRemap = [bs.readUShort() for a in range(MOT.Header.BoneCount)]
	bs.seek(MOLOffLocal + MOL.MOTInfo[i].MOTInfoOffs.IdxOff)
	MOL.MOTInfo[i].Idx = [bs.readUShort() for a in range(MOL.CountsOffs.BoneCount)]
	return MOT
	
def UnderstandIndexCount(GPU, GPU2, MeshHeader):
	FragmentSize = 0
	if GPU2 != 0:
		if ((GPU2 & 0b00000011) == 0b00000011):
			MeshHeader.VtxIndex = 3
			FragmentSize += 2
		elif ((GPU2 & 0b00000010) == 0b00000010):
			MeshHeader.VtxIndex = 2
			FragmentSize += 1
			
		if ((GPU2 & 0b00001100) == 0b00001100):
			MeshHeader.NormIndex = 3
			FragmentSize += 2
		elif ((GPU2 & 0b00001000) == 0b00001000):
			MeshHeader.NormIndex = 2
			FragmentSize += 1
			
		if ((GPU2 & 0b00110000) == 0b00110000):
			MeshHeader.LightIndex = 3
			FragmentSize += 2
		elif ((GPU2 & 0b00100000) == 0b00100000):
			MeshHeader.LightIndex = 2
			FragmentSize += 1
			
		if ((GPU2 & 0b11000000) == 0b11000000):
			MeshHeader.UvIndex = 3
			FragmentSize += 2
		elif ((GPU2 & 0b10000000) == 0b10000000):
			MeshHeader.UvIndex = 2
			FragmentSize += 1
			
		if GPU != 0:
			if ((GPU & 0b00000011) == 0b00000011):
				MeshHeader.Uv2Index = 3
				FragmentSize += 2
			elif ((GPU & 0b00000010) == 0b00000010):
				MeshHeader.Uv2Index = 2
				FragmentSize += 1
	else:
		if MeshHeader.VtxCount >= 0xFF or MD2 == 1 or MeshHeader.IdxStride == 0:
			MeshHeader.VtxIndex = 3
			FragmentSize += 2
		else:
			MeshHeader.VtxIndex = 2
			FragmentSize += 1
		if MeshHeader.NormCount >= 0xFF or MD2 == 1 or MeshHeader.IdxStride == 0:
			MeshHeader.NormIndex = 3
			FragmentSize += 2
		else:
			MeshHeader.NormIndex = 2
			FragmentSize += 1
		if MeshHeader.LightCount >= 0xFF or MD2 == 1 and MeshHeader.LightOff > 0 or MeshHeader.LightOff > 0:
			MeshHeader.LightIndex = 3
			FragmentSize += 2
		elif MD3 == 1 and MeshHeader.LightOff > 0:
			MeshHeader.LightIndex = 2
			FragmentSize += 1
		else:
			MeshHeader.LightIndex = 0
			
		if MeshHeader.UvCount >= 0xFF or MD2 == 1 or MeshHeader.IdxStride == 0:
			MeshHeader.UvIndex = 3
			FragmentSize += 2
		else:
			MeshHeader.UvIndex = 2
			FragmentSize += 1
		if MeshHeader.VtxOff == 0x40:
			if MeshHeader.Uv2Off > 0 and MeshHeader.Uv2Count >= 0xFF:
				MeshHeader.Uv2Index = 3
				FragmentSize += 2
			elif MD3 == 1 and MeshHeader.Uv2Off > 0:
				MeshHeader.Uv2Index = 2
				FragmentSize += 1
			else:
				MeshHeader.Uv2Index = 0
	return FragmentSize
	
class VDL_t:
	def __init__(self, bs, ObjectsCount, MeshCount, MeshInfo):
		self.HiList = HiList_t(bs, ObjectsCount)
		self.Mesh = []
		for i in range(0, MeshCount):
			if MeshInfo[i].MeshType == 0x50:
				bs.seek(VDLOffLocal + MeshInfo[i].SkelDataOff)
			else:
				bs.seek(VDLOffLocal + MeshInfo[i].MeshHeaderOff)
			#print("Mesh: ", end="")
			#print(str(i) + "\t" + hex(bs.tell()))
			self.Mesh.append(Mesh_t(bs, MeshInfo[i]))

class Mesh_t:
	def __init__(self, bs, MeshInfo):
		if MeshInfo.MeshType == 0x50:
			self.SkelData = SkelData_t(bs, MeshInfo)
		bs.seek(VDLOffLocal + MeshInfo.MeshHeaderOff)
		self.MeshHeader = MeshHeader_t(bs)
		self.MeshData = MeshData_t(bs, MeshInfo, self.MeshHeader)

class IndexStatus:
    IND_NONE = 0
    IND_BYTE = 2
    IND_SHORT = 3
	
class MeshData_t:
	def __init__(self, bs, MeshInfo, MeshHeader):
		bs.seek(VDLOffLocal + MeshInfo.MeshHeaderOff + MeshHeader.VtxOff)
		self.VtxBuff = bs.readBytes(MeshHeader.VtxCount * MeshHeader.VtxStride)
		bs.seek(VDLOffLocal + MeshInfo.MeshHeaderOff + MeshHeader.NormOff)
		self.NormBuff = bs.readBytes(MeshHeader.NormCount * MeshHeader.NormStride)
		bs.seek(VDLOffLocal + MeshInfo.MeshHeaderOff + MeshHeader.UvOff)
		self.UvBuff = bs.readBytes(MeshHeader.UvCount * MeshHeader.UvStride)
		if MeshHeader.VtxOff == 0x40:
			if MeshHeader.UvMapsCount == 2:
				bs.seek(VDLOffLocal + MeshInfo.MeshHeaderOff + MeshHeader.Uv2Off)
				self.Uv2Buff = bs.readBytes(MeshHeader.Uv2Count * MeshHeader.UvStride)
		if MeshHeader.VtxOff == 0x40:
			self.FragmentSize = UnderstandIndexCount(MeshHeader.IdxSizeFlags >> 8, (MeshHeader.IdxSizeFlags << 8) >> 8, MeshHeader)
		else:
			self.FragmentSize = UnderstandIndexCount(0, 0, MeshHeader)
		self.Indices = []
		for i in range(0, MeshInfo.IdxSectionsCount):
			bs.seek(VDLOffLocal + MeshInfo.MeshHeaderOff + MeshInfo.InfoIdx[i].Off)
			self.Indices.append(Indices_t(bs, MeshInfo, MeshHeader, self.FragmentSize))
		
class Indices_t:
	def __init__(self, bs, MeshInfo, MeshHeader, FragmentSize):
		self.Idxs = []
		self.cntList = []
		idxBuffer = bytes()
		while True:
			indunk = bs.readUShort()
			cnt = bs.readUShort()
			while cnt < 3:
				bs.seek(cnt * FragmentSize, NOESEEK_REL)
				indunk = bs.readUShort()
				cnt = bs.readUShort()
			idxBuffer = bs.readBytes(cnt * FragmentSize)
			self.Idxs.append(idxBuffer)
			self.cntList.append(cnt)
			if (indunk & 0x1) == 0x0:
				break
				
class MeshHeader_t:
	def __init__(self, bs):
		self.VtxOff = bs.readUInt()
		self.NormOff = bs.readUInt()
		self.LightOff = bs.readUInt()
		self.UvOff = bs.readUInt()
		if self.VtxOff == 0x40:
			self.Uv2Off = bs.readUInt()
			self.MaybeUv3Off = bs.readUInt()
			self.MaybeUv4Off = bs.readUInt()
		self.IdxOff = bs.readUInt()
		self.VtxCount = bs.readUShort()
		self.NormCount = bs.readUShort()
		self.LightCount = bs.readUShort()
		self.UvCount = bs.readUShort()
		if self.VtxOff == 0x40:
			self.Uv2Count = bs.readUShort()
			self.MaybeUv3Count = bs.readUShort()
			self.MaybeUv4Count = bs.readUShort()
		self.MaxCount = bs.readUShort()
		if self.VtxOff == 0x40:
			self.unk1 = bs.readUShort()
			self.IdxSizeFlags = bs.readUShort()
			self.unk2 = bs.readUInt()
			self.unk3 = bs.readByte()
			self.IdxStride = bs.readByte()
			self.IsStrideExtended = bs.readByte()
			self.UvMapsCount = bs.readByte()
			self.VtxStride = bs.readByte()
			self.NormStride = bs.readByte()
			self.LightStride = bs.readByte()
			self.UvStride = bs.readByte()
		else:
			self.unk1 = bs.readByte()
			self.IsStrideExtended = bs.readByte()
			self.IdxStride = 0
			if self.IsStrideExtended == 1:
				self.VtxStride = 0x18
				self.NormStride = 0x18
			else:
				self.VtxStride = 0xC
				self.NormStride = 0xC
			self.LightStride = 4
			self.UvStride = 8
		self.VtxIndex = IndexStatus.IND_NONE
		self.NormIndex = IndexStatus.IND_NONE
		self.LightIndex = IndexStatus.IND_NONE
		self.UvIndex = IndexStatus.IND_NONE
		self.Uv2Index = IndexStatus.IND_NONE
		
class SkelData_t:
	def __init__(self, bs, MeshInfo):
		self.Header = SkelDataHeader_t(bs)
		self.Bones = []
		self.Mat = []
		self.Weights = bytearray()
		self.WeightsIdx = bytearray()
		for i in range(0, MeshInfo.BoneCount):
			self.Bones.append(getString(bs))
		for i in range(0, MeshInfo.BoneCount):
			#self.Mat.append(NoeMat44.fromBytes(bs.readBytes(0x40),1).toMat43().swapHandedness())
			#self.Mat.append(NoeMat44.fromBytes(bs.readBytes(0x40),1).inverse().toMat43()) #OK
			self.Mat.append(NoeMat44.fromBytes(bs.readBytes(0x40),1).toMat43().inverse()) #OK
		bs.seek(VDLOffLocal + MeshInfo.SkelDataOff + self.Header.WeightsOff)
		self.Weights = bytearray(bs.readBytes(self.Header.VtxCount * 0x10))
		bs.seek(VDLOffLocal + MeshInfo.SkelDataOff + self.Header.WeightsIdxOff)
		self.WeightsIdx = bytearray(bs.readBytes(self.Header.VtxCount * 0x4))
		
class SkelDataHeader_t:
	def __init__(self, bs):
		self.Size = bs.readUInt()
		self.WeightsIdxOff = bs.readUInt()
		self.WeightsOff = bs.readUInt()
		self.VtxCount = bs.readUInt()
		
class HiList_t:
	def __init__(self, bs, ObjectsCount):
		if HiListType >= 0x12F:
			self.ObjectsCount = bs.readUShort()
			self.LODCount = bs.readUShort()
			self.HiListOff = bs.readUInt()
			self.HiListSize = bs.readUInt()
		self.Object = []
		for i in range(0, ObjectsCount):
			self.Object.append(Object_t(bs))
			
		for i in range(0, ObjectsCount):
			if self.Object[i].Level > 0:
				CurrLevel = self.Object[i].Level
				for j in range(i - 1, 0, -1):
					if self.Object[j].Level == CurrLevel - 1:
						self.Object[i].PrevObjID = self.Object[j].ID
						break
			else:
				self.Object[i].PrevObjID = -1
				
		#Transform obj's mat43
		for i in range(0, ObjectsCount):
			q = self.Object[i].PrevObjID
			if q != -1:
				self.Object[i].Mat43 *= self.Object[q].Mat43
				
		if HiListType >= 0x12F:
			if self.LODCount > 0:
				self.LODs = []
				for i in range(0, self.LODCount):
					self.LODs.append(LOD_t(bs))

class LOD_t:
	def __init__(self, bs):
		self.unk1 = bs.readUInt()
		self.Name = getString(bs)

class Object_t:
	def __init__(self, bs):
		self.ID = (bs.tell() - VDLOffLocal) // 0x40
		self.PrevObjID = 0
		self.unk1 = bs.readByte()
		self.unk2 = bs.readByte()
		self.unk3 = bs.readByte()
		self.Code = bs.readByte()
		self.Level = bs.readByte()
		self.TranspFlag = bs.readByte()
		self.Idx = bs.readUShort()
		self.Trans = NoeVec3.fromBytes(bs.readBytes(0x0C),1)
		self.Rot = NoeQuat.fromBytes(bs.readBytes(0x10),1)
		self.Scale = NoeVec3.fromBytes(bs.readBytes(0x0C),1)
		self.Name = getString(bs)
		self.Mat43 = self.Rot.toMat43().inverse()
		self.Mat43[3] = self.Trans
	
class Header_t:
	def __init__(self, bs):
		self.RFHeader = RFHeader_t(bs)
		global MD2
		global MD3
		self.CountsOffs = CountsOffs_t(bs, self.RFHeader.MagicRFTypeVersion)
		if self.RFHeader.MagicRFTypeVersion == "2":
			MD2 = 1
			MD3 = 0
			bs.seek(self.CountsOffs.MatOff)
			self.MatMD2 = MatMD2_t(bs)
		else:
			MD2 = 0
			MD3 = 1
			bs.seek(self.CountsOffs.MatsInfoOff)
			self.MatInfo = []
			for i in range(0, self.CountsOffs.MatInfoCount):
				self.MatInfo.append(MatInfo_t(bs))
				tmp = bs.tell()
				bs.seek(self.MatInfo[i].Off)
				self.MatMD3 = MatMD3_t(bs, self.MatInfo[i].TextureCount)
				bs.seek(tmp)
		self.MeshInfo = []
		for i in range(0, self.CountsOffs.MeshCount):
			bs.seek(self.CountsOffs.MeshInfoOffs[i])
			self.MeshInfo.append(MeshInfo_t(bs))
			
class MeshInfo_t:
	def __init__(self, bs):
		self.unk1 = bs.readByte()
		self.MeshType = bs.readByte()
		self.unk2 = bs.readUShort()
		self.unk3 = bs.readUShort()
		self.IdxSectionsCount = bs.readUShort()
		self.AlwaysZero = bs.readUInt()
		self.AlwaysFF = bs.readUInt()
		self.unk4 = bs.readFloat()
		self.Origin = NoeVec3.fromBytes(bs.readBytes(0x0C),1)
		self.AxisMin = NoeVec3.fromBytes(bs.readBytes(0x0C),1)
		self.AxisMax = NoeVec3.fromBytes(bs.readBytes(0x0C),1)
		self.MeshHeaderOff = bs.readUInt()
		self.MeshSize = bs.readUInt()
		if self.MeshType == 0x50:
			self.BoneCount = bs.readUShort()
			self.unk5 = bs.readUShort()
			self.SkelDataOff = bs.readUInt()
		self.InfoIdx = []
		for i in range(0, self.IdxSectionsCount):
			self.InfoIdx.append(InfoIdx_t(bs))

class InfoIdx_t:
	def __init__(self, bs):
		self.MatIdx = bs.readUShort()
		self.unk1 = bs.readByte()
		self.Optimization = bs.readByte()
		self.unk2 = bs.readUShort()
		self.unk3 = bs.readUShort()
		self.Off = bs.readUInt()

class MatMD3_t:
	def __init__(self, bs, TextureCount):
		if TextureCount == 1:
			self.TextureIdx = bs.readUShort()
			self.unk1 = bs.readUShort()
		else:
			self.TextureIdx = bs.readUShort()
			self.unk1 = bs.readUShort()
			self.TextureIdx2 = bs.readUShort()
			self.unk2 = bs.readUShort()

class MatInfo_t:
	def __init__(self, bs):
		self.Off = bs.readUInt()
		self.TextureCount = bs.readByte()
		self.unk1 = bs.readByte()
		self.ProgIdx = bs.readUShort()
		self.unk2 = bs.readFloat()

class MatMD2_t:
	def __init__(self, bs):
		self.TextureIdx = bs.readUShort()
		self.unk1 = bs.readUShort()
		self.unk2 = bs.readUInt()
		self.unk3 = bs.readFloat()

class CountsOffs_t:
	def __init__(self, bs, MagicRFTypeVersion):
		global HiListType
		if MagicRFTypeVersion == "2":
			self.unk1 = bs.readUShort()
			self.unk2 = bs.readUShort()
			self.ObjectsCount = bs.readUShort()
			self.TDLFilesRefCount = bs.readUShort()
			self.MatCount = bs.readUShort()
			self.MeshCount = bs.readUShort()
			self.MeshWithBoneCount = bs.readUShort()
			self.MotFilesCount = bs.readUShort()
			self.MatOff = bs.readUInt()
			HiListType = 0x12E
		else:
			self.unk1 = bs.readUShort()
			self.ObjectListType = bs.readUShort()
			self.ObjectsCount = bs.readUShort()
			self.TDLFilesRefCount = bs.readUShort()
			self.UnkVDLSectionCount = bs.readUShort()
			self.MatInfoCount = bs.readUShort()
			self.MatCount = bs.readUShort()
			self.MeshCount = bs.readUShort()
			self.MeshWithBoneCount = bs.readUShort()
			self.MotFilesCount = bs.readUShort()
			self.UnkVDLSectionInfoOff = bs.readUInt()
			self.MatsInfoOff = bs.readUInt()
			self.MatsIndexOff = bs.readUInt()
			HiListType = self.ObjectListType
		self.MeshInfoOffs = []
		for i in range(0, self.MeshCount):
			self.MeshInfoOffs.append(bs.readUInt())
		NoeBitStream.setEndian(bs, NOE_BIGENDIAN)
		if MagicRFTypeVersion == "3" and self.UnkVDLSectionCount > 0:
			self.UnkVDLSectionOffs = []
			for i in range(0, self.UnkVDLSectionCount):
				self.UnkVDLSectionOffs.append(bs.readUInt())
				
class MOT_t:
	def __init__(self, bs):
		self.Header = MOTHeader_t(bs)
		self.Data = MOTData_t(bs, self.Header)
		
class MOTHeader_t:
	def __init__(self, bs):
		self.Magic = noeStrFromBytes(bs.readBytes(0x4), "ASCII")
		self.Size = bs.readUInt()
		self.Framerate = bs.readFloat()
		self.LenInFrames = bs.readUShort()
		self.TRSPoseIdxCount = bs.readUShort()
		
		self.TRSPoseValuesCount = bs.readUShort()
		self.BoneCount = bs.readUShort()
		self.TRSPoseIdxOff = bs.readUInt()
		self.TRSPoseValuesOff = bs.readUInt()
		self.BoneTransCount = bs.readUShort()
		self.KeyFramesTransCount = bs.readUShort()
		
		self.TransBufferOff = bs.readUInt()
		self.TransKeyFramesOff = bs.readUInt()
		self.BoneRotCount = bs.readUShort()
		self.KeyFramesRotCount = bs.readUShort()
		self.RotBufferOff = bs.readUInt()
		
		self.RotKeyFramesOff = bs.readUInt()
		self.BoneScaleCount = bs.readUShort()
		self.KeyFramesScaleCount = bs.readUShort()
		self.ScaleBufferOff = bs.readUInt()
		self.ScaleKeyFramesOff = bs.readUInt()
		
		self.TRSPoseIdxOff += MOTOffLocal
		self.TRSPoseValuesOff += MOTOffLocal
		self.TransBufferOff += MOTOffLocal
		self.TransKeyFramesOff += MOTOffLocal
		self.RotBufferOff += MOTOffLocal
		self.RotKeyFramesOff += MOTOffLocal
		self.ScaleBufferOff += MOTOffLocal
		self.ScaleKeyFramesOff += MOTOffLocal
		
class MOTData_t:
	def __init__(self, bs, Header):
		self.Trans = []
		self.Rot = []
		self.Scale = []
		self.TRSPoseValues = []
		self.TRSPoseIdx = []
		self.TransKeyFrames = []
		self.RotKeyFrames = []
		self.ScaleKeyFrames = []
		
		bs.seek(Header.TransBufferOff)
		for i in range(0, Header.BoneTransCount * Header.KeyFramesTransCount):
			self.Trans.append(NoeVec4([bs.readFloat() for a in range(4)]).toVec3())
			
		bs.seek(Header.RotBufferOff)
		for i in range(0, Header.BoneRotCount * Header.KeyFramesRotCount):
			self.Rot.append(NoeQuat([bs.readFloat() for a in range(4)]).transpose())
			
		bs.seek(Header.ScaleBufferOff)
		for i in range(0, Header.BoneScaleCount * Header.KeyFramesScaleCount):
			self.Scale.append(NoeVec4([bs.readFloat() for a in range(4)]).toVec3())
			
		bs.seek(Header.TRSPoseValuesOff)
		for i in range(0, Header.TRSPoseValuesCount):
			self.TRSPoseValues.append(NoeVec4([bs.readFloat() for a in range(4)]))
			
		bs.seek(Header.TRSPoseIdxOff)
		for i in range(0, Header.TRSPoseIdxCount):
			self.TRSPoseIdx.append(TRSPoseIdx_t(bs))
		
		if Header.BoneTransCount > 0:
			bs.seek(Header.TransKeyFramesOff)
			self.TransKeyFrames = ([bs.readFloat() for a in range(Header.KeyFramesTransCount)])
		
		if Header.BoneRotCount > 0:
			bs.seek(Header.RotKeyFramesOff)
			self.RotKeyFrames = ([bs.readFloat() for a in range(Header.KeyFramesRotCount)])
		
		if Header.BoneScaleCount > 0:
			bs.seek(Header.ScaleKeyFramesOff)
			self.ScaleKeyFrames = ([bs.readFloat() for a in range(Header.KeyFramesScaleCount)])

class TRSPoseIdx_t:
	def __init__(self, bs):
		self.ID = bs.readUShort()
		self.Trans = bs.readUShort()
		self.Rot = bs.readUShort()
		self.Scale = bs.readUShort()

class MOL_t:
	def __init__(self, bs):
		self.RFHeader = RFHeader_t(bs)
		NoeBitStream.setEndian(bs, NOE_BIGENDIAN)
		self.CountsOffs = MLCountsOffs_t(bs)
		self.Bones = []
		self.SemanticFlags = []
		self.MOTInfo = []
		bs.seek(MOLOffLocal + self.CountsOffs.BoneNamesOff)
		for i in range(0, self.CountsOffs.BoneCount):
			self.Bones.append(getString(bs))
			
		bs.seek(MOLOffLocal + self.CountsOffs.MOTInfoOff)
		for i in range(0, self.CountsOffs.MOTFilesCount):
			self.MOTInfo.append(MOTInfo_t(bs))
		
		bs.seek(MOLOffLocal + self.CountsOffs.SemanticFlagsOff)
		for i in range(0, self.CountsOffs.BoneCount):
			self.SemanticFlags.append(bs.readByte())

class MLCountsOffs_t:
	def __init__(self, bs):
		self.MOTFilesCount = bs.readUShort()
		self.BoneCount = bs.readUShort()
		self.BoneNamesOff = bs.readUInt()
		self.MOTInfoOff = bs.readUInt()
		self.SemanticFlagsOff = bs.readUInt()
		
class MOTInfo_t:
	def __init__(self, bs):
		self.MOTInfoOffs = MOTInfoOffs_t(bs)
		self.BoneRemap = []
		self.Idx = []
		
class MOTInfoOffs_t:
	def __init__(self, bs):
		self.unk1 = bs.readUInt()
		self.BoneRemapOff = bs.readUInt()
		self.IdxOff = bs.readUInt()
		
class RFHeader_t:
	def __init__(self, bs):
		NoeBitStream.setEndian(bs, NOE_LITTLEENDIAN)
		self.MagicRF = noeStrFromBytes(bs.readBytes(0x2), "ASCII")
		self.MagicRFVersion = noeStrFromBytes(bs.readBytes(0x1), "ASCII")
		self.MagicRFType = noeStrFromBytes(bs.readBytes(0x2), "ASCII")
		self.MagicRFTypeVersion = noeStrFromBytes(bs.readBytes(0x1), "ASCII")
		self.FileCount = bs.readUShort()
		self.FilesListSize = bs.readUShort()
		self.Flag = bs.readUShort()
		self.HeaderSize = bs.readUInt()
		self.Files = []
		for i in range(0, self.FileCount):
			self.Files.append(RFFile_t(bs, self.MagicRFVersion))

class RFFile_t:
	def __init__(self, bs, MagicRFVersion):
		if MagicRFVersion == "2":
			self.FileName = noeStrFromBytes(bs.readBytes(0x14), "ASCII")
			self.FileSize = bs.readUInt()
			self.FileOff = bs.readUInt()
			self.FileType = bs.readByte()
			self.unk1 = bs.readByte()
			self.IsInFile = bs.readByte()
			self.unk2 = bs.readByte()
		else:
			self.FileName = noeStrFromBytes(bs.readBytes(0x10), "ASCII")
			self.FileOff = bs.readUInt()
			self.FileSize = bs.readUInt()
			self.unkFlags = bs.readUInt()
			self.FileType = bs.readByte()
			self.unk1 = bs.readByte()
			self.IsInFile = bs.readByte()
			self.unk2 = bs.readByte()