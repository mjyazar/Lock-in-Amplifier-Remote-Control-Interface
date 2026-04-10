import pyvisa
import logging

logger = logging.getLogger(__name__)


class SR830Error(Exception):
    """
    Raised for SR830-specific communication or configuration errors
    """
    pass


class SR830:
    """
    Driver for the SR830 DSP Lock-In Amplifier
    """
    SENSITIVITY: dict = {
        0:  ['2nV', 2e-9],   1:  ['5nV', 5e-9],   2:  ['10nV', 1e-8],  3:  ['20nV', 2e-8],
        4:  ['50nV', 5e-8],  5:  ['100nV', 1e-7], 6:  ['200nV', 2e-7], 7:  ['500nV', 5e-7],
        8:  ['1uV', 1e-6],   9:  ['2uV', 2e-6],   10: ['5uV', 5e-6],   11: ['10uV', 1e-5],
        12: ['20uV', 2e-5],  13: ['50uV', 5e-5],  14: ['100uV', 1e-4], 15: ['200uV', 2e-4],
        16: ['500uV', 5e-4], 17: ['1mV', 1e-3],   18: ['2mV', 2e-3],   19: ['5mV', 5e-3],
        20: ['10mV', 1e-2],  21: ['20mV', 2e-2],  22: ['50mV', 5e-2],  23: ['100mV', 1e-1],
        24: ['200mV', 2e-1], 25: ['500mV', 5e-1], 26: ['1V', 1.0]
    }
    
    TIME_CONSTANT: dict = {
        0:  ['10us', 1e-5],  1:  ['30us', 3e-5],  2:  ['100us', 1e-4], 3:  ['300us', 3e-4],
        4:  ['1ms', 1e-3],   5:  ['3ms', 3e-3],   6:  ['10ms', 1e-2],  7:  ['30ms', 3e-2],
        8:  ['100ms', 1e-1], 9:  ['300ms', 3e-1], 10: ['1s', 1.0],     11: ['3s', 3.0],
        12: ['10s', 1e1],    13: ['30s', 3e1],    14: ['100s', 1e2],   15: ['300s', 3e2],
        16: ['1ks', 1e3],    17: ['3ks', 3e3],    18: ['10ks', 1e4],   19: ['30ks',	3e4],
    }
    
    FILTER_SLOPE: dict = {0: 6, # dB/oct
                          1: 12, 
                          2: 18, 
                          3: 24}

    RESERVE_MODE: dict = {0: "High Reserve",
                          1: "Normal",
                          2: "Low Noise"}
    
    
    # -----------
    # Constructor
    # -----------
    def __init__(self, connection,  backend, timeout_ms=5000):
        self._connection = connection
        self._backend = backend # 
        self._timeout_ms = timeout_ms # operation timeout in milliseconds
        self._amplifier = None

        logger.debug(f"SR830 Class created — connection: '{self._connection}', backend: '{self._backend or '(NI-VISA auto-detect)'}'")


    # -----------
    # Connections
    # -----------
    def connect(self):
        """
        Connect to the SR830 lock-in amplifier using the VISA connection
        """
        logger.info(f"Connecting to SR830 at '{self._connection}'...")
        
        rm = pyvisa.ResourceManager(self._backend)
        self._amplifier = rm.open_resource(self._connection)
        self._amplifier.timeout = self._timeout_ms
        self._amplifier.write_termination = "\n"
        self._amplifier.read_termination  = "\n"
        
        logger.info(f"Connected to: {self._amplifier.query('*IDN?')}")
    

    def disconnect(self):
        """
        Disconnect from the SR830 lock-in amplifier, closing the VISA resource
        """
        if self._amplifier is not None:
            try:
                self._write("LOCL 0")

            except Exception as e:
                logger.warning(f"Could not release remote lock on disconnect: {e}")

            self._amplifier.close()
            self._amplifier = None
            logger.info("Disconnected from SR830.")
    
    
    def __enter__(self):
        self.connect()
        return self
    
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
    
    
    # --------------
    # Communications
    # --------------
    def _check_connection(self):
        if self._amplifier is None:
            raise SR830Error("Not connected to SR830 amplifier. Call connect() first.")


    def _query(self, command):
        """
        Send a query command to the SR830 and return the response
        """
        self._check_connection()

        logger.debug(f"Query: '{command}'")
        response = self._amplifier.query(command)
        logger.debug(f"Response: '{response}'")

        return response
    
    
    def _write(self, command):
        """
        Send a write command to the SR830.
        """
        self._check_connection()

        logger.debug(f"Write: '{command}'")
        self._amplifier.write(command)
    
    
    # ----------------------------
    # REFERENCE and PHASE COMMANDS
    # ----------------------------
    def phase(self):
        # Get the reference phase shift
        return float(self._query("PHAS?"))

    def set_phase(self, phase):
        """
        Set the reference phase shift in degrees
        The value of x will be rounded to 0.01°
        Limited to -360 ≤ x ≤ 729.99 degrees and wrapped around at ±180°
        For example, the PHAS 541.0 command will set the phase to -179.00° (541-360=181=-179)
        """

        if not -360.0 <= phase <= 729.99:
            raise ValueError(f"Phase {phase} out of range (-360 to +729.99 degrees).")

        self._write(f"PHAS {phase:.2f}")
 
        logger.info(f"Phase set to {phase:.2f} degrees")


    def reference_source(self):
        # Get the reference source
        return int(self._query("FMOD?"))

    def set_reference_source(self, i):
        """
        Set the reference source
        Internal (i=1)
        External (i=0)
        """
        if i not in [0, 1]:
            raise ValueError(f"Reference source {i} out of range (0 or 1).")
        
        self._write(f"FMOD {i}")
        logger.info("Reference source set to %s", "Internal" if i else "External")


    def frequency(self):
        # Get the reference frequency
        return float(self._query("FREQ?"))
    
    def set_frequency(self, frequency):
        """
        Sets the frequency of the internal oscillator
        The value of f will be rounded to 5 digits or 0.0001 Hz, whichever is greater
        Limited to 0.001 ≤ f ≤ 102000.
        If the harmonic number is greater than 1, then the frequency is 
        limited to nxf ≤ 102 kHz where n is the harmonic number
        """
        if not 0.001 <= frequency <= 102_000:
            raise ValueError(f"Frequency {frequency} Hz out of range (0.001 - 102,000 Hz).")
        
        self._write(f"FREQ {frequency:.4f}")
        logger.info(f"Frequency set to {frequency:.4f} Hz")


    def reference_trigger(self):
        # Get the reference trigger mode
        return int(self._query("RSLP?"))

    def set_reference_trigger(self, i):
        """
        Set the reference trigger mode
        Sine zero crossing (i=0)
        TTL rising edge (i=1)
        TTL falling edge (i=2). 
        At frequencies below 1 Hz, the a TTL reference must be used
        """
        if i not in [0, 1, 2]:
            raise ValueError(f"Reference trigger {i} out of range (0, 1, or 2).")
        
        self._write(f"RSLP {i}")
    
    
    def detection_harmonic(self):
        # Get the detection harmonic
        return int(self._query("HARM?"))
    
    def set_detection_harmonic(self, i):
        """
        Set the lock-in to detect at the ith harmonic of the reference frequency
        i ranges from 1 to 19999
        i is limited by ixf ≤ 102 kHz
        If the value of i requires a detection frequency greater than 102 kHz, then the 
        harmonic number will be set to the largest value of i such that ixf ≤ 102 kHz
        """
        self._write(f"HARM {i}")
    
    
    def sine_amplitude(self):
        # Get the amplitude of the sine output
        return float(self._query("SLVL?"))
    
    def set_sine_amplitude(self, x):
        """
        Set the amplitude of the sine output
        x is voltage in Volts
        Limited to 0.004 ≤ x ≤ 5.000
        x will be rounded to 0.002V
        """
        if not 0 <= x <= 5:
            raise ValueError(f"Sine amplitude {x} out of range (0 - 5 V).")
        
        self._write(f"SLVL {x}")
        
    
    # -------------------------
    # INPUT and FILTER COMMANDS
    # -------------------------
    def input_configuration(self):
        # Get the input configuration
        return int(self._query("ISRC?"))
    
    def set_input_configuration(self, i):
        """
        Set the input configuration
        i = 0: A
        i = 1: A-B
        i = 2: I (1 MΩ)
        i = 3: I (100 MΩ)
        """
        if i not in [0, 1, 2, 3]:
            raise ValueError(f"Input configuration {i} out of range (0-3).")
        
        self._write(f"ISRC {i}")
    
    
    def input_shield_grounding(self):
        # Get the input shield grounding
        return int(self._query("IGND?"))
    
    def set_input_shield_grounding(self, i):
        """
        Set the input shield grounding
        i = 0: Float
        i = 1: Ground
        """
        if i not in [0, 1]:
            raise ValueError(f"Input shield grounding {i} out of range (0 or 1).")
        
        self._write(f"IGND {i}")
        
    
    def input_coupling(self):
        # Get the input coupling
        return int(self._query("ICPL?"))
    
    def set_input_coupling(self, i):
        """
        Set the input coupling
        i = 0: AC
        i = 1: DC
        """
        if not i in [0, 1]:
            raise ValueError(f"Input coupling {i} out of range (0 or 1).")
        
        self._write(f"ICPL {i}")
    
    
    def input_line_notch_filter(self):
        # Get the input line notch filter status
        return int(self._query("ILIN?"))
    
    def set_input_line_notch_filter(self, i):
        """
        Set the input line notch filter status
        i = 0: Out or no filters
        i = 1: Line notch in
        i = 2: 2xLine notch in
        i = 3: Both notch filters in
        """
        if i not in [0, 1, 2, 3]:
            raise ValueError(f"Input line notch filter {i} out of range (0-3).")
        
        self._write(f"ILIN {i}")
        

    # -------------------------------
    # GAIN and TIME CONSTANT COMMANDS
    # -------------------------------
    def sensitivity(self):
        # Get the sensitivity
        return int(self._query("SENS?"))

    def set_sensitivity(self, i):
        """
        Set the sensitivity
        i ranges from 0 to 26, values are given in the SENSITIVITY dictionary
        """
        if i not in self.SENSITIVITY:
            raise ValueError(f"Sensitivity {i} out of range (0-26).")
        
        self._write(f"SENS {i}")
        

    def reserve_mode(self):
        # Get the reserve mode
        return int(self._query("RMOD?"))
    
    def set_reserve_mode(self, i):
        """
        Set the reserve mode
        i = 0: High Reserve
        i = 1: Normal
        i = 2: Low Noise (minimum)
        """
        
        if i not in self.RESERVE_MODE:
            raise ValueError(f"Reserve mode {i} out of range (0, 1, or 2).")
        
        self._write(f"RMOD {i}")
        
    
    def time_constant(self):
        # Get the time constant
        return int(self._query("OFLT?"))
    
    def set_time_constant(self, i):
        """
        Set the time constant
        i ranges from 0 to 19, values are given in the TIME_CONSTANT dictionary
        
        Time constants greater than 30s may NOT be set if the harmonic 
        x ref. frequency (detection frequency) exceeds 200 Hz.
        """
        if i not in self.TIME_CONSTANT:
            raise ValueError(f"Time constant {i} out of range (0-19).")
        
        self._write(f"OFLT {i}")

    
    def low_pass_filter_slope(self):
        # Get the low pass filter slope
        return int(self._query("OFSL?"))
    
    def set_low_pass_filter_slope(self, i):
        """
        Set the low pass filter slope
        i = 0: 6 dB/octave
        i = 1: 12 dB/octave
        i = 2: 18 dB/octave
        i = 3: 24 dB/octave
        """
        if i not in self.FILTER_SLOPE:
            raise ValueError(f"Low pass filter slope {i} out of range (0-3).")
        
        self._write(f"OFSL {i}")
        
    
    def synchronous_filter(self):
        # Get the synchronous filter status
        return int(self._query("SYNC?"))
    
    def set_synchronous_filter(self, i):
        """
        Set the synchronous filter status
        i = 0: Off
        i = 1: Synchronous filtering below 200 Hz
        Synchronous filtering is turned on only if the detection frequency 
        (reference x harmonic number) is less than 200 Hz.
        """
        if i not in [0, 1]:
            raise ValueError(f"Synchronous filter {i} out of range (0 or 1).")
        
        self._write(f"SYNC {i}")
    
    
    # ---------------------------
    # DISPLAY and OUTPUT COMMANDS
    # ---------------------------
    
    
    
    # -----------------------------
    # AUX INPUT and OUTPUT COMMANDS
    # -----------------------------
    def aux_input(self):
        # Get the aux input voltages in Volts
        return float(self._query("OAUX?"))
    

    def aux_output(self):
        # Get the aux output voltage in Volts
        return float(self._query("AUXV?"))

    def set_aux_output(self, i, x):
        """
        Set the aux output voltage in Volts
        i selects an Aux Output (1, 2, 3 or 4)
        x is the output voltage to set
        Limited to -10.500 ≤ x ≤ 10.500
        """
        if i not in [1, 2, 3, 4]:
            raise ValueError(f"Aux output {i} out of range (1-4).")
        
        if not -10.5 <= x <= 10.5:
            raise ValueError(f"Aux output voltage {x} out of range (-10.5 - 10.5 V).")

        self._write(f"AUXV {i} {x}")
    
    
    # --------------
    # SETUP COMMANDS
    # --------------
    
    
    
    # --------------
    # AUTO FUNCTIONS
    # --------------
    
 

    # ---------------------
    # DATA STORAGE COMMANDS
    # ---------------------
    
    
    
    # ----------------------
    # DATA TRANSFER COMMANDS
    # ----------------------
    
    
    
    # -------------------------
    # STATUS REPORTING COMMANDS
    # -------------------------
    