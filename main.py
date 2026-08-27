import logging
import os
import time
import sys

import config
from amplifier.sr830 import SR830
import interface.webapp as webapp


def setup_logging():
    """
    Configure the logging system for the whole application
 
    Console - shows INFO and above in the terminal while running
    File - saves DEBUG and above (everything) to a log file
 
    Log levels:
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

    # Console handler: INFO and above (clean, not cluttered with DEBUG)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(log_format)
    root_logger.addHandler(console_handler)
 
    # File handler: DEBUG and above (full trace for troubleshooting)
    # The file is appended to on each run, not overwritten.
    # Change mode="a" to mode="w" if you want a fresh file each run.
    # Filename uses hyphens (not colons) so it is valid on Windows/NTFS.
    os.makedirs("logs", exist_ok=True)
    current_time = time.strftime("%Y-%m-%d_%H-%M-%S")
    file_handler = logging.FileHandler(f"logs/{current_time}.log", mode="a", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(log_format)
    root_logger.addHandler(file_handler)

    logging.getLogger("dash.dash").setLevel(logging.WARNING)


def main():
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("Starting Lock-in Amplifier Control Interface")
    logger.info("Backend  : %s", config.BACKEND or "(NI-VISA auto-detect)")
    logger.info("Resource : %s", config.INTERFACE)
    
    # terminal.simulation(amp)

    import pyvisa
    rm = pyvisa.ResourceManager()

    print(rm.list_resources())

    with SR830(config.INTERFACE, backend=config.BACKEND, timeout_ms=config.TIME_OUT_MS) as amp:
        #return terminal.simulation(amp)
        app = webapp.create_app(amp)

        logger.info("Starting Dash web server on port %s", config.DASH_PORT)
        logger.info("Open http://<this-machine-ip>:%s in any browser", config.DASH_PORT)

        # debug=False and use_reloader=False are mandatory when connected to real
        # hardware — the Dash hot-reloader spawns a subprocess that would attempt
        # a second VISA connection and cause instrument conflicts.
        app.run(host="0.0.0.0", port=config.DASH_PORT, debug=False, use_reloader=False)

        
    logger.info("Program exited successfully.")


if __name__ == "__main__":
    main()
