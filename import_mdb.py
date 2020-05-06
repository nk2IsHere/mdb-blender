# nk2's craft made of plasticine (level: Kindergarten, 1 year)
# heavily based on https://github.com/JLouis-B/RedTools/blob/master/W2ENT_QT/IO_MeshLoader_WitcherMDL.cpp
from functools import reduce
import struct
import os
from enum import Enum
from typing.io import BinaryIO
import bpy

# ----MODEL TYPES


class NodeType(Enum):
    kNodeTypeNode = 0x00000001,
    kNodeTypeLight = 0x00000003,
    kNodeTypeEmitter = 0x00000005,
    kNodeTypeCamera = 0x00000009,
    kNodeTypeReference = 0x00000011,
    kNodeTypeTrimesh = 0x00000021,
    kNodeTypeSkin = 0x00000061,
    kNodeTypeAABB = 0x00000221,
    kNodeTypeTrigger = 0x00000421,
    kNodeTypeSectorInfo = 0x00001001,
    kNodeTypeWalkmesh = 0x00002001,
    kNodeTypeDanglyNode = 0x00004001,
    kNodeTypeTexturePaint = 0x00008001,
    kNodeTypeSpeedTree = 0x00010001,
    kNodeTypeChain = 0x00020001,
    kNodeTypeCloth = 0x00040001


class ControllerType(Enum):
    ControllerPosition = 84,
    ControllerOrientation = 96,
    ControllerScale = 184


class NodeTrimeshControllerType(Enum):
    kNodeTrimeshControllerTypeSelfIllumColor = 276
    kNodeTrimeshControllerTypeAlpha = 292


class ModelData(object):
    def __init__(self,
        baseDirectory: str,
        modelName: str,
        fileVersion: int,
        offsetModelData: int,
        sizeModelData: int,
        offsetRawData: int,
        sizeRawData: int,
        offsetTextureInfo: int,
        offsetTexData: int,
        sizeTexData: int
    ):
        super(ModelData, self).__init__()
        self.baseDirectory = baseDirectory
        self.modelName = modelName
        self.fileVersion = fileVersion
        self.offsetModelData = offsetModelData
        self.sizeModelData = sizeModelData
        self.offsetRawData = offsetRawData
        self.sizeRawData = sizeRawData
        self.offsetTextureInfo = offsetTextureInfo
        self.offsetTexData = offsetTexData
        self.sizeTexData = sizeTexData

    def __repr__(self) -> str:
        return "{}({!r})".format(self.__class__.__name__, self.__dict__)


# ----MODEL TYPES END

# simple method to read string from something like 0x[ASCII]dcdcdcdcdc...
def dataToStr(data):
    return reduce(lambda acc, next: acc + next.decode('utf-8') if next != b'\xdc' else acc + "", data, "")


# easier to sync code with RedTools
class FileWrapper(object):
    def __init__(self, content: bytes):
        super(FileWrapper, self).__init__()
        self.content = content
        self.offset = 0

    # set offset to read from
    def seek(self, offset: int, relative: bool = False):
        self.offset = self.offset + offset if relative else offset

    def readUInt32(self):
        data = struct.unpack("I", self.content[self.offset:self.offset + 4])[0]
        self.seek(4, relative=True)
        return data

    def readUInt16(self):
        data = struct.unpack("H", self.content[self.offset:self.offset + 2])[0]
        self.seek(2, relative=True)
        return data

    def readUByte(self):
        data = struct.unpack("B", self.content[self.offset:self.offset + 1])[0]
        self.seek(1, relative=True)
        return data

    def readInt32(self):
        data = struct.unpack("i", self.content[self.offset:self.offset + 4])[0]
        self.seek(4, relative=True)
        return data

    def readInt16(self):
        data = struct.unpack("h", self.content[self.offset:self.offset + 2])[0]
        self.seek(2, relative=True)
        return data

    def readByte(self):
        data = struct.unpack("b", self.content[self.offset:self.offset + 1])[0]
        self.seek(1, relative=True)
        return data

    def readFloat32(self):
        data = struct.unpack("f", self.content[self.offset:self.offset + 4])[0]
        self.seek(4, relative=True)
        return data

    def readString(self, size: int):
        data = dataToStr(struct.unpack("c" * size, self.content[self.offset:self.offset + size]))
        self.seek(size, relative=True)
        return data

    def readStringUntilNull(self):
        data = []

        cnt = 0
        while True:
            chr = struct.unpack("c", self.content[self.offset + cnt:self.offset + cnt + 1])[0]
            data.append(chr)
            cnt += 1
            if chr == b'\x00':
                break

        self.seek(cnt, relative=True)
        return dataToStr(data)

    @classmethod
    def fromFile(cls, file: BinaryIO):
        instance = cls(file.read())
        file.close()
        return instance


# array header used by bioware aurora models
class ArrayDefinition(object):
    def __init__(self, firstElemOffset: int, nbUsedEntries: int, nbAllocatedEntries: int):
        super().__init__()
        self.firstElemOffset = firstElemOffset
        self.nbUsedEntries = nbUsedEntries
        self.nbAllocatedEntries = nbAllocatedEntries


# read array using its definition
# (all arrays' contents start globally @offsetModelData)
def readArray(
    content: FileWrapper,
    definition: ArrayDefinition,
    sType: str,
    sSize: int,
    offsetModelData: int
):
    offset = offsetModelData + definition.firstElemOffset
    return [
        struct.unpack(sType, content[offset + sSize * i:offset + sSize * (i + 1)])[0]
        for i in range(definition.nbUsedEntries)
    ]

# ----MODEL LOADER

def load(
    operator,
    context,
    filepath="",
    base_path=None,
    global_matrix=None,
):
    modelName, modelExtension = os.path.basename(filepath).split('.')
    baseDirectory = os.path.join(os.path.dirname(filepath), base_path)

    content = FileWrapper.fromFile(open(filepath, "rb"))

    if content.readByte() != 0:
        raise Exception('File is not binary!')

    content.seek(4)
    fileVersion = content.readUInt32() & 0x0fffffff
    modelCount = content.readUInt32()
    offsetModelData = 32
    if fileVersion not in [133, 136] and modelCount != 1:
        raise Exception('Version 133 or 136 expected, got {0}; Model count 1 expected, got {1}'.format(fileVersion, modelCount))

    content.seek(4, relative=True)
    sizeModelData = content.readUInt32()

    content.seek(4, relative=True)
    modelData = ModelData(
        baseDirectory=baseDirectory,
        modelName=modelName,
        fileVersion=fileVersion,
        offsetModelData=offsetModelData,
        sizeModelData=sizeModelData,
        offsetRawData=content.readUInt32() + offsetModelData if fileVersion == 133 else 0,
        sizeRawData=content.readUInt32() if fileVersion == 133 else 0,
        offsetTexData=content.readUInt32() + offsetModelData if fileVersion == 136 else 0,
        sizeTexData=content.readUInt32() if fileVersion == 136 else 0,
        offsetTextureInfo=-1
    )
    content.seek(8, relative=True)

    modelData.name = content.readString(64)
    print(modelData)

    offsetRootNode = content.readUInt32()
    content.seek(32, relative=True)
    type = content.readUByte()

    content.seek(3 + 48, relative=True)
    firstLOD = content.readFloat32()
    lastLOD = content.readFloat32()

    content.seek(16, relative=True)
    detailMap = content.readString(64)
    print('detailMap={}'.format(detailMap))

    content.seek(4, relative=True)
    modelScale = content.readFloat32()
    superModel = content.readString(60)
    print('superModel={}'.format(superModel))

    animationScale = content.readFloat32()

    content.seek(16, relative=True)
    content.seek(modelData.offsetModelData + offsetRootNode)

    # loadNode()
    return {'FINISHED'}
