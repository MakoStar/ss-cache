#!/usr/bin/env python3
import struct
from pathlib import Path
from typing import Any, Dict, List, Optional

from utils.file_utils import FileHandler
from reader.binary_reader import BinaryReader
from utils.logger_utils import LogHelper, logger
from config.constants import ProjectConfigs, FileRuleConfigs, ClientConfigParserSettings


class ClientConfigParser:
    def __init__(self) -> None:
        self.region_keys                = ProjectConfigs.REGION_KEYS
        self.alignment: int             = ClientConfigParserSettings.ALIGNMENT
        self.target_name: bytes         = ClientConfigParserSettings.TARGET_NAME
        self.output_data_path_tpl: str  = ProjectConfigs.OUTPUT_DATA_PATH_TPL
        self.max_back_track_offset: int = ClientConfigParserSettings.MAX_BACKTRACK_OFFSET


    def _calc_aligned_object_start(self, str_end: int) -> int:
        padding = (self.alignment - (str_end % self.alignment)) % self.alignment
        return str_end + padding


    def _validate_header_at(self, raw: bytes, obj_start: int) -> Optional[bytes]:
        max_offset = min(self.max_back_track_offset, obj_start)
        for back in range(0, max_offset + 1, 4):
            candidate = obj_start - back
            if self._is_valid_monobehaviour_header(raw, candidate):
                return raw[candidate:]
        return None


    @staticmethod
    def _skip_monobehaviour_header(reader: BinaryReader) -> str:
        _ = reader.read_int32()   # m_GameObject.fileID
        _ = reader.read_int32()   # m_GameObject.pathID
        _ = reader.read_int32()   # m_Enabled
        _ = reader.read_int32()   # m_Script.fileID
        _ = reader.read_int32()   # m_Script.pathID
        return reader.read_string()


    def _is_valid_monobehaviour_header(self, raw: bytes, offset: int) -> bool:
        try:
            reader = BinaryReader(raw[offset:])
            name = self._skip_monobehaviour_header(reader)
            return name == self.target_name.decode("utf-8")
        except Exception:
            return False
        
    
    def _find_valid_string_length(self, raw: bytes, start: int = 0) -> Optional[int]:
        pos = start
        while True:
            idx = raw.find(self.target_name, pos)
            if idx == -1:
                return None
            len_offset = idx - 4
            if len_offset < 0:
                pos = idx + 1
                continue
            str_len = struct.unpack('<I', raw[len_offset:len_offset + 4])[0]
            if str_len == len(self.target_name):
                return len_offset
            pos = idx + 1


    def get_input_path(self, region: str) -> str:
        file_name = self.target_name.decode("utf-8") + FileRuleConfigs.EXT_BYTES
        saved_data_path = self.output_data_path_tpl.format(region=region)
        return str(Path(saved_data_path) / file_name)


    def get_output_path(self, region: str) -> str:
        file_name = self.target_name.decode("utf-8") + FileRuleConfigs.EXT_JSON
        output_path = self.output_data_path_tpl.format(region=region)
        return str(Path(output_path) / file_name)


    def find_client_config_payload(self, raw: bytes) -> bytes:
        search_start = 0
        while True:
            len_offset = self._find_valid_string_length(raw, search_start)
            if len_offset is None:
                raise ValueError("No valid ClientConfig string found in data")
            str_end = len_offset + 4 + self.target_name.__len__()
            obj_start = self._calc_aligned_object_start(str_end)
            result = self._validate_header_at(raw, obj_start)
            if result is not None:
                return result
            search_start = len_offset + 4 + 1


    def parse_vendor_env_data(self, reader: BinaryReader) -> Dict[str, Any]:
        return {
            "name": reader.read_string(), # 0x10
            "vendorDisplayName": reader.read_string(), # 0x18
            "flags": reader.read_int32(), # 0x20
            "clientVersion_Android": reader.read_string(), # 0x28
            "clientVersion_IOS": reader.read_string(), # 0x30
            "clientVersion_Windows": reader.read_string(), # 0x38
            "timeZone": reader.read_int32(), # 0x40
            "localLanguage": reader.read_string(), # 0x48
            "voiceLanguage": reader.read_string(), # 0x50
            "availableTextLanguages": reader.read_string_array(), # 0x58
            "availableVoiceLanguages": reader.read_string_array(), # 0x60
            "sdkName": reader.read_string(), # 0x68
            "serverURL": reader.read_string(), # 0x70
            "serverChannelName": reader.read_string(), # 0x78
            "serverMetaKey": reader.read_string(), # 0x80
            "reviewServerMetaKey": reader.read_string(), # 0x88
            "serverGarbleKey": reader.read_string(), # 0x90
            "reviewServerGarbleKey": reader.read_string(), # 0x98
        }
    

    def parse_and_save(self, region: str, raw_data: bytes) -> Dict[str, Any]:
        object_data = self.find_client_config_payload(raw_data)
        reader = BinaryReader(object_data)
        name = self._skip_monobehaviour_header(reader)
        target_name = self.target_name.decode("utf-8")
        if name != target_name:
            raise ValueError(f"Object name is '{name}', expected {target_name}")
        client_config_data = {
            "buildVersion": reader.read_string(),
            "buildTag": reader.read_string(),
            "isOpenGM": reader.read_bool(),
            "useLocalResourcesDownloadServer": reader.read_bool(),
            "localResourcesDownloadServerUrl": reader.read_string(),
            "backupServerUrlPrefix": reader.read_string(),
            "vendorEnvData": [
                self.parse_vendor_env_data(reader) for _ in range(reader.read_int32())
            ],
        }
        save_path = self.get_output_path(region)
        FileHandler.write_json(client_config_data, save_path)
        logger.info(f"Saved parsed client config json -> {save_path}")
        return client_config_data
    

    def extract_vendor_env(self, region: str) -> List[Dict[str, Any]]:
        LogHelper.log_header(f"GET {region} VENDOR ENV DATA")
        input_path = self.get_input_path(region)
        raw_data = FileHandler.read_binary(input_path)
        parsed_data = self.parse_and_save(region, raw_data)
        return parsed_data.get("vendorEnvData", [])
    
    
    def process_regions(self, target_region: str = "", exclude: bool = False) -> None:      
        for region_key in self.region_keys:
            if target_region:
                is_match = (region_key == target_region)
                if exclude and is_match:
                    continue
                if not exclude and not is_match:
                    continue
            LogHelper.log_header(f"PARSING CONFIG {region_key}")
            input_path = self.get_input_path(region_key)
            raw_data = FileHandler.read_binary(input_path)
            logger.debug(f"ClientConfig: {len(raw_data)} - {input_path}")
            self.parse_and_save(region_key, raw_data)


def main():
    from config.constants import RegionSettings

    region = RegionSettings.CN.name
    client_config_parser = ClientConfigParser()
    vendor_env_data = client_config_parser.extract_vendor_env(region)
    logger.info(vendor_env_data)

    client_config_parser.process_regions()

if __name__ == '__main__':
    main()
