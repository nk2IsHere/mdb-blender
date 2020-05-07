#  all available header metadata from model
from mathutils import Vector, Quaternion, Matrix, Color, Euler
from typing import List


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
        rot = self.rotation.to_euler()

        qPos = Matrix.Translation((self.position.x, self.position.y, self.position.z))
        qRot = _defaultMatrix().rotate(Euler((self.rotation.x, self.rotation.y, self.rotation.z)))
        qScale = Matrix.Scale(1.0, 4, (self.scale.x, self.scale.y, self.scale.z))

        self.localTransform = qPos * qRot * qScale

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
