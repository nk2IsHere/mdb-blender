import struct
from functools import reduce

from .model_data import ModelData
from typing import Callable
from typing.io import BinaryIO


# simple method to read string from something like 0x[ASCII]dcdcdcdcdc...00
def _dataToString(data):
    return reduce(
        lambda acc, next: acc + next.decode('utf-8') if next != b'\xdc' else acc, data, ""
    )


# easier to sync code with RedTools
class FileWrapper(object):
    def __init__(self, content: bytes):
        super(object, self).__init__()
        self.content = content
        self.offset = 0

    # set offset to read from
    def seek(self, offset: int, relative: bool = False):
        self.offset = self.offset + offset if relative else offset

    def readUInt32(self):
        data = struct.unpack("I", self.content[self.offset:self.offset + 4])[0]
        self.seek(4, relative=True)
        return data

    def readUInt16(self):
        data = struct.unpack("H", self.content[self.offset:self.offset + 2])[0]
        self.seek(2, relative=True)
        return data

    def readUByte(self):
        data = struct.unpack("B", self.content[self.offset:self.offset + 1])[0]
        self.seek(1, relative=True)
        return data

    def readInt32(self):
        data = struct.unpack("i", self.content[self.offset:self.offset + 4])[0]
        self.seek(4, relative=True)
        return data

    def readInt16(self):
        data = struct.unpack("h", self.content[self.offset:self.offset + 2])[0]
        self.seek(2, relative=True)
        return data

    def readByte(self):
        data = struct.unpack("b", self.content[self.offset:self.offset + 1])[0]
        self.seek(1, relative=True)
        return data

    def readFloat32(self):
        data = struct.unpack("f", self.content[self.offset:self.offset + 4])[0]
        self.seek(4, relative=True)
        return data

    def readString(self, size: int):
        data = _dataToString(struct.unpack("c" * size, self.content[self.offset:self.offset + size]))
        self.seek(size, relative=True)
        return data

    def readStringUntilNull(self):
        data = []

        counter = 0
        while True:
            tempChar = struct.unpack("c", self.content[self.offset + counter:self.offset + counter + 1])[0]
            data.append(tempChar)
            counter += 1
            if tempChar == b'\x00':
                break

        self.seek(counter, relative=True)
        return _dataToString(data)

    @classmethod
    def fromFile(cls, file: BinaryIO):
        instance = cls(file.read())
        file.close()
        return instance


# array header containing its size and elements
class ArrayDefinition(object):
    def __init__(self, firstElemOffset: int, nbUsedEntries: int, nbAllocatedEntries: int):
        super(object, self).__init__()
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
    modelData: ModelData,
    definition: ArrayDefinition,
    wrapperReaderDelegate: Callable
):
    back = wrapper.offset
    wrapper.seek(modelData.offsetModelData + definition.firstElemOffset)
    arrayData = [
        wrapperReaderDelegate() for i in range(definition.nbUsedEntries)
    ]
    wrapper.seek(back)

    return arrayData
