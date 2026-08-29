#!/usr/bin/env python3
import os
import sys
import json
from os import PathLike
from pathlib import Path
from functools import wraps
from datetime import datetime
from typing import Any, Callable, Dict, List, TypeVar, Union, Optional

from requests import Response
from utils.logger_utils import logger 

JsonSerializable = TypeVar("JsonSerializable", Dict, List, str, int, float, bool, None)


class LogMsg:
    # Error
    E101: str = "File not found: {path}"
    E102: str = "Json data parsing error: {e}"
    E103: str = "System IO error: {e}"
    E104: str = "Unexpected error: {e}"
    # Other
    O101: str = "[{func_name}] {msg}"


class suppress_read_errors:
    def __init__(self, func: Callable[..., Any]):
        self.func = func
        wraps(func)(self)

    def __call__(self, *args, **kwargs) -> Any:
        try:
            return self.func(*args, **kwargs)
        except FileNotFoundError as e:
            path = self._extract_path(e, args)
            self._log_error(LogMsg.E101.format(path=path))
        except (json.JSONDecodeError, ValueError) as e:
            self._log_error(LogMsg.E102.format(e=str(e)))
        except OSError as e:
            self._log_error(LogMsg.E103.format(e=str(e)))
        except Exception as e:
            self._log_error(LogMsg.E104.format(e=str(e)), exc_info=True)  
        return None

    @staticmethod
    def _extract_path(exc: FileNotFoundError, args: tuple) -> str:
        if getattr(exc, "filename", None):
            return str(exc.filename)
        for arg in args:
            if isinstance(arg, (str, Path)):
                return str(arg)
            if hasattr(arg, "__fspath__"):
                return str(arg)
        return "Unknown Path"

    def _log_warning(self, msg: str):
        func_name = self.func.__name__
        logger.warning(LogMsg.O101.format(func_name=func_name, msg=msg))

    def _log_error(self, msg: str, exc_info: bool = False):
        func_name = self.func.__name__
        logger.error(LogMsg.O101.format(func_name=func_name, msg=msg), exc_info=exc_info)


class suppress_write_errors:
    def __init__(self, func: Callable[..., Any]):
        self.func = func
        wraps(func)(self)

    def __call__(self, *args, **kwargs) -> bool:
        try:
            self.func(*args, **kwargs)
            return True
        except OSError as e:
            self._log_error(LogMsg.E103.format(e=str(e)))
        except Exception as e:
            self._log_error(LogMsg.E104.format(e=str(e)), exc_info=True)
        return False

    def _log_error(self, msg: str, exc_info: bool = False):
        func_name = self.func.__name__
        logger.error(LogMsg.O101.format(func_name=func_name, msg=msg), exc_info=exc_info)

    
class ConsoleProgress:  
    def __init__(self, total: int, desc: str = "", bar_width: int = 30):
        self.total = max(total, 1)
        self.desc = desc
        self.bar_width = bar_width
        self.downloaded = 0
        self._last_pct = -1
        self.is_ci = os.environ.get("CI", "false").lower() == "true"
        if not self.is_ci:
            self._render()

    def _format_size(self, size_bytes: int) -> str:
        return f"{size_bytes / (1024 * 1024):.2f} mb"

    def _render(self):
        pct = min(100, self.downloaded * 100 // self.total)
        filled = self.bar_width * pct // 100
        bar = '█' * filled + '░' * (self.bar_width - filled)
        prefix = self._get_prefix()
        current_mb = self._format_size(self.downloaded)
        total_mb = self._format_size(self.total)
        line = f"\r{prefix}{bar}| {pct}% {self.desc} ({current_mb}/{total_mb})"
        sys.stdout.write(line)
        sys.stdout.flush()
        self._last_pct = pct
    
    def _get_prefix(self) -> str:
        now = datetime.now() .strftime("%Y-%m-%d %H:%M:%S")
        color = "\033[32m"
        color_reset = "\033[0m"
        return f"{color}[{now}]{color_reset}[DOWN] - "
        
    def update(self, n: int):
        self.downloaded += n
        pct = min(100, self.downloaded * 100 // self.total)
        if not self.is_ci:
            if pct != self._last_pct:
                self._render()
  
    def finish(self):
        if not self.is_ci:
            self.downloaded = self.total
            pct = min(100, self.downloaded * 100 // self.total)
            if pct != self._last_pct:
                self._render()
            sys.stdout.write('\n')
            sys.stdout.flush()


class FileHandler:
    @staticmethod
    def _resolve_path(path: Union[str, PathLike]) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    @classmethod
    def write_bytes(cls, data: bytes, path: Union[str, PathLike]) -> None:
        target_path = cls._resolve_path(path)
        target_path.write_bytes(data)

    @classmethod
    @suppress_write_errors
    def write_stream(cls, response: Response, path: Union[str, PathLike], size: int = 0, chunk_size: int = 8192):
        response.raise_for_status()
        total = int(response.headers.get("content-length", 0)) or size
        target_path = cls._resolve_path(path)
        temp_path = f"{target_path}.temp"
        filename = os.path.basename(target_path)
        progress = ConsoleProgress(total=total, desc=filename)
        try:
            with open(temp_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        progress.update(len(chunk))
            os.replace(temp_path, target_path)
        except Exception:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass
            raise
        finally:
            progress.finish()
            response.close()


    @classmethod
    def write_json(cls, data: JsonSerializable, path: Union[str, PathLike]) -> None:
        target_path = cls._resolve_path(path)
        json_str = json.dumps(data, indent=4, ensure_ascii=False)
        target_path.write_text(json_str, encoding="utf-8")

    @classmethod
    def write_text(cls, data: str, path: Union[str, PathLike]) -> None:
        target_path = cls._resolve_path(path)
        target_path.write_text(data)

    @classmethod
    def ensure_path(cls, path: Union[str, PathLike]) -> None:
        cls._resolve_path(path)

    @classmethod
    @suppress_read_errors
    def read_json(cls, path: Union[str, PathLike], encoding: str = "utf-8") -> Dict | List | None:
        with open(path, 'r', encoding=encoding) as f:
            return json.load(f)

    @classmethod
    @suppress_read_errors
    def read_binary(cls, path: Union[str, PathLike]) -> Optional[bytes]:
        with open(path, "rb") as f:
            return f.read()
        
    @classmethod
    @suppress_read_errors
    def read_text(cls, path: Union[str, PathLike]) -> Optional[str]:
        with open(path, 'r', encoding="utf-8") as f:
            return f.read()
        
def main():
    # Test
    json_data = FileHandler.read_json("./test/ike.json")
    logger.debug(json_data)
    binary_data = FileHandler.read_binary("./data_storage/notice_list/CN/noticelist.bin")
    logger.debug(binary_data)

if __name__ == '__main__':
    main()

