#  all available header metadata from model
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
