#!/usr/bin/env python3
import logging

import coloredlogs

logging.addLevelName(logging.DEBUG, "DEBU")
logging.addLevelName(logging.INFO, "INFO")
logging.addLevelName(logging.WARNING, "WARN")
logging.addLevelName(logging.ERROR, "ERRO")
logging.addLevelName(logging.CRITICAL, "CRIT")


logger_level_styles = {
    "debu": {"color": "white", "faint": True},
    "info": {"color": "green", "bold": True},
    "warn": {"color": "yellow", "bold": True},
    "erro": {"color": "red", "bold": True},
    "crit": {"color": "red", "background": "white"}
}

coloredlogs.install(
    level="DEBUG",
    fmt="[%(asctime)s][%(levelname)s] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level_styles=logger_level_styles,
    isatty=True
)


logger = logging.getLogger(__name__)


class LogHelper:
    COLOR_CYAN = "\033[96m"
    COLOR_RESET = "\033[0m"

    @classmethod
    def _log(cls, msg: str, level: int, color: str, is_use_lv_color: bool = False) -> None:
        if color:
            if is_use_lv_color:
                logger.log(level, f"{msg}")
            else:
                logger.log(level, f"{color}{msg}{cls.COLOR_RESET}")
        else:
            if is_use_lv_color:
                logger.log(level, f"{msg}")
            else:
                logger.log(level, f"{cls.COLOR_CYAN}{msg}{cls.COLOR_RESET}")


    @classmethod
    def log_text(cls, text: str, level: int = logging.INFO, color: str = "") -> None:
        cls._log(text, level, color)


    @classmethod
    def log_header(cls, title: str, total_width: int = 60, level: int = logging.INFO, color: str = "") -> None:
        label = f"[ {title} ]"
        label_len = len(label)

        if label_len >= total_width:
            sep = "=" * max(total_width, label_len)
            cls._log(f"{label}{sep}", level, color)
            return
        
        remaining = total_width - label_len
        left_sep = remaining // 2
        right_sep = remaining - left_sep
        line = f"{'=' * left_sep}{label}{'=' * right_sep}"
        cls._log(line, level, color)

    @classmethod
    def log_separator(cls, sep: str = "=", level: int = logging.INFO, length: int = 100, color: str = "", is_use_lv_color: bool = True) -> None:    
        cls._log(f"{sep * length}", level, color, is_use_lv_color)  



def main():
    # Black	  30  90  40  100
    # Red	  31  91  41  101
    # Green	  32  92  42  102
    # Yellow  33  93  43  103
    # Blue	  34  94  44  104
    # Magenta 35  95  45  105
    # Cyan	  36  96  46  106
    # White	  37  97  47  107
    logger.info("info")
    logger.debug("debug")
    logger.warning("warning")
    logger.error("error")

    LogHelper.log_header("LOG HEADER")
    LogHelper.log_header("LOG HEADER", level=logging.ERROR, color="\033[35m")
    
    LogHelper.log_text("text")
    LogHelper.log_text("text", level=logging.WARNING, color="\033[37m")

    LogHelper.log_separator(level=logging.DEBUG)
    LogHelper.log_separator(level=logging.INFO)
    LogHelper.log_separator(level=logging.WARNING)
    LogHelper.log_separator(level=logging.ERROR)

    LogHelper.log_separator(level=logging.DEBUG, sep="-⭐-", length=10, color="\033[34m", is_use_lv_color=True)
    LogHelper.log_separator(level=logging.INFO, sep="-⭐-", length=20, is_use_lv_color=True)
    LogHelper.log_separator(level=logging.WARNING, sep="-⭐-", length=30, color="\033[33m", is_use_lv_color=True)
    LogHelper.log_separator(level=logging.ERROR, sep="-⭐-", length=40, color="\033[104m", is_use_lv_color=False)


if __name__ == '__main__':
    main()
        