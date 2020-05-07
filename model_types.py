from enum import Enum


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

