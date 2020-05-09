#  data layer of parser
#  [notification to myself]
#  [notification to myself] DONT EVEN TRY TO USE BLENDER OBJECT TYPES HERE, BASTARD!
#  [notification to myself]
import os
import re
from collections import OrderedDict
from enum import Enum

from mathutils import Vector, Quaternion, Matrix, Color, Euler
from typing import List, Tuple, Dict, OrderedDict as TOrderedDict


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
                 sizeTexData: int,
                 offsetRootNode: int,
                 modelType: int,
                 firstLOD: float,
                 lastLOD: float,
                 detailMap: str,
                 modelScale: float,
                 superModel: str,
                 animationScale: float
                 ):
        super(object, self).__init__()
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
        self.offsetRootNode = offsetRootNode
        self.modelType = modelType
        self.firstLOD = firstLOD
        self.lastLOD = lastLOD
        self.detailMap = detailMap
        self.modelScale = modelScale
        self.superModel = superModel
        self.animationScale = animationScale

    def __repr__(self) -> str:
        return "{}({!r})".format(self.__class__.__name__, self.__dict__)


def _defaultMatrix():
    return Matrix([
        [0, 0, 0, 0],
        [0, 0, 0, 0],
        [0, 0, 0, 0],
        [0, 0, 0, 0]
    ])


class StaticControllersData(object):
    def __init__(self, position: Vector, rotation: Quaternion, scale: Vector, localTransform: Matrix,
                 globalTransform: Matrix, alpha: float, selfIllumColor: Color = None):
        super().__init__()
        self.position = position
        self.rotation = rotation
        self.scale = scale
        self.localTransform = localTransform
        self.globalTransform = globalTransform
        self.alpha = alpha
        self.selfIllumColor = selfIllumColor

    def __repr__(self):
        return "{}({!r})".format(self.__class__.__name__, self.__dict__)

    def computeLocalTransform(self):
        qPos = Matrix.Translation((self.position.x, self.position.y, self.position.z))
        qRot = Euler((self.rotation.x, self.rotation.y, self.rotation.z)).to_matrix().to_4x4()
        qScale = Matrix.Scale(1.0, 4, (self.scale.x, self.scale.y, self.scale.z))

        self.localTransform = qPos @ qRot @ qScale

    @classmethod
    def default(cls):
        return cls(
            Vector((.0, .0, .0)),
            Quaternion((.0, .0, .0, .0)),
            Vector((1.0, 1.0, 1.0)),
            _defaultMatrix(),
            _defaultMatrix(),
            1.0,
            None
        )


class ControllersData(object):
    def __init__(self,
                 positionTime: List[float],
                 position: List[Vector],
                 rotationTime: List[float],
                 rotation: List[Quaternion],
                 scaleTime: List[float],
                 scale: List[Vector],
                 alphaTime: List[float],
                 alpha: List[float],
                 selfIllumColorTime: List[float],
                 selfIllumColor: List[Color]
                 ):
        super().__init__()
        self.positionTime = positionTime
        self.position = position
        self.rotationTime = rotationTime
        self.rotation = rotation
        self.scaleTime = scaleTime
        self.scale = scale
        self.alphaTime = alphaTime
        self.alpha = alpha
        self.selfIllumColorTime = selfIllumColorTime
        self.selfIllumColor = selfIllumColor

    @classmethod
    def default(cls):
        return cls([], [], [], [], [], [], [], [], [], [])


class ModelWeight(object):
    def __init__(self,
                 vertexId: int,
                 strength: float,
                 staticPos: Vector = None,
                 staticNormal: Vector = None
                 ):
        super().__init__()
        self.vertexId = vertexId
        self.strength = strength
        self.staticPos = staticPos
        self.staticNormal = staticNormal

    def __repr__(self) -> str:
        return "{}({!r})".format(self.__class__.__name__, self.__dict__)


class ModelPositionKey(object):
    def __init__(self, frame: int, position: Vector):
        super().__init__()
        self.frame = frame
        self.position = position

    def __repr__(self) -> str:
        return "{}({!r})".format(self.__class__.__name__, self.__dict__)


class ModelScaleKey(object):
    def __init__(self, frame: int, scale: Vector):
        super().__init__()
        self.frame = frame
        self.scale = scale

    def __repr__(self) -> str:
        return "{}({!r})".format(self.__class__.__name__, self.__dict__)


class ModelRotationKey(object):
    def __init__(self, frame: int, rotation: Quaternion):
        super().__init__()
        self.frame = frame
        self.rotation = rotation

    def __repr__(self) -> str:
        return "{}({!r})".format(self.__class__.__name__, self.__dict__)


class ModelJoint(object):
    def __init__(self,
                 name: str,
                 animatedPosition: Vector,
                 animatedScale: Vector,
                 animatedRotation: Vector,
                 localMatrix: Matrix,
                 globalMatrix: Matrix,
                 globalAnimatedMatrix: Matrix = _defaultMatrix(),
                 localAnimatedMatrix: Matrix = _defaultMatrix(),
                 children: list = [],
                 attachedMeshes: list = [],
                 weights: List[ModelWeight] = [],
                 positionKeys: List[ModelPositionKey] = [],
                 scaleKeys: List[ModelScaleKey] = [],
                 rotationKeys: List[ModelRotationKey] = [],
                 ):
        super(object, self).__init__()
        self.name = name
        self.animatedPosition = animatedPosition
        self.animatedScale = animatedScale
        self.animatedRotation = animatedRotation
        self.localMatrix = localMatrix
        self.globalMatrix = globalMatrix
        self.globalAnimatedMatrix = globalAnimatedMatrix
        self.localAnimatedMatrix = localAnimatedMatrix
        self.children = children
        self.attachedMeshes = attachedMeshes
        self.weights = weights
        self.positionKeys = positionKeys
        self.scaleKeys = scaleKeys
        self.rotationKeys = rotationKeys

    def __repr__(self) -> str:
        return "{}({!r})".format(self.__class__.__name__, self.__dict__)


class ModelBoundingBox(object):
    def __init__(self, min: Vector, max: Vector):
        super().__init__()
        self.min = min
        self.max = max

    def __repr__(self) -> str:
        return "{}({!r})".format(self.__class__.__name__, self.__dict__)


class ModelVertex(object):
    def __init__(self,
                 position: Vector = None,
                 normal: Vector = None,
                 color: Color = None,
                 tCoords: Vector = None,
                 biNormal: Vector = None,
                 tangent: Vector = None
                 ):
        super().__init__()
        self.position = position
        self.normal = normal
        self.color = color
        self.tCoords = tCoords
        self.biNormal = biNormal
        self.tangent = tangent

    def __repr__(self) -> str:
        return "{}({!r})".format(self.__class__.__name__, self.__dict__)

    @classmethod
    def fromCoords(cls, x: float, y: float, z: float, nx: float, ny: float, nz: float, color: Color, tu: float,
                   tv: float):
        return cls(
            Vector((x, y, z)),
            Vector((nx, ny, nz)),
            color,
            Vector((tu, tv))
        )


class ModelMaterialType(Enum):
    ModelMaterialTypeSolid = 0x0
    ModelMaterialTypeTransparent = 0x1


class ModelMaterial(object):
    def __init__(self,
                 shader: str = '',
                 textures: TOrderedDict[str, str] = OrderedDict(),
                 bumpmaps: TOrderedDict[str, str] = OrderedDict(),
                 floats: TOrderedDict[str, float] = OrderedDict(),
                 vectors: TOrderedDict[str, Vector] = OrderedDict(),
                 diffuseColor: Color = None,
                 ambientColor: Color = None,
                 specularColor: Color = None,
                 shininess: float = None,
                 shadow: bool = None,
                 beaming: bool = None,
                 render: bool = None,
                 transparencyHint: bool = None,
                 textureStrings: List[str] = None,
                 tileFade: bool = None,
                 controlFade: bool = None,
                 lightMapped: bool = None,
                 rotateTexture: bool = None,
                 transparencyShift: float = None,
                 defaultRenderList: int = None,
                 preserveVColors: int = None,
                 fourCC: int = None,
                 depthOffset: float = None,
                 coronaCenterMult: float = None,
                 fadeStartDistance: float = None,
                 distFromScreenCenterFace: bool = None,
                 enlargeStartDistance: float = None,
                 affectedByWind: bool = None,
                 dampFactor: float = None,
                 blendGroup: int = None,
                 dayNightLightMaps: bool = None,
                 dayNightTransition: str = None,
                 ignoreHitCheck: bool = None,
                 needsReflection: bool = None,
                 reflectionPlaneNormal: List[float] = None,
                 reflectionPlaneDistance: float = None,
                 fadeOnCameraCollision: bool = None,
                 noSelfShadow: bool = None,
                 isReflected: bool = None,
                 onlyReflected: bool = None,
                 lightMapName: str = None,
                 canDecal: bool = None,
                 multiBillBoard: bool = None,
                 ignoreLODReflection: bool = None,
                 detailMapScape: float = None,
                 enableSpecular: bool = None,
                 ):
        super().__init__()
        self.shader = shader
        self.textures = textures
        self.bumpmaps = bumpmaps
        self.floats = floats
        self.vectors = vectors
        self.diffuseColor = diffuseColor
        self.ambientColor = ambientColor
        self.specularColor = specularColor
        self.shininess = shininess
        self.shadow = shadow
        self.beaming = beaming
        self.render = render
        self.transparencyHint = transparencyHint
        self.textureStrings = textureStrings
        self.tileFade = tileFade
        self.controlFade = controlFade
        self.lightMapped = lightMapped
        self.rotateTexture = rotateTexture
        self.transparencyShift = transparencyShift
        self.defaultRenderList = defaultRenderList
        self.preserveVColors = preserveVColors
        self.fourCC = fourCC
        self.depthOffset = depthOffset
        self.coronaCenterMult = coronaCenterMult
        self.fadeStartDistance = fadeStartDistance
        self.distFromScreenCenterFace = distFromScreenCenterFace
        self.enlargeStartDistance = enlargeStartDistance
        self.affectedByWind = affectedByWind
        self.dampFactor = dampFactor
        self.blendGroup = blendGroup
        self.dayNightLightMaps = dayNightLightMaps
        self.dayNightTransition = dayNightTransition
        self.ignoreHitCheck = ignoreHitCheck
        self.needsReflection = needsReflection
        self.reflectionPlaneNormal = reflectionPlaneNormal
        self.reflectionPlaneDistance = reflectionPlaneDistance
        self.fadeOnCameraCollision = fadeOnCameraCollision
        self.noSelfShadow = noSelfShadow
        self.isReflected = isReflected
        self.onlyReflected = onlyReflected
        self.lightMapName = lightMapName
        self.canDecal = canDecal
        self.multiBillBoard = multiBillBoard
        self.ignoreLODReflection = ignoreLODReflection
        self.detailMapScape = detailMapScape
        self.enableSpecular = enableSpecular

    def setMaterialParameters(self,
                              diffuseColor: Color = None,
                              ambientColor: Color = None,
                              specularColor: Color = None,
                              shininess: float = None,
                              shadow: bool = None,
                              beaming: bool = None,
                              render: bool = None,
                              transparencyHint: bool = None,
                              textureStrings: List[str] = None,
                              tileFade: bool = None,
                              controlFade: bool = None,
                              lightMapped: bool = None,
                              rotateTexture: bool = None,
                              transparencyShift: float = None,
                              defaultRenderList: int = None,
                              preserveVColors: int = None,
                              fourCC: int = None,
                              depthOffset: float = None,
                              coronaCenterMult: float = None,
                              fadeStartDistance: float = None,
                              distFromScreenCenterFace: bool = None,
                              enlargeStartDistance: float = None,
                              affectedByWind: bool = None,
                              dampFactor: float = None,
                              blendGroup: int = None,
                              dayNightLightMaps: bool = None,
                              dayNightTransition: str = None,
                              ignoreHitCheck: bool = None,
                              needsReflection: bool = None,
                              reflectionPlaneNormal: List[float] = None,
                              reflectionPlaneDistance: float = None,
                              fadeOnCameraCollision: bool = None,
                              noSelfShadow: bool = None,
                              isReflected: bool = None,
                              onlyReflected: bool = None,
                              lightMapName: str = None,
                              canDecal: bool = None,
                              multiBillBoard: bool = None,
                              ignoreLODReflection: bool = None,
                              detailMapScape: float = None,
                              enableSpecular: bool = None
                              ):
        self.diffuseColor = diffuseColor if diffuseColor is not None else self.diffuseColor
        self.ambientColor = ambientColor if ambientColor is not None else self.ambientColor
        self.specularColor = specularColor if specularColor is not None else self.specularColor
        self.shininess = shininess if shininess is not None else self.shininess
        self.shadow = shadow if shadow is not None else self.shadow
        self.beaming = beaming if beaming is not None else self.beaming
        self.render = render if render is not None else self.render
        self.transparencyHint = transparencyHint if transparencyHint is not None else self.transparencyHint
        self.textureStrings = textureStrings if textureStrings is not None else self.textureStrings
        self.tileFade = tileFade if tileFade is not None else self.tileFade
        self.controlFade = controlFade if controlFade is not None else self.controlFade
        self.lightMapped = lightMapped if lightMapped is not None else self.lightMapped
        self.rotateTexture = rotateTexture if rotateTexture is not None else self.rotateTexture
        self.transparencyShift = transparencyShift if transparencyShift is not None else self.transparencyShift
        self.defaultRenderList = defaultRenderList if defaultRenderList is not None else self.defaultRenderList
        self.preserveVColors = preserveVColors if preserveVColors is not None else self.preserveVColors
        self.fourCC = fourCC if fourCC is not None else self.fourCC
        self.depthOffset = depthOffset if depthOffset is not None else self.depthOffset
        self.coronaCenterMult = coronaCenterMult if coronaCenterMult is not None else self.coronaCenterMult
        self.fadeStartDistance = fadeStartDistance if fadeStartDistance is not None else self.fadeStartDistance
        self.distFromScreenCenterFace = distFromScreenCenterFace if distFromScreenCenterFace is not None else self.distFromScreenCenterFace
        self.enlargeStartDistance = enlargeStartDistance if enlargeStartDistance is not None else self.enlargeStartDistance
        self.affectedByWind = affectedByWind if affectedByWind is not None else self.affectedByWind
        self.dampFactor = dampFactor if dampFactor is not None else self.dampFactor
        self.blendGroup = blendGroup if blendGroup is not None else self.blendGroup
        self.dayNightLightMaps = dayNightLightMaps if dayNightLightMaps is not None else self.dayNightLightMaps
        self.dayNightTransition = dayNightTransition if dayNightTransition is not None else self.dayNightTransition
        self.ignoreHitCheck = ignoreHitCheck if ignoreHitCheck is not None else self.ignoreHitCheck
        self.needsReflection = needsReflection if needsReflection is not None else self.needsReflection
        self.reflectionPlaneNormal = reflectionPlaneNormal if reflectionPlaneNormal is not None else self.reflectionPlaneNormal
        self.reflectionPlaneDistance = reflectionPlaneDistance if reflectionPlaneDistance is not None else self.reflectionPlaneDistance
        self.fadeOnCameraCollision = fadeOnCameraCollision if fadeOnCameraCollision is not None else self.fadeOnCameraCollision
        self.noSelfShadow = noSelfShadow if noSelfShadow is not None else self.noSelfShadow
        self.isReflected = isReflected if isReflected is not None else self.isReflected
        self.onlyReflected = onlyReflected if onlyReflected is not None else self.onlyReflected
        self.lightMapName = lightMapName if lightMapName is not None else self.lightMapName
        self.canDecal = canDecal if canDecal is not None else self.canDecal
        self.multiBillBoard = multiBillBoard if multiBillBoard is not None else self.multiBillBoard
        self.ignoreLODReflection = ignoreLODReflection if ignoreLODReflection is not None else self.ignoreLODReflection
        self.detailMapScape = detailMapScape if detailMapScape is not None else self.detailMapScape
        self.enableSpecular = enableSpecular if enableSpecular is not None else self.enableSpecular

    def getMaterialTypeFromShader(self):
        return ModelMaterialType.ModelMaterialTypeTransparent \
            if self.shader in ["dblsided_atest", "leaves", "leaves_lm", "leaves_lm_bill", "leaves_singles"] \
            else ModelMaterialType.ModelMaterialTypeSolid

    def getTexture(self, slot: int):
        # TW1 supports only 1 slot for textures
        if slot != 0 or len(self.textures) == 0:
            return None

        return next(
            map(
                lambda kv: kv[1],
                filter(lambda kv: kv[0] in ["tex", "texture0", "diffuse_texture", "diffuse_map"], self.textures)
            )
        )

    def hasMaterial(self):
        return len(self.shader) > 0 or len(self.textures) > 0

    def __repr__(self) -> str:
        return "{}({!r})".format(self.__class__.__name__, self.__dict__)

    @classmethod
    def fromString(cls, data: str):
        instance = cls()

        data = list(filter(
            lambda token: len(token) > 0 and token != '\x00',
            re.split(r'[ \t\r\n]', data)
        ))
        i = 0
        while i < len(data):
            dataType = data[i]
            if dataType == 'shader':
                instance.shader = data[i + 1]
                i += 1
            elif dataType == 'texture':
                id, value = data[i + 1: i + 3]
                i += 2
                instance.textures[id if id != 'tex' else 'texture{}'.format(len(instance.textures))] = value
            elif dataType == 'bumpmap':
                id, value = data[i + 1: i + 3]
                i += 2
                instance.bumpmaps[id] = value
            elif dataType == 'string':
                id, value = data[i + 1: i + 3]
                i += 2
                instance.textures[id] = value
            elif dataType == 'float':
                id, value = data[i + 1: i + 3]
                i += 2
                instance.floats[id] = float(value)
            elif dataType == 'vector':
                id, x, y, z, w = data[i + 1: i + 6]
                i += 5
                instance.vectors[id] = Vector((x, y, z))
            i += 1

        return instance

    @classmethod
    def fromFile(cls, path: str):
        assert os.path.exists(path), "File {} must be present in current directory".format(path)
        with open(path, 'r') as file:
            content = file.read()
            instance = ModelMaterial.fromString(content)
            file.close()
            return instance


class ModelTextureLayer(object):
    def __init__(self,
                 hasTexture: bool,
                 texture: str = None,
                 weights: List[float] = []
                 ):
        super().__init__()
        self.hasTexture = hasTexture
        self.texture = texture
        self.weights = weights

    def __repr__(self) -> str:
        return "{}({!r})".format(self.__class__.__name__, self.__dict__)


class ModelMeshBuffer(object):
    def __init__(self,
                 material: ModelMaterial = None,
                 vertexType: int = 0,
                 vertices: List[ModelVertex] = [],
                 indices: List[int] = [],
                 boundingBox: ModelBoundingBox = None,
                 position: Vector = None,
                 normal: Vector = None,
                 tCoords: Vector = None,
                 primitives: list = [],
                 transformation: Matrix = _defaultMatrix(),
                 textureLayers: List[ModelTextureLayer] = [],
                 ):
        super().__init__()
        self.material = material
        self.vertexType = vertexType
        self.vertices = vertices
        self.indices = indices
        self.boundingBox = boundingBox
        self.position = position
        self.normal = normal
        self.tCoords = tCoords
        self.primitives = primitives
        self.transformation = transformation
        self.textureLayers = textureLayers

    def __repr__(self) -> str:
        return "{}({!r})".format(self.__class__.__name__, self.__dict__)


class ModelMesh(object):
    def __init__(self,
                 meshBuffers: List[ModelMeshBuffer] = [],
                 frameCount: int = 0,
                 animationSpeed: float = 0,
                 meshType: int = 0,
                 joints: List[ModelJoint] = [],
                 weights: List[ModelWeight] = [],
                 positionKeys: List[ModelPositionKey] = [],
                 scaleKeys: List[ModelScaleKey] = [],
                 rotationKeys: List[ModelRotationKey] = [],
                 ):
        self.meshBuffers = meshBuffers
        self.frameCount = frameCount
        self.animationSpeed = animationSpeed
        self.meshType = meshType
        self.joints = joints
        self.weights = weights
        self.positionKeys = positionKeys
        self.scaleKeys = scaleKeys
        self.rotationKeys = rotationKeys

    def getJointByName(self, name):
        try:
            return next(filter(lambda joint: joint.name == name, self.joints))
        except StopIteration:
            return None

    def __repr__(self) -> str:
        return "{}({!r})".format(self.__class__.__name__, self.__dict__)
