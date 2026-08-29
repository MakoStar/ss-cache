#!/usr/bin/env python3
from enum import Enum
from typing import Dict, List, Set, Tuple
from dataclasses import dataclass


@dataclass
class SettingMap:
    tag: str
    salt: str
    api_url: str
    pkg_url: str
    gl_ver: str = "game_latest_version"
    gl_path: str = "game_latest_file_path"
    api_route: str = "/api/launcher/game/config"
    api_params: str = "/json?version={ver}&file_path={path}"


class RegionSettings(Enum):
    CN = SettingMap(
        tag="StellaSora_CN", 
        salt="872550AD59A235662C5B7D5F88CEBE4B", 
        api_url="https://launcher-api.yostar.net",
        pkg_url="https://game-launcher-ss-cn.yostar.net"
    )
    EN = SettingMap(
        tag="StellaSora_EN", 
        salt="DE7108E9B2842FD460F4777702727869", 
        api_url="https://api-launcher-en.yo-star.com",
        pkg_url="https://launcher-pkg-ss-en.yo-star.com"
    )
    JP = SettingMap(
        tag="StellaSora_JP", 
        salt="DE7108E9B2842FD460F4777702727869", 
        api_url="https://api-launcher-jp.yo-star.com",
        pkg_url="https://launcher-pkg-ss-jp.yo-star.com"
    )
    KR = SettingMap(
        tag="StellaSora_KR", 
        salt="DE7108E9B2842FD460F4777702727869", 
        api_url="https://api-launcher-kr.yo-star.com",
        pkg_url="https://launcher-pkg-ss-kr.yo-star.com"
    )
    TW = SettingMap(
        tag="StellaSora_TW", 
        salt="DE7108E9B2842FD460F4777702727869", 
        api_url="https://api-launcher-tw.stargazer-games.com",
        pkg_url="https://launcher-pkg-ss-hk.stargazer-games.com"
    )


class ProjectConfigs:
    LAUNCHER_VERSION: str            = "1.6.0"
    IS_SAVE_MANIFEST: bool           = False
    REGION_KEYS: List[str]           = [r.name for r in RegionSettings]
    ROOT_OUTPUT_PATH: str            = "./output"
    OUTPUT_DATA_PATH_TPL: str        = "output/{region}/"
    INPUT_METADATA_PATH_TPL: str     = "./data_storage/metadatas/{region}/"
    SAVE_RESOURCE_PATH: str          = "./data_storage/data_u3d/{tag}/"
    SAVE_MANIFEST_JSON_PATH: str     = "./data_storage/manifests/{tag}/manifest.json"
    NEED_FETCHER_RESOURCES: Set[str] = {"data.unity3d"}
    VERSION_OUTPUT: str              = "./output/version.json"


class FileRuleConfigs:
    EXT_BIN: str    = ".bin"
    EXT_JSON: str   = ".json"
    EXT_LUA: str    = ".lua"
    EXT_BYTES: str  = ".bytes"
    EXT_ARCX: str   = ".arcx"
    EXT_ARCH: str   = ".arch"
    EXT_HTML: str   = ".html"
    EXT_TEXT: str   = ".txt"

    EXT_UPDATE_MANIFEST: str = ".ss_win.mani"



class RequestConfigs:
    TOTAL: int                  = 3
    VERIFY: bool                = False
    BACKOFF_FACTOR: int         = 1
    RAISE_ON_STATUS: bool       = True
    TIMEOUT: Tuple[int, int]    = (15, 60)
    ALLOWED_METHODS: List[str]  = ["GET", "POST"]
    STATUS_FORCELIST: List[int] = [429, 500, 502, 503, 504]


@dataclass
class ExportFileItem:
    type_name: str
    file_name: str
    extension: str
    parse_method: str


class AssetTypes:
    TEXT_ASSET: str = "TextAsset"
    MONO_BEHAVIOUR: str = "MonoBehaviour"


class ExtractorSettings:
    ASSET_NAME: str = "data.unity3d"
    NEED_EXPORT_FILES: List[ExportFileItem] = [
        ExportFileItem(
            file_name="SDKConfigSettings", 
            parse_method="parse_as_object",
            type_name=AssetTypes.TEXT_ASSET, 
            extension=FileRuleConfigs.EXT_JSON    
        ),
        ExportFileItem(
            file_name="ClientConfig", 
            parse_method="get_raw_data",
            type_name=AssetTypes.MONO_BEHAVIOUR, 
            extension=FileRuleConfigs.EXT_BYTES    
        )
    ]

class ClientConfigParserSettings:
    ALIGNMENT: int = 4
    TARGET_NAME = b"ClientConfig"
    MAX_BACKTRACK_OFFSET: int = 100