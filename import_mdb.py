from functools import reduce
import struct


# simple method to read string from somthing like 0x[ASCII]dcdcdcdcdc...
def dataToStr(data):
    return reduce(lambda acc, next: acc + next.decode('utf-8') if next != b'\xdc' else acc + "", data, "")


# easier to sync code with RedTools
class FileWrapper(object):
    def __init__(self, content: bytes):
        super(FileWrapper, self).__init__()
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
        data = struct.unpack("H", content[self.offset:self.offset + 2])[0]
        self.seek(2, relative=True)
        return data

    def readUByte(self):
        data = struct.unpack("B", content[self.offset:self.offset + 1])[0]
        self.seek(1, relative=True)
        return data

    def readInt32(self):
        data = struct.unpack("i", content[self.offset:self.offset + 4])[0]
        self.seek(4, relative=True)
        return data

    def readInt16(self):
        data = struct.unpack("h", content[self.offset:self.offset + 2])[0]
        self.seek(2, relative=True)
        return data

    def readByte(self):
        data = struct.unpack("b", content[self.offset:self.offset + 1])[0]
        self.seek(1, relative=True)
        return data

    def readFloat32(self):
        data = struct.unpack("f", content[self.offset:self.offset + 4])[0]
        self.seek(4, relative=True)
        return data

    def readString(self, size: int):
        data = dataToStr(struct.unpack("c" * size, content[self.offset:self.offset + size]))
        self.seek(size, relative=True)
        return data

    def readStringUntilNull(self):
        data = []

        cnt = 0
        while True:
            chr = struct.unpack("c", content[self.offset + cnt:self.offset + cnt + 1])[0]
            data.append(chr)
            cnt += 1
            if chr == b'\x00':
                break

        self.offset += cnt
        return dataToStr(data)


# array header used by bioware aurora models
class ArrayDefinition(object):
    def __init__(self, firstElemOffset: int, nbUsedEntries: int, nbAllocatedEntries: int):
        super().__init__()
        self.firstElemOffset = firstElemOffset
        self.nbUsedEntries = nbUsedEntries
        self.nbAllocatedEntries = nbAllocatedEntries


# read array using its definition
def readArray(content: FileWrapper, definition: ArrayDefinition, s_type: str, s_size: int, offsetModelData: int):
    offset = offsetModelData + definition.firstElemOffest
    return [
        struct.unpack(s_type, content[offset + s_size * i:offset + s_size * (i + 1)])[0] for i in
        range(definition.nbUsedEntries)
    ]


def load(
    operator,
    context,
    filepath="",
    base_path=None,
    global_matrix=None,
):
    print('bbb {0}'.format(filepath))
    return {'FINISHED'}
