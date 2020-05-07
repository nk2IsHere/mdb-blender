#  data layer of parser
#  [notification to myself]
#  [notification to myself] DONT EVEN TRY TO USE BLENDER OBJECT TYPES HERE, BASTARD!
#  [notification to myself]
import os
import re

from mathutils import Vector, Quaternion, Matrix, Color, Euler
from typing import List, Tuple

from .model_types import ModelMaterialType


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
                 bufferId: int,
                 vertexId: int,
                 strength: float,
                 staticPos: Vector,
                 staticNormal: Vector
                 ):
        super().__init__()
        self.bufferId = bufferId
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
                 attachedMeshes: List[int] = [],
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
    def __init__(self, position: Vector, normal: Vector, color: Color, tCoords: Vector):
        super().__init__()
        self.position = position
        self.normal = normal
        self.color = color
        self.tCoords = tCoords

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


class ModelMaterial(object):
    def __init__(self,
                 shader: str = '',
                 textures: List[Tuple[str, str]] = [],
                 bumpmaps: List[Tuple[str, str]] = [],
                 floats: List[Tuple[str, float]] = [],
                 vectors: List[Tuple[str, Vector]] = []
                 ):
        super().__init__()
        self.shader = shader
        self.textures = textures
        self.bumpmaps = bumpmaps
        self.floats = floats
        self.vectors = vectors

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

    @classmethod
    def fromString(cls, data: str):
        instance = cls()

        data = re.split(' \t\r\n', data)
        i = 0
        while i < len(data):
            dataType = data[i]
            if dataType == 'shader':
                instance.shader = data[i + 1]
                i += 1
            elif dataType == 'texture':
                id, value = data[i + 1: i + 3]
                i += 2
                instance.textures.append((id, value))
            elif dataType == 'bumpmap':
                id, value = data[i + 1: i + 3]
                i += 2
                instance.bumpmaps.append((id, value))
            elif dataType == 'string':
                id, value = data[i + 1: i + 3]
                i += 2
                instance.textures.append((id, value))
            elif dataType == 'float':
                id, value = data[i + 1: i + 3]
                i += 2
                instance.floats.append((id, float(value)))
            elif dataType == 'vector':
                id, x, y, z, w = data[i + 1: i + 6]
                i += 5
                instance.vectors.append((id, Vector((x, y, z))))
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
                 transformation: Matrix = Matrix()
                 ):
        super().__init__()

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
        return next(filter(lambda joint: joint.name == name, self.joints))

    def __repr__(self) -> str:
        return "{}({!r})".format(self.__class__.__name__, self.__dict__)
