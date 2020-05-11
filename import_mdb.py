# nk2's craft made of plasticine (level: Kindergarten, 1 year)
# heavily based on https://github.com/JLouis-B/RedTools/blob/master/W2ENT_QT/IO_MeshLoader_WitcherMDL.cpp
import os
from collections import OrderedDict
from itertools import chain

import bpy
from bpy_extras.io_utils import unpack_list
from bpy_extras.object_utils import object_data_add
from typing import List, Optional, Tuple

from bpy_types import Object, Mesh
from mathutils import Matrix, Vector, Quaternion, Color

from .debug_utils import debugPrint as print, setDepth as debugSetDepth, increaseDepth as debugIncreaseDepth, \
    decreaseDepth as debugDecreaseDepth
from .model_types import ControllerType, NodeType
from .model_data import ModelData, StaticControllersData, ControllersData, ModelMesh, ModelJoint, _defaultMatrix, \
    ModelBoundingBox, ModelMaterial, ModelMeshBuffer, ModelVertex, ModelTextureLayer, ModelWeight, ModelBoundingSphere, \
    ModelAnimationNode, ModelPositionKey, ModelRotationKey, ModelScaleKey, ModelAnimationMeta
from .file_utils import FileWrapper, ArrayDefinition, readArray


#  Function that reads all controllers in mdb-eqsue format
def readNodeControllers(
    wrapper: FileWrapper,
    modelData: ModelData,
    controllerKeyDef: ArrayDefinition,
    controllerDataDef: ArrayDefinition
):
    debugIncreaseDepth()
    controllers = ControllersData.default()
    controllerData = readArray(wrapper, modelData, controllerDataDef, wrapper.readFloat32)
    back = wrapper.offset

    wrapper.seek(modelData.offsetModelData + controllerKeyDef.firstElemOffset)
    for i in range(controllerKeyDef.nbUsedEntries):
        controllerType = ControllerType(wrapper.readUInt32())
        nbRows = wrapper.readInt16()
        firstKeyIndex = wrapper.readInt16()
        firstValueIndex = wrapper.readInt16()
        nbColumns = wrapper.readUByte()

        wrapper.seek(1, relative=True)
        print('read node controller', type=controllerType)
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
                controllers.rotationTime.append(controllerData[firstKeyIndex + j])
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
        elif controllerType == ControllerType.ControllerSelfIllumColor:
            for j in range(nbRows):
                offset = j * nbColumns
                controllers.selfIllumColorTime.append(controllerData[firstKeyIndex + j])
                controllers.selfIllumColor.append(Color((
                    controllerData[offset + firstValueIndex],
                    controllerData[offset + firstValueIndex + 1],
                    controllerData[offset + firstValueIndex + 2]
                )))
        elif controllerType == ControllerType.ControllerAlpha:
            for j in range(nbRows):
                offset = j * nbColumns
                controllers.alphaTime.append(controllerData[firstKeyIndex + j])
                controllers.alpha.append(
                    controllerData[offset + firstValueIndex]
                )

    wrapper.seek(back)
    debugDecreaseDepth()
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


def getTexture(
    modelData: ModelData,
    name: str
):
    try:
        return next(
            list(filter(
                lambda path: os.path.exists(path),
                chain.from_iterable(map(
                    lambda ext: list(map(
                        lambda folder: os.path.join(modelData.baseDirectory, folder, '{}.{}'.format(name, ext)),
                        ['meshes00', 'textures00', 'textures01']
                    )),
                    ['dds', 'txi', 'jpg', 'jpeg']
                ))
            ))
        )
    except StopIteration:
        return None


def readTextures(
    wrapper: FileWrapper,
    modelData: ModelData
):
    wrapper.seek(
        modelData.offsetRawData + modelData.offsetTexData
            if modelData.fileVersion == 133
            else modelData.offsetTexData + modelData.offsetTextureInfo
    )

    textureCount = wrapper.readUInt32()
    offTexture = wrapper.readUInt32()

    materialContent = ""
    for i in range(textureCount):
        line = wrapper.readStringUntilNull()
        materialContent += "{}\n".format(line)

    return ModelMaterial.fromString(materialContent)


def evaluateTextures(
    modelData: ModelData,
    material: ModelMaterial,
    textureCount: int,
    staticTextureStrings: Optional[List[str]],
    tVertsArrayDefinitions: List[ArrayDefinition],
    lightMapDayNight: bool,
    lightMapName: str
):
    material.textures = OrderedDict((
        ('texture0', material.textures['texture0'] if 'texture0' in material.textures else ''),
        ('texture1', material.textures['texture1'] if 'texture1' in material.textures else ''),
        ('texture2', material.textures['texture2'] if 'texture2' in material.textures else ''),
        ('texture3', material.textures['texture3'] if 'texture3' in material.textures else '')
    ))

    for t in range(textureCount):
        textureType = 'texture{}'.format(t)
        if material.textures[textureType] == "" and staticTextureStrings is not None:
            material.textures[textureType] = staticTextureStrings[t]

        if tVertsArrayDefinitions[t].nbUsedEntries == 0:
            material.textures[textureType] = ""

        if material.textures[textureType] == "":
            continue

        if lightMapDayNight and material.textures[textureType] == lightMapName:
            if getTexture(modelData, material.textures[textureType] + "!d") is not None:  # dzien
                material.textures[textureType] = material.textures[textureType] + "!d"
            elif getTexture(modelData, material.textures[textureType] + "!r") is not None:  # rano
                material.textures[textureType] = material.textures[textureType] + "!r"
            elif getTexture(modelData, material.textures[textureType] + "!p") is not None:  # poludnie
                material.textures[textureType] = material.textures[textureType] + "!p"
            elif getTexture(modelData, material.textures[textureType] + "!w") is not None:  # wieczor
                material.textures[textureType] = material.textures[textureType] + "!w"
            elif getTexture(modelData, material.textures[textureType] + "!n") is not None:  # noc
                material.textures[textureType] = material.textures[textureType] + "!n"
            else:
                material.textures[textureType] = ""


def readMeshNode(
    wrapper: FileWrapper,
    modelData: ModelData,
    name: str
):
    debugIncreaseDepth()
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

    wrapper.seek(3, relative=True)  # Unknown
    dampFactor = wrapper.readFloat32()
    blendGroup = wrapper.readUInt32()
    dayNightLightMaps = wrapper.readByte() == 1
    dayNightTransition = wrapper.readString(200)
    ignoreHitCheck = wrapper.readByte() == 1
    needsReflection = wrapper.readByte() == 1

    wrapper.seek(1, relative=True)  # Unknown
    reflectionPlaneNormal = [
        wrapper.readFloat32() for i in range(3)
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
    enableSpecular = wrapper.readByte() == 1
    detailMapScape = wrapper.readFloat32()
    modelData.offsetTextureInfo = wrapper.readUInt32()

    wrapper.seek(modelData.offsetRawData + offMeshArrays)
    wrapper.seek(4, relative=True)

    vertexArrayDefinition = ArrayDefinition.fromWrapper(wrapper)
    normalsArrayDefinition = ArrayDefinition.fromWrapper(wrapper)
    tangentsArrayDefinition = ArrayDefinition.fromWrapper(wrapper)
    biNormalsArrayDefinition = ArrayDefinition.fromWrapper(wrapper)
    tVertsArrayDefinitions = [
        ArrayDefinition.fromWrapper(wrapper) for i in range(4)
    ]
    unknownArrayDefinition = ArrayDefinition.fromWrapper(wrapper)
    facesArrayDefinition = ArrayDefinition.fromWrapper(wrapper)

    modelData.offsetTexData = wrapper.readUInt32() if modelData.fileVersion == 133 else modelData.offsetTexData

    if vertexArrayDefinition.nbUsedEntries == 0 or facesArrayDefinition.nbUsedEntries == 0:
        debugDecreaseDepth()
        return

    material = readTextures(wrapper, modelData)
    evaluateTextures(modelData, material, 4, textureStrings, tVertsArrayDefinitions, dayNightLightMaps, lightMapName)
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
        detailMapScape=detailMapScape,
        enableSpecular=enableSpecular
    )
    meshBuffer = ModelMeshBuffer(
        name=name,
        material=material,
        boundingBox=nodeBoundingBox
    )
    meshBuffer.vertices = [
        ModelVertex() for i in range(max(
            vertexArrayDefinition.nbUsedEntries,
            normalsArrayDefinition.nbUsedEntries,
            tangentsArrayDefinition.nbUsedEntries,
            biNormalsArrayDefinition.nbUsedEntries
        ))
    ]

    wrapper.seek(modelData.offsetRawData + vertexArrayDefinition.firstElemOffset)
    for i in range(vertexArrayDefinition.nbUsedEntries):
        meshBuffer.vertices[i].position = Vector((
            wrapper.readFloat32(),
            wrapper.readFloat32(),
            wrapper.readFloat32()
        ))
        meshBuffer.vertices[i].color = Color((1.0, 1.0, 1.0))
        meshBuffer.vertices[i].tCoords = Vector((0.0, 0.0))

    wrapper.seek(modelData.offsetRawData + normalsArrayDefinition.firstElemOffset)
    for i in range(normalsArrayDefinition.nbUsedEntries):
        meshBuffer.vertices[i].normal = Vector((
            wrapper.readFloat32(),  # wrapper.readInt16() / 8192,
            wrapper.readFloat32(),  # wrapper.readInt16() / 8192,
            wrapper.readFloat32()  # wrapper.readInt16() / 8192
        ))

    wrapper.seek(modelData.offsetRawData + tangentsArrayDefinition.firstElemOffset)
    for i in range(tangentsArrayDefinition.nbUsedEntries):
        meshBuffer.vertices[i].tangent = Vector((
            wrapper.readFloat32(),  # wrapper.readInt16() / 8192,
            wrapper.readFloat32(),  # wrapper.readInt16() / 8192,
            wrapper.readFloat32()  # wrapper.readInt16() / 8192
        ))

    wrapper.seek(modelData.offsetRawData + biNormalsArrayDefinition.firstElemOffset)
    for i in range(biNormalsArrayDefinition.nbUsedEntries):
        meshBuffer.vertices[i].biNormal = Vector((
            wrapper.readFloat32(),  # wrapper.readInt16() / 8192,
            wrapper.readFloat32(),  # wrapper.readInt16() / 8192,
            wrapper.readFloat32()  # wrapper.readInt16() / 8192
        ))

    wrapper.seek(modelData.offsetRawData + facesArrayDefinition.firstElemOffset)
    for i in range(facesArrayDefinition.nbUsedEntries):
        wrapper.seek(4 * 4 + 4, relative=True)
        if modelData.fileVersion == 133:
            wrapper.seek(3 * 4, relative=True)

        meshBuffer.indices.append((
            wrapper.readInt32(),
            wrapper.readInt32(),
            wrapper.readInt32()
        ))

        if modelData.fileVersion == 133:
            wrapper.seek(4, relative=True)

    for t in range(len(material.textures)):
        wrapper.seek(modelData.offsetRawData + tVertsArrayDefinitions[t].firstElemOffset)
        for i in range(tVertsArrayDefinitions[t].nbUsedEntries):
            meshBuffer.vertices[i].tCoords = Vector((
                wrapper.readFloat32(),
                wrapper.readFloat32()
            ))

    debugDecreaseDepth()
    # TODO load custom materials based on textureStrings[0] (typically will be __shader__)
    return meshBuffer


def readTexturePaintNode(
    wrapper: FileWrapper,
    modelData: ModelData,
    name: str
):
    debugIncreaseDepth()
    layersArrayDefinitions = ArrayDefinition.fromWrapper(wrapper)

    wrapper.seek(28, relative=True)  # Unknown
    offMeshArrays = wrapper.readUInt32()
    sectorID0 = wrapper.readUInt32()
    sectorID1 = wrapper.readUInt32()
    sectorID2 = wrapper.readUInt32()
    sectorID3 = wrapper.readUInt32()
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
    shadow = wrapper.readUInt32() == 1
    render = wrapper.readUInt32() == 1
    tileFade = wrapper.readUInt32() == 1
    controlFade = wrapper.readByte() == 1
    lightMapped = wrapper.readByte() == 1
    rotateTexture = wrapper.readByte() == 1

    wrapper.seek(1, relative=True)  # Unknown
    transparencyShift = wrapper.readFloat32()
    defaultRenderList = wrapper.readUInt32()
    fourCC = wrapper.readUInt32()

    wrapper.seek(4, relative=True)  # Unknown
    depthOffset = wrapper.readFloat32()
    blendGroup = wrapper.readUInt32()
    dayNightLightMaps = wrapper.readByte() == 1
    dayNightTransition = wrapper.readString(200)
    ignoreHitCheck = wrapper.readByte() == 1
    needsReflection = wrapper.readByte() == 1

    wrapper.seek(1, relative=True)  # Unknown
    reflectionPlaneNormal = [
        wrapper.readFloat32() for i in range(3)
    ]
    reflectionPlaneDistance = wrapper.readFloat32()
    fadeOnCameraCollision = wrapper.readByte() == 1
    noSelfShadow = wrapper.readByte() == 1
    isReflected = wrapper.readByte() == 1

    wrapper.seek(1, relative=True)  # Unknown
    detailMapScape = wrapper.readFloat32()
    onlyReflected = wrapper.readByte() == 1
    lightMapName = wrapper.readString(64)
    canDecal = wrapper.readByte() == 1
    ignoreLODReflection = wrapper.readByte() == 1
    enableSpecular = wrapper.readByte() == 1

    wrapper.seek(modelData.offsetRawData + offMeshArrays)
    wrapper.seek(4, relative=True)
    vertexArrayDefinition = ArrayDefinition.fromWrapper(wrapper)
    normalsArrayDefinition = ArrayDefinition.fromWrapper(wrapper)
    tangentsArrayDefinition = ArrayDefinition.fromWrapper(wrapper)
    biNormalsArrayDefinition = ArrayDefinition.fromWrapper(wrapper)
    tVertsArrayDefinitions = [
        ArrayDefinition.fromWrapper(wrapper) for i in range(4)
    ]
    unknownArrayDefinition = ArrayDefinition.fromWrapper(wrapper)
    facesArrayDefinition = ArrayDefinition.fromWrapper(wrapper)

    if vertexArrayDefinition.nbUsedEntries == 0 or facesArrayDefinition.nbUsedEntries == 0:
        debugDecreaseDepth()
        return

    textureLayers = []
    for i in range(layersArrayDefinitions.nbUsedEntries):
        wrapper.seek(modelData.offsetRawData + layersArrayDefinitions.firstElemOffset + i * 52)
        textureLayer = ModelTextureLayer(hasTexture=wrapper.readByte() == 1)

        if not textureLayer.hasTexture:
            continue

        wrapper.seek(3 + 4, relative=True)  # Unknown, Offset to material
        textureLayer.texture = wrapper.readString(32)
        weightsArrayDefinition = ArrayDefinition.fromWrapper(wrapper)
        textureLayer.weights = readArray(wrapper, modelData, weightsArrayDefinition, wrapper.readFloat32)
        textureLayers.append(textureLayer)

    material = ModelMaterial(
        textures=OrderedDict(('texture0', lightMapName)),
        diffuseColor=nodeDiffuseColor,
        ambientColor=nodeAmbientColor,
        specularColor=nodeSpecularColor,
        shadow=shadow,
        render=render,
        textureStrings=[],
        tileFade=tileFade,
        controlFade=controlFade,
        lightMapped=lightMapped,
        rotateTexture=rotateTexture,
        transparencyShift=transparencyShift,
        defaultRenderList=defaultRenderList,
        fourCC=fourCC,
        depthOffset=depthOffset,
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
        ignoreLODReflection=ignoreLODReflection,
        detailMapScape=detailMapScape,
        enableSpecular=enableSpecular
    )
    evaluateTextures(modelData, material, 1, None, tVertsArrayDefinitions, dayNightLightMaps, lightMapName)
    meshBuffer = ModelMeshBuffer(
        name=name,
        material=material,
        boundingBox=nodeBoundingBox,
        textureLayers=textureLayers
    )
    meshBuffer.vertices = [
        ModelVertex() for i in range(max(
            vertexArrayDefinition.nbUsedEntries,
            normalsArrayDefinition.nbUsedEntries,
            tangentsArrayDefinition.nbUsedEntries,
            biNormalsArrayDefinition.nbUsedEntries
        ))
    ]

    wrapper.seek(modelData.offsetRawData + vertexArrayDefinition.firstElemOffset)
    for i in range(vertexArrayDefinition.nbUsedEntries):
        meshBuffer.vertices[i].position = Vector((
            wrapper.readFloat32(),
            wrapper.readFloat32(),
            wrapper.readFloat32()
        ))
        meshBuffer.vertices[i].color = Color((1.0, 1.0, 1.0))
        meshBuffer.vertices[i].tCoords = Vector((0.0, 0.0))

    wrapper.seek(modelData.offsetRawData + normalsArrayDefinition.firstElemOffset)
    for i in range(normalsArrayDefinition.nbUsedEntries):
        meshBuffer.vertices[i].normal = Vector((
            wrapper.readFloat32(),  # wrapper.readInt16() / 8192,
            wrapper.readFloat32(),  # wrapper.readInt16() / 8192,
            wrapper.readFloat32()  # wrapper.readInt16() / 8192
        ))

    wrapper.seek(modelData.offsetRawData + tangentsArrayDefinition.firstElemOffset)
    for i in range(tangentsArrayDefinition.nbUsedEntries):
        meshBuffer.vertices[i].tangent = Vector((
            wrapper.readFloat32(),  # wrapper.readInt16() / 8192,
            wrapper.readFloat32(),  # wrapper.readInt16() / 8192,
            wrapper.readFloat32()  # wrapper.readInt16() / 8192
        ))

    wrapper.seek(modelData.offsetRawData + biNormalsArrayDefinition.firstElemOffset)
    for i in range(biNormalsArrayDefinition.nbUsedEntries):
        meshBuffer.vertices[i].biNormal = Vector((
            wrapper.readFloat32(),  # wrapper.readInt16() / 8192,
            wrapper.readFloat32(),  # wrapper.readInt16() / 8192,
            wrapper.readFloat32()  # wrapper.readInt16() / 8192
        ))

    wrapper.seek(modelData.offsetRawData + facesArrayDefinition.firstElemOffset)
    for i in range(facesArrayDefinition.nbUsedEntries):
        wrapper.seek(4 * 4 + 4, relative=True)
        if modelData.fileVersion == 133:
            wrapper.seek(3 * 4, relative=True)

        meshBuffer.indices.append((
            wrapper.readInt32(),
            wrapper.readInt32(),
            wrapper.readInt32()
        ))

        if modelData.fileVersion == 133:
            wrapper.seek(4, relative=True)

    for t in range(len(material.textures)):
        wrapper.seek(modelData.offsetRawData + tVertsArrayDefinitions[t].firstElemOffset)
        for i in range(tVertsArrayDefinitions[t].nbUsedEntries):
            meshBuffer.vertices[i].tCoords = Vector((
                wrapper.readFloat32(),
                wrapper.readFloat32()
            ))

    debugDecreaseDepth()
    # TODO load custom materials based on textureStrings[0] (typically will be __shader__)
    return meshBuffer


def readSkinNode(
    wrapper: FileWrapper,
    modelData: ModelData,
    parentMesh: ModelMesh,
    name: str
):
    debugIncreaseDepth()
    # TODO UNITE MESH HEADER (0x0 to 0x270)
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

    wrapper.seek(3, relative=True)  # Unknown
    dampFactor = wrapper.readFloat32()
    blendGroup = wrapper.readUInt32()
    dayNightLightMaps = wrapper.readByte()
    dayNightTransition = wrapper.readString(200)
    ignoreHitCheck = wrapper.readByte() == 1
    needsReflection = wrapper.readByte() == 1

    wrapper.seek(1, relative=True)  # Unknown
    reflectionPlaneNormal = [
        wrapper.readFloat32() for i in range(3)
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
    enableSpecular = wrapper.readByte() == 1
    detailMapScape = wrapper.readFloat32()
    modelData.offsetTextureInfo = wrapper.readUInt32()

    wrapper.seek(4, relative=True)
    bonesArrayDefinition = ArrayDefinition.fromWrapper(wrapper)

    back = wrapper.offset
    wrapper.seek(modelData.offsetTexData + bonesArrayDefinition.firstElemOffset)
    bones = []
    for i in range(bonesArrayDefinition.nbUsedEntries):
        boneId = wrapper.readUInt32()
        boneName = wrapper.readString(92).split('+')[0]  # FIXME seems to collect garbage with name
        joint = parentMesh.getJointByName(boneName)
        bones.append(joint)

    wrapper.seek(back)
    wrapper.seek(4, relative=True)
    vertexArrayDefinition = ArrayDefinition.fromWrapper(wrapper)
    normalsArrayDefinition = ArrayDefinition.fromWrapper(wrapper)
    tangentsArrayDefinition = ArrayDefinition.fromWrapper(wrapper)
    biNormalsArrayDefinition = ArrayDefinition.fromWrapper(wrapper)
    tVertsArrayDefinitions = [
        ArrayDefinition.fromWrapper(wrapper) for i in range(4)
    ]
    unknownArrayDefinition = ArrayDefinition.fromWrapper(wrapper)
    facesArrayDefinition = ArrayDefinition.fromWrapper(wrapper)

    print(vertexArrayDefinition, facesArrayDefinition)

    modelData.offsetTexData = wrapper.readUInt32() if modelData.fileVersion == 133 else modelData.offsetTexData

    if vertexArrayDefinition.nbUsedEntries == 0 or facesArrayDefinition.nbUsedEntries == 0:
        debugDecreaseDepth()
        return

    wrapper.seek(24 + 12, relative=True)
    weightsArrayDefinition = ArrayDefinition.fromWrapper(wrapper)
    weights = readArray(wrapper, modelData, weightsArrayDefinition, wrapper.readFloat32)
    bonesArrayDefinition = ArrayDefinition.fromWrapper(wrapper)
    bones = readArray(wrapper, modelData, bonesArrayDefinition, wrapper.readUByte)

    material = readTextures(wrapper, modelData)
    evaluateTextures(modelData, material, 4, textureStrings, tVertsArrayDefinitions, dayNightLightMaps, lightMapName)
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
        detailMapScape=detailMapScape,
        enableSpecular=enableSpecular
    )
    meshBuffer = ModelMeshBuffer(
        name=name,
        material=material,
        boundingBox=nodeBoundingBox
    )
    meshBuffer.vertices = [
        ModelVertex() for i in range(max(
            vertexArrayDefinition.nbUsedEntries,
            normalsArrayDefinition.nbUsedEntries,
            tangentsArrayDefinition.nbUsedEntries,
            biNormalsArrayDefinition.nbUsedEntries
        ))
    ]

    wrapper.seek(modelData.offsetRawData + vertexArrayDefinition.firstElemOffset)
    skinningIndex = 0
    for i in range(vertexArrayDefinition.nbUsedEntries):
        meshBuffer.vertices[i].position = Vector((
            wrapper.readFloat32(),
            wrapper.readFloat32(),
            wrapper.readFloat32()
        ))
        meshBuffer.vertices[i].color = Color((1.0, 1.0, 1.0))
        meshBuffer.vertices[i].tCoords = Vector((0.0, 0.0))
        for j in range(4):  # Skinning of the vertex
            currentSkinningIndex = skinningIndex
            skinningIndex += 1
            boneId = bones[currentSkinningIndex]
            if boneId == 255:
                continue

            if boneId < len(bones):
                weight = weights[currentSkinningIndex]
                parentMesh.weights.append(ModelWeight(
                    vertexId=i,
                    strength=weight
                ))

    wrapper.seek(modelData.offsetRawData + normalsArrayDefinition.firstElemOffset)
    for i in range(normalsArrayDefinition.nbUsedEntries):
        meshBuffer.vertices[i].normal = Vector((
            wrapper.readFloat32(),  # wrapper.readInt16() / 8192,
            wrapper.readFloat32(),  # wrapper.readInt16() / 8192,
            wrapper.readFloat32()  # wrapper.readInt16() / 8192
        ))

    wrapper.seek(modelData.offsetRawData + tangentsArrayDefinition.firstElemOffset)
    for i in range(tangentsArrayDefinition.nbUsedEntries):
        meshBuffer.vertices[i].tangent = Vector((
            wrapper.readFloat32(),  # wrapper.readInt16() / 8192,
            wrapper.readFloat32(),  # wrapper.readInt16() / 8192,
            wrapper.readFloat32()  # wrapper.readInt16() / 8192
        ))

    wrapper.seek(modelData.offsetRawData + biNormalsArrayDefinition.firstElemOffset)
    for i in range(biNormalsArrayDefinition.nbUsedEntries):
        meshBuffer.vertices[i].biNormal = Vector((
            wrapper.readFloat32(),  # wrapper.readInt16() / 8192,
            wrapper.readFloat32(),  # wrapper.readInt16() / 8192,
            wrapper.readFloat32()  # wrapper.readInt16() / 8192
        ))

    wrapper.seek(modelData.offsetRawData + facesArrayDefinition.firstElemOffset)
    for i in range(facesArrayDefinition.nbUsedEntries):
        wrapper.seek(4 * 4 + 4, relative=True)
        if modelData.fileVersion == 133:
            wrapper.seek(3 * 4, relative=True)

        meshBuffer.indices.append((
            wrapper.readInt32(),
            wrapper.readInt32(),
            wrapper.readInt32()
        ))

        if modelData.fileVersion == 133:
            wrapper.seek(4, relative=True)

    for t in range(len(material.textures)):
        wrapper.seek(modelData.offsetRawData + tVertsArrayDefinitions[t].firstElemOffset)
        for i in range(tVertsArrayDefinitions[t].nbUsedEntries):
            meshBuffer.vertices[i].tCoords = Vector((
                wrapper.readFloat32(),
                wrapper.readFloat32()
            ))

    debugDecreaseDepth()
    # TODO load custom materials based on textureStrings[0] (typically will be __shader__)
    return meshBuffer


def loadSkinNode(
    wrapper: FileWrapper,
    modelData: ModelData,
    joint: ModelJoint,
    parentMesh: ModelMesh
):
    debugIncreaseDepth()
    print('post load skin node', name=joint.name)
    meshBuffer = readSkinNode(
        wrapper=wrapper,
        modelData=modelData,
        parentMesh=parentMesh,
        name=joint.name
    )
    if meshBuffer is not None:
        parentMesh.meshBuffers.append(meshBuffer)
        joint.attachedMeshes.append(meshBuffer)
    debugDecreaseDepth()


def loadNode(
    wrapper: FileWrapper,
    modelData: ModelData,
    parentMesh: ModelMesh = None,
    parentTransform: Matrix = _defaultMatrix(),
    # why the fuck in petooh THIS IS A POINTER FOR EVERY RECURSIVE CALL?!
    postLoad: List[Tuple[int, StaticControllersData, ModelJoint]] = []
):
    debugIncreaseDepth()
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
    type = NodeType(wrapper.readUInt32())

    joint = parentMesh.getJointByName(name)
    if joint is None:
        joint = ModelJoint(
            localMatrix=controllersData.localTransform,
            globalMatrix=controllersData.globalTransform,
            name=name,
            animatedPosition=controllersData.position,
            animatedScale=controllersData.scale,
            animatedRotation=controllersData.rotation#.invert()
        )
        parentMesh.joints.append(joint)

    print('load node', name=name, type=type)

    meshBuffer = None
    if type == NodeType.NodeTypeTrimesh:
        meshBuffer = readMeshNode(wrapper, modelData, joint.name)
    elif type == NodeType.NodeTypeSkin:
        # these should be loaded after other types
        postLoad.append((wrapper.offset, controllersData, joint))
    elif type == NodeType.NodeTypeSpeedTree:
        print('spt node should be loaded')
        # TODO SPT NODE LOADING
    elif type == NodeType.NodeTypeTexturePaint:
        meshBuffer = readTexturePaintNode(wrapper, modelData, joint.name)

    if meshBuffer is not None:
        print('attach buffer')
        parentMesh.meshBuffers.append(meshBuffer)
        joint.attachedMeshes.append(meshBuffer)

    for childOffset in children:
        wrapper.seek(modelData.offsetModelData + childOffset)
        _, postLoadChild = loadNode(wrapper, modelData, parentMesh, parentTransform, [])
        postLoad += postLoadChild

    debugDecreaseDepth()
    return parentMesh, postLoad


def readAnimationNode(
    wrapper: FileWrapper,
    modelData: ModelData,
    parentMesh: ModelMesh,
    children: List[ModelAnimationNode] = []
):
    debugIncreaseDepth()
    wrapper.seek(24 + 4, relative=True)  # Function pointers, inherit color flag
    id = wrapper.readUInt32()
    name = wrapper.readString(64)

    wrapper.seek(8, relative=True)  # parent geometry + parent node
    childNodesArrayDefinition = ArrayDefinition.fromWrapper(wrapper)
    childNodes = readArray(wrapper, modelData, childNodesArrayDefinition, wrapper.readUInt32)

    controllerKeyArrayDefinition = ArrayDefinition.fromWrapper(wrapper)
    controllerDataArrayDefinition = ArrayDefinition.fromWrapper(wrapper)
    controllers = readNodeControllers(wrapper, modelData, controllerKeyArrayDefinition, controllerDataArrayDefinition)

    wrapper.seek(4 + 8, relative=True)  # node flags/type, fixed rot + imposter group ?
    minLOD = wrapper.readFloat32()
    maxLOD = wrapper.readFloat32()
    type = NodeType(wrapper.readUInt32())

    animation = ModelAnimationNode(
        id=id,
        name=name,
        minLOD=minLOD,
        maxLOD=maxLOD,
        joint=parentMesh.getJointByName(name)
    )

    print('read animation node', id=id, name=name)
    if animation.joint is not None:
        for i in range(len(controllers.position)):
            animation.positionKeys.append(ModelPositionKey(
                frame=controllers.positionTime[i],
                position=controllers.position[i]
            ))
        for i in range(len(controllers.rotation)):
            animation.rotationKeys.append(ModelRotationKey(
                frame=controllers.rotationTime[i],
                rotation=controllers.rotation[i]
            ))
        for i in range(len(controllers.scale)):
            animation.scaleKeys.append(ModelScaleKey(
                frame=controllers.scaleTime[i],
                scale=controllers.scale[i]
            ))
        # TODO check if other types of controllers required

    for childNodeOffset in childNodes:
        wrapper.seek(modelData.offsetModelData + childNodeOffset)
        animation.children.append(readAnimationNode(wrapper, modelData, parentMesh, []))

    debugDecreaseDepth()
    return animation


def loadAnimations(
    wrapper: FileWrapper,
    modelData: ModelData,
    parentMesh: ModelMesh
):
    debugIncreaseDepth()
    wrapper.seek(
        modelData.offsetModelData + modelData.offsetRawData
            if modelData.fileVersion == 133
            else modelData.offsetTexData
    )
    chunkStart = wrapper.offset

    wrapper.seek(4, relative=True)
    animationsArrayDefinition = ArrayDefinition.fromWrapper(wrapper)
    wrapper.seek(chunkStart + animationsArrayDefinition.firstElemOffset)
    for i in range(animationsArrayDefinition.nbUsedEntries):
        animOffset = wrapper.readUInt32()
        back = wrapper.offset

        wrapper.seek(modelData.offsetModelData + animOffset)
        wrapper.seek(8, relative=True)
        animationName = wrapper.readString(64)
        offsetRootNode = wrapper.readUInt32()

        wrapper.seek(32, relative=True)
        geometryType = wrapper.readUByte()

        wrapper.seek(3, relative=True)
        animationLength = wrapper.readFloat32()
        transitionTime = wrapper.readFloat32()
        animationRootName = wrapper.readString(64)
        eventArrayDef = ArrayDefinition.fromWrapper(wrapper)
        animBox = ModelBoundingBox(
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
        animSphere = ModelBoundingSphere(
            x=wrapper.readFloat32(),
            y=wrapper.readFloat32(),
            z=wrapper.readFloat32(),
            radius=wrapper.readFloat32(),
        )

        print('read animation', rootName=animationRootName, name=animationName, length=animationLength)

        wrapper.seek(4, relative=True)  # Unknown
        wrapper.seek(modelData.offsetModelData + offsetRootNode)
        animation = readAnimationNode(wrapper, modelData, parentMesh)

        parentMesh.animations.append(ModelAnimationMeta(
            name=animationName,
            rootName=animationRootName,
            animationNode=animation,
            length=animationLength,
            transitionTime=transitionTime,
            animationBox=animBox,
            animationSphere=animSphere
        ))

        wrapper.seek(back)
    debugDecreaseDepth()


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
        offsetRawData=wrapper.readUInt32() + offsetModelData if fileVersion == 133 else offsetModelData,
        sizeRawData=wrapper.readUInt32() if fileVersion == 133 else 0,
        offsetTexData=wrapper.readUInt32() + offsetModelData if fileVersion == 136 else offsetModelData,
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


# ---------------------------------------------------------------------
# ---------------------------------------------------------------------
# -----------------------------BLENDER---------------------------------
# ---------------------------------------------------------------------
# ---------------------------------------------------------------------


def wrapVerticesToBlender(
    vertices: List[ModelVertex],
    indices: List[Tuple[int, int, int]]
):
    vertexes = []
    faces = []
    normals = []
    tangents = []
    biNormals = []

    for i in range(len(vertices)):
        vertex = vertices[i]

        vertexes.append((vertex.position.x, vertex.position.y, vertex.position.z))
        normals.append((vertex.normal.x, vertex.normal.y, vertex.normal.z))
        tangents.append(
            (vertex.tangent.x, vertex.tangent.y, vertex.tangent.z)
                if vertex.tangent is not None
                else (0, 0, 0)
        )
        biNormals.append(
            (vertex.biNormal.x, vertex.biNormal.y, vertex.biNormal.z)
                if vertex.biNormal is not None
                else (0, 0, 0)
        )

    for indice in indices:
        faces.append(indice)

    return vertexes, faces, normals, tangents, biNormals


def wrapToBlender(
    context,
    modelData: ModelData,
    modelMesh: ModelMesh
):
    for buffer in modelMesh.meshBuffers:
        print('wrap to blender', name=buffer.name)
        mesh: Mesh = bpy.data.meshes.new(name="mesh_{}".format(buffer.name))
        obj: Object = bpy.data.objects.new(buffer.name, mesh)
        bpy.context.collection.objects.link(obj)

        vertices, faces, normals, tangents, biNormals = wrapVerticesToBlender(buffer.vertices, buffer.indices)
        mesh.from_pydata(vertices, [], faces)
        mesh.vertices.foreach_set('normal', unpack_list(normals))
        mesh.loops.foreach_set('tangent', unpack_list(tangents))
        mesh.loops.foreach_set('bitangent', unpack_list(biNormals))


def load(
    operator,
    context,
    filepath="",
    base_path=None,
    global_matrix: Matrix = None,
):
    debugSetDepth(0)
    modelName, modelExtension = os.path.basename(filepath).split('.')
    baseDirectory = os.path.join(os.path.dirname(filepath), base_path)

    wrapper = FileWrapper.fromFile(open(filepath, "rb"))

    modelData = loadMeta(wrapper, baseDirectory, modelName)
    print(name=modelData.modelName, version=modelData.fileVersion)

    wrapper.seek(modelData.offsetModelData + modelData.offsetRootNode)

    importedMeshData, postLoad = loadNode(
        wrapper=wrapper,
        modelData=modelData,
        parentMesh=None,
        parentTransform=global_matrix if global_matrix else _defaultMatrix()
    )

    debugSetDepth(0)
    for offset, controllersData, joint in postLoad:
        wrapper.seek(offset)
        loadSkinNode(
            wrapper=wrapper,
            modelData=modelData,
            parentMesh=importedMeshData,
            joint=joint
        )

    debugSetDepth(0)
    loadAnimations(
        wrapper=wrapper,
        modelData=modelData,
        parentMesh=importedMeshData
    )

    debugSetDepth(0)
    wrapToBlender(
        context=context,
        modelData=modelData,
        modelMesh=importedMeshData
    )

    return {'FINISHED'}
