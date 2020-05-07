from enum import Enum


class NodeType(Enum):
    NodeTypeNode = 0x00000001,
    NodeTypeLight = 0x00000003,
    NodeTypeEmitter = 0x00000005,
    NodeTypeCamera = 0x00000009,
    NodeTypeReference = 0x00000011,
    NodeTypeTrimesh = 0x00000021,
    NodeTypeSkin = 0x00000061,
    NodeTypeAABB = 0x00000221,
    NodeTypeTrigger = 0x00000421,
    NodeTypeSectorInfo = 0x00001001,
    NodeTypeWalkmesh = 0x00002001,
    NodeTypeDanglyNode = 0x00004001,
    NodeTypeTexturePaint = 0x00008001,
    NodeTypeSpeedTree = 0x00010001,
    NodeTypeChain = 0x00020001,
    NodeTypeCloth = 0x00040001


class ControllerType(Enum):
    ControllerPosition = 84,
    ControllerOrientation = 96,
    ControllerScale = 184


class NodeTrimeshControllerType(Enum):
    ControllerSelfIllumColor = 276
    ControllerAlpha = 292


class ModelMaterialType(Enum):
    ModelMaterialTypeSolid = 0x0
    ModelMaterialTypeTransparent = 0x1
