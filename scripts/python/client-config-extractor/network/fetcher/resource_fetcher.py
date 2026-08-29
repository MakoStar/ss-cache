#!/usr/bin/env python3
import time
import json
import hashlib
from pathlib import PurePosixPath
from typing import Any, Dict, List, Optional, Tuple

from fake_useragent import UserAgent, FakeUserAgent

from utils.file_utils import FileHandler
from utils.logger_utils import LogHelper, logger
from network.request_handler import RequestHandler
from config.constants import ProjectConfigs, RegionSettings, SettingMap


class ResourceFetcher:
    def __init__(self) -> None:
        self.requester: "RequestHandler"             = RequestHandler()
        self.user_agent: "FakeUserAgent"             = UserAgent("Chrome")
        self.launcher_version: str                   = ProjectConfigs.LAUNCHER_VERSION
        self.region_settings: type["RegionSettings"] = RegionSettings
        self.is_save_manifest: bool                  = ProjectConfigs.IS_SAVE_MANIFEST
        self.target_resource_names                   = ProjectConfigs.NEED_FETCHER_RESOURCES
        self.resource_save_path_tpl: str             = ProjectConfigs.SAVE_RESOURCE_PATH
        self.manifest_save_path_tpl: str             = ProjectConfigs.SAVE_MANIFEST_JSON_PATH
        self.version_data: Dict[str, str]            = {}
        self.version_output: str                     = ProjectConfigs.VERSION_OUTPUT


    def fetch_manifest_json(self, manifest_url: str) -> Any:
        return self.requester.fetch_json(manifest_url)


    def generate_signature(self, head_data: Dict[str, Any], salt: str) -> str:
        str_to_sign = json.dumps(head_data, separators=(',', ':')) + salt
        return hashlib.md5(str_to_sign.encode("utf-8")).hexdigest()
    

    def create_request_headers(self, game_tag: str, salt: str) -> Dict[str, Any]:
        authorization = self.create_auth_header(game_tag, salt)
        return {"User-Agent":self.user_agent.random,"Authorization":authorization}


    def create_auth_header(self, game_tag: str, salt: str) -> str:
        version = self.launcher_version
        head = {"game_tag": game_tag, "time": int(time.time()), "version": version}
        sign_str = self.generate_signature(head, salt)
        authorization = {"head": head, "sign": sign_str}
        return json.dumps(authorization, separators=(',', ':'))


    def process_server_info(self, region: str, config: SettingMap) -> None:
        headers = self.create_request_headers(config.tag, config.salt)
        server_info_url = config.api_url + config.api_route
        self.requester.set_header(headers=headers)
        server_info_data = self.requester.fetch_json(server_info_url)
        self.process_manifest_data(region, config, server_info_data)


    def build_manifest_url(self, config: SettingMap, ver: str, path: str) -> str:
        server_manifest_url = config.api_url + config.api_route
        api_route_params = config.api_params.format(ver=ver, path=path)
        return server_manifest_url + api_route_params


    def process_manifest_data(self, region: str, config: SettingMap, data: Any) -> None:
        manifest_json = self.retrieve_manifest(region, config, data)
        if manifest_json is None:
            return
        self.filter_and_process_resources(config, manifest_json)


    def extract_version_and_path(self, config: SettingMap, data: Dict[str,Any]) -> Tuple[str,str]:
        server_info_data = data.get("data")
        if not isinstance(server_info_data, dict):
            return "", ""
        version = server_info_data.get(config.gl_ver, "")
        file_path = server_info_data.get(config.gl_path, "")
        return version, file_path


    def get_manifest_url(self, response_json: Dict[str, Any] | List[Any] | None) -> Optional[str]:
        if not isinstance(response_json, dict):
            return None
        json_data = response_json.get("data")
        if not isinstance(json_data, dict):
            return None
        return json_data.get("url")
    

    def retrieve_manifest(self, region: str, config: SettingMap, data: Any) -> Optional[dict]:
        ver, path = self.extract_version_and_path(config, data)
        if not (ver and path):
            logger.warning(f"Invalid ver/path for {config.tag}: {ver}, {path}")
            return None
        self.version_data[region] = ver
        url = self.build_manifest_url(config, ver, path)
        headers = self.create_request_headers(config.tag, config.salt)
        response_json = self.requester.fetch_json(url, headers=headers)
        manifest_link = self.get_manifest_url(response_json)
        if manifest_link is None:
            logger.warning(f"Manifest link not found in response: {url}")
            return None
        manifest_json = self.fetch_manifest_json(manifest_link)
        if not isinstance(manifest_json, dict):
            logger.warning(f"Invalid manifest format from {manifest_link}")
            return None
        return manifest_json


    def filter_and_process_resources(self, config: SettingMap, manifest_json: Dict[str, Any]) -> None:
        save_manifest_path = self.manifest_save_path_tpl.format(tag=config.tag)
        if self.is_save_manifest:
            FileHandler.write_json(manifest_json, save_manifest_path)
        source = manifest_json.get("source", "")
        need_fetch_resource_list: List[Dict[str, str | int]] = []
        for res in manifest_json.get("file", []):
            file_name = PurePosixPath(res["path"]).name
            if file_name in self.target_resource_names:
                need_fetch_resource_list.append({
                    "name": file_name,
                    "url": f"{config.pkg_url}{source}{res['path']}",
                    "size": res.get("size", 0)
                })
        self.batch_download_resources(config, need_fetch_resource_list)


    def fetch_resource_file(self,config: SettingMap, name: str, url: Optional[str], size: str | int) -> None:
        if not url:
            return
        response_content = self.requester.fetch_response(url, is_use_stream=True)
        if response_content is None:
            return
        save_path = self.resource_save_path_tpl.format(tag=config.tag.split("_")[1]) + name
        if FileHandler.write_stream(response_content, save_path, size=int(size), chunk_size=8192):
            logger.info("Successfully written resource file stream")


    def batch_download_resources(self,config:SettingMap, need_fetch_files: List[Dict[str, Any]]) -> None:
        for res_map in need_fetch_files:
            name = res_map.get("name", "")
            url = res_map.get("url", "")
            size = res_map.get("size", 0)
            self.fetch_resource_file(config, name, url, size)


    def process_regions(self, target_region: str = "", exclude: bool = False) -> None:
        for setting in self.region_settings:
            region_name = setting.name
            region_config = setting.value
            if target_region:
                is_match = (region_name == target_region)
                if exclude and is_match:
                    continue
                if not exclude and not is_match:
                    continue
            LogHelper.log_header(f"FETCHING MATCH RESOURCES {region_name}")
            self.process_server_info(region_name, region_config)

        if len(self.version_data):
            FileHandler.write_json(self.version_data, self.version_output)


    def get_saved_folders(self) -> Dict[str, str]:
        saved_folders = {}
        for setting in self.region_settings:
            region_name = setting.name
            # tag = region
            save_path = self.resource_save_path_tpl.format(tag=region_name)
            saved_folders[region_name] = save_path
        return saved_folders
    

def main():
    # Test
    resource_fetcher = ResourceFetcher()
    resource_fetcher.process_regions("KR")
    

if __name__ == "__main__":
    main()
