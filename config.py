# Connection settings for SR830 lock-in amplifier

"""
SIMULATION
"""
#BACKEND = 'simulation/simulation.yaml@sim'
#INTERFACE = 'GPIB::1::INSTR'


"""
REAL HARDWARE
Backend: argument '' on lab computer, '@py' if using pyvisa-py (if no NI-VISA installed)
Interface: change to match resource name on amplifier, e.g. "GPIB0::1::INSTR" instead of "GPIB0::8::INSTR"
Time Out: any operation longer than this will raise a timeout error (in milliseconds)
"""
BACKEND = ''
INTERFACE = 'GPIB::8::INSTR'
TIME_OUT_MS = 10000 