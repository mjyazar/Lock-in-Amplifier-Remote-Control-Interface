# Connection settings for SR830 lock-in amplifier

# argument '' on lab computer, '@py' if using pyvisa-py (if no NI-VISA installed)   
BACKEND = 'simulation/simulation.yaml@sim'

# change to match resource name on amplifier, e.g. "GPIB0::1::INSTR" instead of "GPIB0::8::INSTR"
INTERFACE = 'GPIB::8::INSTR'

# any operation longer than this will raise a timeout error (in milliseconds)
TIME_OUT_MS = 5000 