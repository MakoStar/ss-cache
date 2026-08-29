#!/usr/bin/env python3
import struct
from typing import List


class BinaryReader:
    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0


    def read_bool(self) -> bool:
        return self.read_int32() != 0


    def read_string_array(self) -> List[str]:
        count = self.read_int32()
        return [self.read_string() for _ in range(count)]
    

    def read_int32(self) -> int:
        if self.pos + 4 > len(self.data):
            raise EOFError("Unexpected end of data")
        val = struct.unpack('<i', self.data[self.pos:self.pos + 4])[0]
        self.pos += 4
        return val
    

    def read_int64(self) -> int:
        if self.pos + 8 > len(self.data):
            raise EOFError("Unexpected end of data")
        val = struct.unpack('<q', self.data[self.pos:self.pos + 8])[0]
        self.pos += 8
        return val
    

    def read_string(self) -> str:
        length = self.read_int32()
        if length == 0:
            return ""
        if self.pos + length > len(self.data):
            raise EOFError("String length exceeds data")
        raw = self.data[self.pos:self.pos + length]
        self.pos += length
        padding = (4 - (length % 4)) % 4
        self.pos += padding
        return raw.decode("utf-8", errors="replace")
    

def main():
    from utils.logger_utils import logger
    from utils.file_utils import FileHandler
    binary_data = FileHandler.read_binary("./output/CN/ClientConfig.bytes")
    binary_reader = BinaryReader(binary_data)
    logger.info(binary_reader.read_int64()) # -
    logger.info(binary_reader.read_int64()) # -
    logger.info(binary_reader.read_int64()) # -
    logger.info(binary_reader.read_int64()) # -
    logger.info(binary_reader.read_int32()) # 1701407811
    logger.info(binary_reader.read_int32()) # 1866691694
    logger.info(binary_reader.read_int32()) # 1734960750
    logger.info(binary_reader.read_int32()) # 14

    raw_bytes_1 = struct.pack("<i", 1701407811)
    raw_bytes_2 = struct.pack("<i", 1866691694)
    raw_bytes_3 = struct.pack("<i", 1734960750)
    raw_bytes = raw_bytes_1 + raw_bytes_2 + raw_bytes_3
    # b'ClientConfig'
    print(raw_bytes)


if __name__ == '__main__':
    main()
