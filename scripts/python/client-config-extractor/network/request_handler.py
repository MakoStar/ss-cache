#!/usr/bin/env python3
import json
import socket
from typing import Any, Dict, List, Optional, Tuple, Union

import requests
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from requests.packages import urllib3 # type: ignore

from utils.logger_utils import logger
from config.constants import RequestConfigs

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

socket.setdefaulttimeout(60)


class LogMsg:
    W101: str = "The request must include the URL"
    E101: str = "Request failed for {url}: {e}"
    E102: str = "JSON parsed failed: {e}"
    E103: str = "Text decoding failed: {e}"
    E104: str = "The request session not create"


class RequestHandler:
    def __init__(self) -> None:
        self._total: int                  = RequestConfigs.TOTAL
        self._verify: bool                = RequestConfigs.VERIFY
        self._backoff_factor: int         = RequestConfigs.BACKOFF_FACTOR
        self._raise_on_status: bool       = RequestConfigs.RAISE_ON_STATUS
        self._timeout: Tuple[int, int]    = RequestConfigs.TIMEOUT
        self._allowed_methods: List[str]  = RequestConfigs.ALLOWED_METHODS
        self._status_forcelist: List[int] = RequestConfigs.STATUS_FORCELIST
        self._headers: Dict[str, Any]     = {}
        self._session: Optional[requests.Session]   = self._create_session()


    def __enter__(self) -> "RequestHandler":
        return self


    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        self.close()
        return False 


    def close(self) -> None:
        if hasattr(self, "_session") and self._session:
            self._session.close()
        session = getattr(self, "_session", None)
        if session is not None:
            try:
                session.close()
            except Exception:
                pass
            finally:
                self._session = None
            
        
    def _create_retry_strategy(self) -> Retry:
        return Retry(
            total=self._total,
            backoff_factor=self._backoff_factor,
            status_forcelist=self._status_forcelist,
            allowed_methods=self._allowed_methods,
            raise_on_status=self._raise_on_status
        )
    

    def _create_session(self) -> requests.Session:
        session = requests.Session()
        retry_strategy = self._create_retry_strategy()
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        if self._headers:
            session.headers.update(self._headers)
        return session


    def add_header(self, header: Dict[str, Any]) -> None:
        if not isinstance(header, dict):
            return
        self._headers.update(header)
        if self._session is not None:
            self._session.headers.update(header)


    def set_header(self, headers: Dict[str, Any]) -> None:
        # wtf
        if not isinstance(headers, dict) or not headers:
            headers = {}
        self._headers = headers
        if self._session is not None:
            self._session.headers.clear()
            self._session.headers.update(headers)


    def request(
        self, method: str, url: str, 
        params: Optional[Dict] = None,
        data: Optional[Union[Dict, str, bytes]] = None, 
        json_data: Optional[Dict[Any, Any]] = None,
        headers: Optional[Dict] = None,
        **kwargs
    ) -> Optional[requests.Response]:
        if not url or not url.strip():
            logger.warning(LogMsg.W101)
            return None 
        try:
            if self._session is None:
                raise RuntimeError(LogMsg.E104)
            response = self._session.request(
                method=method.upper(),
                url=url,
                params=params,
                data=data,
                json=json_data,
                headers=headers,
                verify=self._verify,
                timeout=self._timeout,
                **kwargs
            )
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logger.error(LogMsg.E101.format(url=url, e=str(e)))
            return None


    def fetch_content(self, url: str, headers: Optional[Dict] = None) -> Optional[bytes]:
        response = self.request("GET", url, headers=headers)
        return response.content if response else None


    def fetch_response(self, url: str, headers: Optional[Dict[str, Any]] = None, is_use_stream: bool = False) -> Optional[requests.Response]:
        return self.request(method="GET", url=url, headers=headers, stream=is_use_stream)


    def fetch_json(self, url: str, headers: Optional[Dict] = None) -> Optional[Union[dict, list]]:
        content = self.fetch_content(url, headers=headers)
        if content is None:
            return None
        try:
            return json.loads(content.decode("utf-8"))
        except (ValueError, UnicodeDecodeError) as e:
            logger.error(LogMsg.E102.format(e=str(e)))
            return None
    

    def fetch_text(self, url: str, encoding: str = "utf-8", headers: Optional[Dict] = None) -> Optional[str]:
        content = self.fetch_content(url, headers=headers)
        if content is None:
            return None
        try:
            return content.decode(encoding)
        except UnicodeDecodeError as e:
            logger.error(LogMsg.E103.format(e=str(e)))
            return None


    def post_json(self, url: str, data: Dict, headers: Optional[Dict] = None) -> Optional[requests.Response]:
        return self.request("POST", url, json_data=data, headers=headers)


    def post_binary(self, url: str, data: Union[bytes, str], headers: Optional[Dict] = None) -> Optional[requests.Response]:
        return self.request("POST", url, data=data, headers=headers)
    
        
def main():
    # from config.constants import StaticResourceServerConfigs, ServerRouteConfigs
    # with RequestHandler() as request_handler:
    #     # url = StaticResourceServerConfigs.CN.value.url
    #     # url = StaticResourceServerConfigs.EN.value.url
    #     url = StaticResourceServerConfigs.CN.value.url
    #     url = url + ServerRouteConfigs.META_SERVER_LIST
    #     data = request_handler.fetch_content(url)
    #     logger.info(data)
    pass

if __name__ == '__main__':
    main()
