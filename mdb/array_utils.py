import struct
from mdb.file_utils import FileWrapper


# array header containing its size and elements
class ArrayDefinition(object):
    def __init__(self, firstElemOffset: int, nbUsedEntries: int, nbAllocatedEntries: int):
        super(ArrayDefinition, self).__init__()
        self.firstElemOffset = firstElemOffset
        self.nbUsedEntries = nbUsedEntries
        self.nbAllocatedEntries = nbAllocatedEntries

    @classmethod
    def fromWrapper(cls, wrapper: FileWrapper):
        return cls(
            firstElemOffset=wrapper.readUInt32(),
            nbUsedEntries=wrapper.readUInt32(),
            nbAllocatedEntries=wrapper.readUInt32()
        )


# read array using its definition
# (all arrays' contents start globally @offsetModelData)
def readArray(
    wrapper: FileWrapper,
    definition: ArrayDefinition,
    sType: str,
    sSize: int,
    offsetModelData: int
):
    offset = offsetModelData + definition.firstElemOffset
    return [
        struct.unpack(sType, wrapper.content[offset + sSize * i:offset + sSize * (i + 1)])[0]
            for i in range(definition.nbUsedEntries)
    ]
