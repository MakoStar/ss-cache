#!/usr/bin/env python3
from pathlib import Path
from typing import List, Optional

import UnityPy
from UnityPy import Environment as UnityPyEnv

from utils.file_utils import FileHandler
from utils.logger_utils import LogHelper, logger
from config.constants import ProjectConfigs, ExportFileItem, ExtractorSettings, AssetTypes

class ClientConfigExtractor:
    def __init__(self) -> None:
        self.region_keys = ProjectConfigs.REGION_KEYS
        self.asset_name: str = ExtractorSettings.ASSET_NAME
        self.save_path_tpl: str = ProjectConfigs.SAVE_RESOURCE_PATH
        self.output_path_tpl: str = ProjectConfigs.OUTPUT_DATA_PATH_TPL
        self.export_target_files: List[ExportFileItem] = ExtractorSettings.NEED_EXPORT_FILES


    def get_asset_folder(self, region: str) -> str:
        return self.save_path_tpl.format(tag=region)
    

    def get_asset_path(self, region: str) -> str:
        folder = self.get_asset_folder(region)
        return str(Path(folder) / self.asset_name)


    def get_export_path(self, region: str, export_item: ExportFileItem) -> str:
        output_path = Path(self.output_path_tpl.format(region=region))
        return str(output_path / f"{export_item.file_name}{export_item.extension}")


    def _save_exported_file(self, data: bytes, path: str, file_name: str) -> None:
        FileHandler.write_bytes(data, path)
        logger.info(f"Export success: | {file_name} -> {path}")


    def load_asset_env(self, region: str, asset_path: str) -> UnityPyEnv:
        try:
            return UnityPy.load(asset_path)
        except Exception as e:
            raise RuntimeError(f"Load asset env failed: {region} | {asset_path} | {e}")
    

    def extract_region(self, region: str) -> None:
        asset_path = self.get_asset_path(region)
        env = self.load_asset_env(region, asset_path)
        for export_item in self.export_target_files:
            self._extract_and_save(region, env, export_item)
        del env


    def process_regions(self, target_region: str = "", exclude: bool = False) -> None:
        for region_key in self.region_keys:
            if target_region:
                is_match = (region_key == target_region)
                if exclude and is_match:
                    continue
                if not exclude and not is_match:
                    continue
            LogHelper.log_header(f"EXTRACTING CONFIG {region_key}")
            self.extract_region(region=region_key)

    
    def _extract_and_save(self, region: str, env: UnityPyEnv, export_item: ExportFileItem) -> None:
        target_type = export_item.type_name
        target_name = export_item.file_name
        for asset_obj in env.objects:
            if asset_obj.type.name != target_type:
                continue
            if asset_obj.peek_name() != target_name:
                continue
            save_path = self.get_export_path(region, export_item)
            if target_type == AssetTypes.TEXT_ASSET:
                parsed = asset_obj.parse_as_object()
                raw_bytes = parsed.m_Script.encode("utf-8", "surrogateescape")
                self._save_exported_file(raw_bytes, save_path, target_name)
            elif target_type == AssetTypes.MONO_BEHAVIOUR:
                raw_bytes = asset_obj.get_raw_data()
                self._save_exported_file(raw_bytes, save_path, target_name)
            else:
                logger.warning(f"Unsupported export type: {region} | {target_type} | {target_name}")
            return
        logger.warning(f"Asset not found: {region} | {target_type} | {target_name}")


def main():
    extractor = ClientConfigExtractor()
    extractor.process_regions()


if __name__ == '__main__':
    main()
