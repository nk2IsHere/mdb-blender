# nk2's craft made of plasticine (level: Kindergarten, 1 year)
# heavily based on https://github.com/JLouis-B/RedTools/blob/master/W2ENT_QT/IO_MeshLoader_WitcherMDL.cpp
import os

from mdb.model_data import ModelData
from mdb.file_utils import FileWrapper
from bpy.types import Armature
from mathutils import Matrix


def loadNode(
    wrapper: FileWrapper,
    modelData: ModelData,
    parentJoint: Armature = None,
    parentTransform: Matrix = None
):
    pass


def loadMeta(
    wrapper: FileWrapper,
    baseDirectory: str,
    modelName: str
):
    if wrapper.readByte() != 0:
        raise Exception('File is not binary!')

    wrapper.seek(4)
    fileVersion = wrapper.readUInt32() & 0x0fffffff
    modelCount = wrapper.readUInt32()
    offsetModelData = 32
    if fileVersion not in [133, 136] and modelCount != 1:
        raise Exception(
            'Version 133 or 136 expected, got {0}; Model count 1 expected, got {1}'
                .format(fileVersion, modelCount)
        )

    wrapper.seek(4, relative=True)
    sizeModelData = wrapper.readUInt32()

    wrapper.seek(4, relative=True)
    modelData = ModelData(
        baseDirectory=baseDirectory,
        modelName=modelName,
        fileVersion=fileVersion,
        offsetModelData=offsetModelData,
        sizeModelData=sizeModelData,
        offsetRawData=wrapper.readUInt32() + offsetModelData if fileVersion == 133 else 0,
        sizeRawData=wrapper.readUInt32() if fileVersion == 133 else 0,
        offsetTexData=wrapper.readUInt32() + offsetModelData if fileVersion == 136 else 0,
        sizeTexData=wrapper.readUInt32() if fileVersion == 136 else 0,
        offsetTextureInfo=-1,  # will be filled later
        offsetRootNode=-1,
        modelType=-1,
        firstLOD=-1,
        lastLOD=-1,
        detailMap='',
        modelScale=-1,
        superModel='',
        animationScale=-1
    )

    wrapper.seek(8, relative=True)
    modelData.name = wrapper.readString(64)

    modelData.offsetRootNode = wrapper.readUInt32()
    wrapper.seek(32, relative=True)
    modelData.type = wrapper.readUByte()

    wrapper.seek(3 + 48, relative=True)
    modelData.firstLOD = wrapper.readFloat32()
    modelData.lastLOD = wrapper.readFloat32()

    wrapper.seek(16, relative=True)
    modelData.detailMap = wrapper.readString(64)

    wrapper.seek(4, relative=True)
    modelData.modelScale = wrapper.readFloat32()
    modelData.superModel = wrapper.readString(60)
    modelData.animationScale = wrapper.readFloat32()

    wrapper.seek(16, relative=True)
    return modelData


def load(
    operator,
    context,
    filepath="",
    base_path=None,
    global_matrix: Matrix = None,
):
    modelName, modelExtension = os.path.basename(filepath).split('.')
    baseDirectory = os.path.join(os.path.dirname(filepath), base_path)

    wrapper = FileWrapper.fromFile(open(filepath, "rb"))

    modelData = loadMeta(wrapper, baseDirectory, modelName)
    print(modelData)

    wrapper.seek(modelData.offsetModelData + modelData.offsetRootNode)
    loadNode(wrapper, modelData, None, global_matrix)
    return {'FINISHED'}
