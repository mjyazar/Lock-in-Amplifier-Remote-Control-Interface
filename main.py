import config
import simulation.terminal as terminal
from amplifier.sr830 import SR830


def main():
    
    with SR830(config.INTERFACE, backend=config.BACKEND, timeout_ms=config.TIME_OUT_MS) as amp:
        return terminal.simulation(amp)
        

if __name__ == "__main__":
    main()
