import logging
import sys

import config
import interface.terminal as terminal
from amplifier.sr830 import SR830


def setup_logging():
    """
    Configure the logging system for the whole application.
 
    Two handlers are set up:
      1. Console — shows INFO and above in the terminal while running
      2. File    — saves DEBUG and above (everything) to a log file
 
    Log levels, from least to most severe:
        DEBUG    low-level detail (every VISA write/query)
        INFO     normal operational messages (connected, parameter set, etc.)
        WARNING  something unexpected but not fatal
        ERROR    something failed
        CRITICAL application cannot continue
    """
 
    # The root logger captures everything from all modules
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # capture everything; handlers filter below
 
    log_format = logging.Formatter(
        fmt="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
 
    # --- Console handler: INFO and above (clean, not cluttered with DEBUG) ---
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(log_format)
    root_logger.addHandler(console_handler)
 
    # --- File handler: DEBUG and above (full trace for troubleshooting) ---
    # The file is appended to on each run, not overwritten.
    # Change mode="a" to mode="w" if you want a fresh file each run.
    file_handler = logging.FileHandler("sr830.log", mode="a", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(log_format)
    root_logger.addHandler(file_handler)


def main():
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("Starting Lock-in Amplifier Control Interface")
    logger.info("Backend  : %s", config.BACKEND or "(NI-VISA auto-detect)")
    logger.info("Resource : %s", config.INTERFACE)
    
    with SR830(config.INTERFACE, backend=config.BACKEND, timeout_ms=config.TIME_OUT_MS) as amp:
        return terminal.simulation(amp)
        
    logger.info("Program exited successfully.")


if __name__ == "__main__":
    main()
