# nk2's craft made of plasticine (level: Kindergarten, 1 year)
# heavily based on https://github.com/JLouis-B/RedTools/blob/master/W2ENT_QT/IO_MeshLoader_WitcherMDL.cpp
import os

import bpy
from bpy_extras.object_utils import object_data_add

from .model_types import ControllerType, NodeTrimeshControllerType, NodeType
from .model_data import ModelData, StaticControllersData, ControllersData, ModelMesh, ModelJoint, _defaultMatrix, \
    ModelBoundingBox, ModelMaterial, ModelMeshBuffer
from .file_utils import FileWrapper, ArrayDefinition, readArray
from mathutils import Matrix, Vector, Quaternion, Color


#  Function that reads all animation in mdb-eqsue format
def readNodeControllers(
    wrapper: FileWrapper,
    modelData: ModelData,
    controllerKeyDef: ArrayDefinition,
    controllerDataDef: ArrayDefinition
):
    controllers = ControllersData.default()
    controllerData = readArray(wrapper, modelData, controllerDataDef, wrapper.readFloat32)
    back = wrapper.offset

    wrapper.seek(modelData.offsetModelData + controllerKeyDef.firstElemOffset)
    for i in range(controllerKeyDef.nbUsedEntries):
        controllerType = wrapper.readUInt32()
        nbRows = wrapper.readInt16()
        firstKeyIndex = wrapper.readInt16()
        firstValueIndex = wrapper.readInt16()
        nbColumns = wrapper.readUByte()

        wrapper.seek(1, relative=True)
        #  FIXME: seems, that every j in nbRows means absolutely different animation, maybe we should split it?
        if controllerType == ControllerType.ControllerPosition:
            for j in range(nbRows):
                offset = j * nbColumns
                controllers.positionTime.append(controllerData[firstKeyIndex + j])
                controllers.position.append(Vector((
                    controllerData[offset + firstValueIndex],
                    controllerData[offset + firstValueIndex + 1],
                    controllerData[offset + firstValueIndex + 2]
                )))
        elif controllerType == ControllerType.ControllerOrientation:
            for j in range(nbRows):
                offset = j * nbColumns
                controllers.positionTime.append(controllerData[firstKeyIndex + j])
                controllers.rotation.append(Quaternion((
                    controllerData[offset + firstValueIndex],
                    controllerData[offset + firstValueIndex + 1],
                    controllerData[offset + firstValueIndex + 2],
                    controllerData[offset + firstValueIndex + 3]
                )))
        elif controllerType == ControllerType.ControllerScale:
            for j in range(nbRows):
                offset = j * nbColumns
                controllers.scaleTime.append(controllerData[firstKeyIndex + j])
                controllers.scale.append(Vector((
                    controllerData[offset + firstValueIndex],
                    controllerData[offset + firstValueIndex],
                    controllerData[offset + firstValueIndex]
                )))
        elif controllerType == NodeTrimeshControllerType.ControllerSelfIllumColor:
            for j in range(nbRows):
                offset = j * nbColumns
                controllers.selfIllumColorTime.append(controllerData[firstKeyIndex + j])
                controllers.selfIllumColor.append(Color((
                    controllerData[offset + firstValueIndex],
                    controllerData[offset + firstValueIndex + 1],
                    controllerData[offset + firstValueIndex + 2]
                )))
        elif controllerType == NodeTrimeshControllerType.ControllerAlpha:
            for j in range(nbRows):
                offset = j * nbColumns
                controllers.alphaTime.append(controllerData[firstKeyIndex + j])
                controllers.alpha.append(
                    controllerData[offset + firstValueIndex]
                )

    wrapper.seek(back)
    return controllers


#  Function that wraps animation for static mesh (which has no animation, only first key)
def getStaticNodeControllers(
    wrapper: FileWrapper,
    modelData: ModelData,
    controllerKeyDef: ArrayDefinition,
    controllerDataDef: ArrayDefinition
):
    controllersData = StaticControllersData.default()
    controllers = readNodeControllers(wrapper, modelData, controllerKeyDef, controllerDataDef)
    if len(controllers.position) > 0:
        controllersData.position = controllers.position[0]
    if len(controllers.rotation) > 0:
        controllersData.rotation = controllers.rotation[0]
    if len(controllers.scale) > 0:
        controllersData.scale = controllers.scale[0]
    if len(controllers.alpha) > 0:
        controllersData.alpha = controllers.alpha[0]
    if len(controllers.selfIllumColor) > 0:
        controllersData.selfIllumColor = controllers.selfIllumColor[0]
    controllersData.computeLocalTransform()

    return controllersData


def hasTexture(path):
    return os.path.exists(path)


def readTextures(
    wrapper: FileWrapper,
    modelData: ModelData
):
    wrapper.seek(
        modelData.offsetRawData + modelData.offsetTexData
            if modelData.fileVersion == 133
            else modelData.offsetTexData + modelData.offsetTextureInfo
    )

    textureCount, offset = wrapper.readUInt32()
    offTexture, offset = wrapper.readUInt32()

    materialContent = ""
    for i in range(textureCount):
        line, offset = wrapper.readStringUntilNull()
        materialContent += "{}\n".format(line)

    return ModelMaterial.fromString(materialContent)


def readMeshNode(
    wrapper: FileWrapper,
    modelData: ModelData
):
    wrapper.seek(8, relative=True)  # Function pointer
    offMeshArrays = wrapper.readUInt32()

    wrapper.seek(4, relative=True)  # Unknown
    nodeBoundingBox = ModelBoundingBox(
        min=Vector((
            wrapper.readFloat32(),
            wrapper.readFloat32(),
            wrapper.readFloat32()
        )),
        max=Vector((
            wrapper.readFloat32(),
            wrapper.readFloat32(),
            wrapper.readFloat32()
        ))
    )

    wrapper.seek(28 + 4 + 16, relative=True)  # Unknown, fog scale, Unknown
    nodeDiffuseColor = Color((
        wrapper.readFloat32(),
        wrapper.readFloat32(),
        wrapper.readFloat32(),
    ))
    nodeAmbientColor = Color((
        wrapper.readFloat32(),
        wrapper.readFloat32(),
        wrapper.readFloat32(),
    ))
    nodeSpecularColor = Color((
        wrapper.readFloat32(),
        wrapper.readFloat32(),
        wrapper.readFloat32(),
    ))
    shininess = wrapper.readFloat32()
    shadow = wrapper.readUInt32() == 1
    beaming = wrapper.readUInt32() == 1
    render = wrapper.readUInt32() == 1
    transparencyHint = wrapper.readUInt32() == 1

    wrapper.seek(4, relative=True)  # Unknown
    textureStrings = list(map(
        lambda textureString: "" if textureString == "NULL" else textureString,
        [wrapper.readString(64) for i in range(4)]
    ))
    tileFade = wrapper.readUInt32() == 1
    controlFade = wrapper.readByte() == 1
    lightMapped = wrapper.readByte() == 1
    rotateTexture = wrapper.readByte() == 1

    wrapper.seek(1, relative=True)  # Unknown
    transparencyShift = wrapper.readFloat32()
    defaultRenderList = wrapper.readUInt32()
    preserveVColors = wrapper.readUInt32()
    fourCC = wrapper.readUInt32()

    wrapper.seek(4, relative=True)  # Unknown
    depthOffset = wrapper.readFloat32()
    coronaCenterMult = wrapper.readFloat32()
    fadeStartDistance = wrapper.readFloat32()
    distFromScreenCenterFace = wrapper.readByte() == 1

    wrapper.seek(3, relative=True)  # Unknown
    enlargeStartDistance = wrapper.readFloat32()
    affectedByWind = wrapper.readByte() == 1
    dampFactor = wrapper.readFloat32()
    blendGroup = wrapper.readUInt32()
    dayNightLightMaps = wrapper.readByte() == 1
    dayNightTransition = wrapper.readString(200)
    ignoreHitCheck = wrapper.readByte() == 1
    needsReflection = wrapper.readByte() == 1

    wrapper.seek(1, relative=True)  # Unknown
    reflectionPlaneNormal = [
        wrapper.readFloat32(),
        wrapper.readFloat32(),
        wrapper.readFloat32()
    ]
    reflectionPlaneDistance = wrapper.readFloat32()
    fadeOnCameraCollision = wrapper.readByte() == 1
    noSelfShadow = wrapper.readByte() == 1
    isReflected = wrapper.readByte() == 1
    onlyReflected = wrapper.readByte() == 1
    lightMapName = wrapper.readString(64)
    canDecal = wrapper.readByte() == 1
    multiBillBoard = wrapper.readByte() == 1
    ignoreLODReflection = wrapper.readByte() == 1

    wrapper.seek(1, relative=True)  # Unknown
    detailMapScape = wrapper.readFloat32()
    modelData.offsetTextureInfo = wrapper.readUInt32()

    wrapper.seek(modelData.offsetRawData, offMeshArrays)
    wrapper.seek(4, relative=True)

    vertexArrayDefinition = ArrayDefinition.fromWrapper(wrapper)
    normalsArrayDefinition = ArrayDefinition.fromWrapper(wrapper)
    tangentsArrayDefinition = ArrayDefinition.fromWrapper(wrapper)
    biNormalsArrayDefinition = ArrayDefinition.fromWrapper(wrapper)
    tVertsArrayDefinition = ArrayDefinition.fromWrapper(wrapper)
    unknownArrayDefinition = ArrayDefinition.fromWrapper(wrapper)
    facesArrayDefinition = ArrayDefinition.fromWrapper(wrapper)

    modelData.offsetTexData = wrapper.readUInt32() if modelData.fileVersion == 133 else modelData.offsetTexData

    if vertexArrayDefinition.nbUsedEntries == 0 or facesArrayDefinition.nbUsedEntries == 0:
        return

    material = readTextures(wrapper, modelData)
    material.setMaterialParameters(
        diffuseColor=nodeDiffuseColor,
        ambientColor=nodeAmbientColor,
        specularColor=nodeSpecularColor,
        shininess=shininess,
        shadow=shadow,
        beaming=beaming,
        render=render,
        transparencyHint=transparencyHint,
        textureStrings=textureStrings,
        tileFade=tileFade,
        controlFade=controlFade,
        lightMapped=lightMapped,
        rotateTexture=rotateTexture,
        transparencyShift=transparencyShift,
        defaultRenderList=defaultRenderList,
        preserveVColors=preserveVColors,
        fourCC=fourCC,
        depthOffset=depthOffset,
        coronaCenterMult=coronaCenterMult,
        fadeStartDistance=fadeStartDistance,
        distFromScreenCenterFace=distFromScreenCenterFace,
        enlargeStartDistance=enlargeStartDistance,
        affectedByWind=affectedByWind,
        dampFactor=dampFactor,
        blendGroup=blendGroup,
        dayNightLightMaps=dayNightLightMaps,
        dayNightTransition=dayNightTransition,
        ignoreHitCheck=ignoreHitCheck,
        needsReflection=needsReflection,
        reflectionPlaneNormal=reflectionPlaneNormal,
        reflectionPlaneDistance=reflectionPlaneDistance,
        fadeOnCameraCollision=fadeOnCameraCollision,
        noSelfShadow=noSelfShadow,
        isReflected=isReflected,
        onlyReflected=onlyReflected,
        lightMapName=lightMapName,
        canDecal=canDecal,
        multiBillBoard=multiBillBoard,
        ignoreLODReflection=ignoreLODReflection,
        detailMapScape=detailMapScape
    )
    meshBuffer = ModelMeshBuffer(
        material=material,
        boundingBox=nodeBoundingBox
    )


def loadNode(
    wrapper: FileWrapper,
    modelData: ModelData,
    parentMesh: ModelMesh = None,
    parentTransform: Matrix = _defaultMatrix()
):
    if parentMesh is None:  # root node
        parentMesh = ModelMesh()

    wrapper.seek(24 + 4, relative=True)  # Function pointers, inherit color flag
    id = wrapper.readUInt32()
    name = wrapper.readString(64)

    wrapper.seek(8, relative=True)  # parent geometry, parent node
    childrenNodesDef = ArrayDefinition.fromWrapper(wrapper)
    children = readArray(wrapper, modelData, childrenNodesDef, wrapper.readUInt32)

    controllerKeyDef = ArrayDefinition.fromWrapper(wrapper)
    controllerDataDef = ArrayDefinition.fromWrapper(wrapper)

    controllersData = getStaticNodeControllers(wrapper, modelData, controllerKeyDef, controllerDataDef)
    controllersData.globalTransform = parentTransform @ controllersData.localTransform

    wrapper.seek(4 + 8, relative=True)  # node flags/type, fixed rot + imposter group ?
    minLOD = wrapper.readInt32()
    maxLOD = wrapper.readInt32()
    type = wrapper.readUInt32()

    joint = parentMesh.getJointByName(name)
    if joint is None:
        joint = ModelJoint(
            localMatrix=controllersData.localTransform,
            globalMatrix=controllersData.globalTransform,
            name=name,
            animatedPosition=controllersData.position,
            animatedScale=controllersData.scale,
            animatedRotation=controllersData.rotation.invert()
        )
        parentMesh.joints.append(joint)

    print('load {} type {}'.format(name, hex(type)))
    if type == NodeType.NodeTypeTrimesh:
        pass
    elif type == NodeType.NodeTypeSpeedTree:
        pass
    elif type == NodeType.NodeTypeTexturePaint:
        pass

    for childOffset in children:
        wrapper.seek(modelData.offsetModelData + childOffset)
        loadNode(wrapper, modelData, parentMesh, parentTransform)

    return parentMesh


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

    # mesh = bpy.data.meshes.new(name=modelData.modelName)
    # obj = bpy.data.objects.new(modelName, mesh)
    #
    # bpy.context.collection.objects.link(obj)

    importedMeshData = loadNode(
        wrapper=wrapper,
        modelData=modelData,
        parentMesh=None,
        parentTransform=global_matrix if global_matrix else _defaultMatrix()
    )
    return {'FINISHED'}
