import threading

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
        0:  ['2nV/fA', 2e-9],   1:  ['5nV/fA', 5e-9],   2:  ['10nV/fA', 1e-8],  3:  ['20nV/fA', 2e-8],
        4:  ['50nV/fA', 5e-8],  5:  ['100nV/fA', 1e-7], 6:  ['200nV/fA', 2e-7], 7:  ['500nV/fA', 5e-7],
        8:  ['1uV/pA', 1e-6],   9:  ['2uV/pA', 2e-6],   10: ['5uV/pA', 5e-6],   11: ['10uV/pA', 1e-5],
        12: ['20uV/pA', 2e-5],  13: ['50uV/pA', 5e-5],  14: ['100uV/pA', 1e-4], 15: ['200uV/pA', 2e-4],
        16: ['500uV/pA', 5e-4], 17: ['1mV/nA', 1e-3],   18: ['2mV/nA', 2e-3],   19: ['5mV/nA', 5e-3],
        20: ['10mV/nA', 1e-2],  21: ['20mV/nA', 2e-2],  22: ['50mV/nA', 5e-2],  23: ['100mV/nA', 1e-1],
        24: ['200mV/nA', 2e-1], 25: ['500mV/nA', 5e-1], 26: ['1V/µA', 1.0]
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

    DISPLAY_PARAM: dict = {
        0: "X", 1: "Y", 2: "R", 3: "θ", 4: "Noise",
        5: "Aux In 1", 6: "Aux In 2", 7: "Aux In 3", 8: "Aux In 4",
        9: "Aux Out 1", 10: "Aux Out 2", 11: "Phase", 12: "Mark",
    }
    DISPLAY_RATIO: dict = {
        0: "None", 1: "Aux In 1", 2: "Aux In 2", 3: "Aux In 3", 4: "Aux In 4",
    }
    EXPAND: dict = {0: "×1", 1: "×10", 2: "×100"}

    # -----------
    # Constructor
    # -----------
    def __init__(self, connection,  backend, timeout_ms=5000):
        self._connection = connection
        self._backend = backend
        self._timeout_ms = timeout_ms  # operation timeout in milliseconds
        self._amplifier = None
        self._rm = None
        self._lock = threading.Lock()  # protect VISA from concurrent callback access

        logger.debug(f"SR830 Class created — connection: '{self._connection}', backend: '{self._backend or '(NI-VISA auto-detect)'}'")


    # -----------
    # Connections
    # -----------
    def connect(self):
        """
        Connect to the SR830 lock-in amplifier using the VISA connection
        """
        logger.info(f"Connecting to SR830 at '{self._connection}'...")

        self._rm = pyvisa.ResourceManager(self._backend)
        self._amplifier = self._rm.open_resource(self._connection)
        self._amplifier.timeout = self._timeout_ms
        self._amplifier.write_termination = "\n"
        self._amplifier.read_termination  = "\n"

        # OUTX 1 routes all responses over GPIB (essential — without this all
        # queries time out because the instrument sends replies to RS-232 by default).
        # Use OUTX 0 for RS-232 connections.
        self._amplifier.write("OUTX 1")

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
            if self._rm is not None:
                self._rm.close()
                self._rm = None
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
        Send a query command to the SR830 and return the response.
        Thread-safe: acquires the instrument lock for the full query/response cycle.
        """
        with self._lock:
            self._check_connection()
            logger.debug(f"Query: '{command}'")
            response = self._amplifier.query(command)
            logger.debug(f"Response: '{response}'")
            return response


    def _write(self, command):
        """
        Send a write command to the SR830.
        Thread-safe: acquires the instrument lock before writing.
        """
        with self._lock:
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
        if not 1 <= i <= 19999:
            raise ValueError(f"Detection harmonic {i} out of range (1–19999).")
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
        if not 0.004 <= x <= 5.000:
            raise ValueError(f"Sine amplitude {x} out of range (0.004 – 5.000 Vrms).")
        
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
    def display_config(self, i):
        """Get display channel i (1 or 2) config — returns (param_index, ratio_index)"""
        if i not in [1, 2]:
            raise ValueError(f"Display channel {i} must be 1 or 2.")
        resp = self._query(f"DDEF? {i}")
        j, k = resp.split(",")
        return int(j), int(k)

    def set_display_config(self, i, j, k=0):
        """
        Set display channel i (1 or 2) to parameter j with ratio k.
        j: 0=X, 1=Y, 2=R, 3=θ, 4=Noise, 5-8=AuxIn1-4, 9-10=AuxOut1-2, 11=Phase, 12=Mark
        k: 0=None, 1-4=AuxIn1-4 (ratio denominator)
        """
        if i not in [1, 2]:
            raise ValueError(f"Display channel {i} must be 1 or 2.")
        if j not in self.DISPLAY_PARAM:
            raise ValueError(f"Display parameter {j} out of range (0–12).")
        if k not in self.DISPLAY_RATIO:
            raise ValueError(f"Display ratio {k} out of range (0–4).")
        self._write(f"DDEF {i}, {j}, {k}")
        logger.info(f"Display {i} set to {self.DISPLAY_PARAM[j]}, ratio: {self.DISPLAY_RATIO[k]}")

    def display_value(self, i):
        """Read the current value shown on display channel i (1 or 2)"""
        if i not in [1, 2]:
            raise ValueError(f"Display channel {i} must be 1 or 2.")
        return float(self._query(f"OUTR? {i}"))

    def front_panel_output(self, i):
        """Get front panel output source for channel i (1=CH1, 2=CH2)"""
        if i not in [1, 2]:
            raise ValueError(f"Output channel {i} must be 1 or 2.")
        return int(self._query(f"FPOP? {i}"))

    def set_front_panel_output(self, i, j):
        """
        Set front panel output source for channel i (1 or 2).
        CH1 (i=1): j=0 → tracks CH1 display, j=1 → X
        CH2 (i=2): j=0 → tracks CH2 display, j=1 → Y
        """
        if i not in [1, 2]:
            raise ValueError(f"Output channel {i} must be 1 or 2.")
        if j not in [0, 1]:
            raise ValueError(f"Output source {j} must be 0 or 1.")
        self._write(f"FPOP {i}, {j}")
        src = "Display" if j == 0 else ("X" if i == 1 else "Y")
        logger.info(f"Front panel output CH{i} set to {src}")
    def get_display_mode(self, channel):
        """
        Get the output offset and expand (display mode) for a channel.
        channel: 1 or 2 (CH1 / CH2)
        Returns (offset_percent, expand_index)
            offset_percent: current output offset as a percentage (−105.00 to +105.00)
            expand_index:   0 = ×1,  1 = ×10,  2 = ×100  (see EXPAND dict)
        Uses VISA command: OEXP? {channel}
        """
        if channel not in [1, 2]:
            raise ValueError(f"Channel {channel} must be 1 or 2.")
        resp = self._query(f"OEXP? {channel}")
        x, j = resp.split(",")
        return float(x), int(j)

    def set_display_mode(self, channel, offset_pct=0.0, expand=0):
        """
        Set the output offset and expand (display mode) for a channel.
        channel:    1 or 2 (CH1 / CH2)
        offset_pct: output offset in percent (−105.00 to +105.00)
        expand:     expand index — 0 = ×1,  1 = ×10,  2 = ×100  (see EXPAND dict)
        Uses VISA command: OEXP {channel}, {offset_pct}, {expand}
        """
        if channel not in [1, 2]:
            raise ValueError(f"Channel {channel} must be 1 or 2.")
        if not -105.0 <= offset_pct <= 105.0:
            raise ValueError(f"Offset {offset_pct}% out of range (−105 to +105).")
        if expand not in self.EXPAND:
            raise ValueError(f"Expand index {expand} out of range (0=×1, 1=×10, 2=×100).")
        self._write(f"OEXP {channel}, {offset_pct:.2f}, {expand}")
        logger.info(f"CH{channel} output: offset={offset_pct:.2f}%, expand={self.EXPAND[expand]}")

    
    

    # -----------------------------
    # AUX INPUT and OUTPUT COMMANDS
    # -----------------------------
    def aux_input(self, i):
        """
        Read the voltage on Aux Input channel i (1–4) in Volts.
        Aux inputs are hardware BNC read-only inputs; they cannot be set by software.
        Uses VISA command: OAUX? {i}
        """
        if i not in [1, 2, 3, 4]:
            raise ValueError(f"Aux input channel {i} out of range (1–4).")
        return float(self._query(f"OAUX? {i}"))


    def aux_output(self, i):
        """
        Read the voltage on Aux Output channel i (1–4) in Volts.
        Uses VISA command: AUXV? {i}
        """
        if i not in [1, 2, 3, 4]:
            raise ValueError(f"Aux output channel {i} out of range (1–4).")
        return float(self._query(f"AUXV? {i}"))

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
    # AUTO FUNCTIONS
    # --------------
    def auto_gain(self):
        """Execute auto gain — SR830 automatically adjusts sensitivity"""
        self._write("AGAN")
        sens = self.sensitivity()
        logger.info(f"Auto Gain complete — Sensitivity: {self.SENSITIVITY[sens][0]} (index {sens})")

    def auto_reserve(self):
        """Execute auto reserve — SR830 automatically adjusts reserve mode"""
        self._write("ARSV")
        res = self.reserve_mode()
        logger.info(f"Auto Reserve complete — Reserve: {self.RESERVE_MODE[res]}")

    def auto_phase(self):
        """Execute auto phase — SR830 automatically adjusts reference phase"""
        self._write("APHS")
        ph = self.phase()
        logger.info(f"Auto Phase complete — Phase: {ph:.2f}°")
    

    # ----------------------
    # DATA TRANSFER COMMANDS
    # ----------------------
    def read_parameters(self):
        """
        Read the X, Y, R, and Theta parameters via a single SNAP query.
        Returns (X, Y, R, theta) as floats.
        """
        values = self._query("SNAP? 1,2,3,4")
        parts = values.split(",")
        X     = float(parts[0])
        Y     = float(parts[1])
        R     = float(parts[2])
        theta = float(parts[3])
        logger.debug(f"SNAP read — X={X:.6f} Y={Y:.6f} R={R:.6f} θ={theta:.4f}")
        return X, Y, R, theta


    def read_all_params(self):
        """
        Read every instrument parameter in a single call and return them as a dict.

        Keys returned (where available):
            Measurements : X, Y, R, theta
            Reference    : frequency, phase, sine_amp, harmonic, ref_src, ref_trig
            Gain/TC      : sensitivity, reserve, time_constant, filter_slope, sync_filter
            Input        : input_cfg, input_gnd, input_cpl, notch
            Aux Inputs   : aux_in_1 … aux_in_4

        Any parameter that fails to read is omitted from the dict and a WARNING is logged.
        Using this method instead of individual reads reduces VISA round-trips and avoids
        concurrent access issues when the display-interval callback is running.
        """
        result = {}

        # ── Measurements (single SNAP query) ──────────────────────────────────
        try:
            values = self._query("SNAP? 1,2,3,4")
            p = values.split(",")
            result["X"]     = float(p[0])
            result["Y"]     = float(p[1])
            result["R"]     = float(p[2])
            result["theta"] = float(p[3])
        except Exception as e:
            logger.warning(f"read_all_params: SNAP? 1,2,3,4 failed: {e}")

        # ── Reference & Phase ─────────────────────────────────────────────────
        for key, cmd, cast in [
            ("frequency", "FREQ?", float),
            ("phase",     "PHAS?", float),
            ("sine_amp",  "SLVL?", float),
            ("harmonic",  "HARM?", int),
            ("ref_src",   "FMOD?", int),
            ("ref_trig",  "RSLP?", int),
        ]:
            try:
                result[key] = cast(self._query(cmd))
            except Exception as e:
                logger.warning(f"read_all_params: {cmd} failed: {e}")

        # ── Gain & Time Constant ──────────────────────────────────────────────
        for key, cmd, cast in [
            ("sensitivity",   "SENS?", int),
            ("reserve",       "RMOD?", int),
            ("time_constant", "OFLT?", int),
            ("filter_slope",  "OFSL?", int),
            ("sync_filter",   "SYNC?", int),
        ]:
            try:
                result[key] = cast(self._query(cmd))
            except Exception as e:
                logger.warning(f"read_all_params: {cmd} failed: {e}")

        # ── Input & Filter ────────────────────────────────────────────────────
        for key, cmd, cast in [
            ("input_cfg", "ISRC?", int),
            ("input_gnd", "IGND?", int),
            ("input_cpl", "ICPL?", int),
            ("notch",     "ILIN?", int),
        ]:
            try:
                result[key] = cast(self._query(cmd))
            except Exception as e:
                logger.warning(f"read_all_params: {cmd} failed: {e}")

        # ── Aux Inputs ────────────────────────────────────────────────────────
        for ch in range(1, 5):
            try:
                result[f"aux_in_{ch}"] = float(self._query(f"OAUX? {ch}"))
            except Exception as e:
                logger.warning(f"read_all_params: OAUX? {ch} failed: {e}")

        logger.debug(f"read_all_params: {len(result)} parameters read successfully")
        return result



    # -------------------------
    # STATUS REPORTING COMMANDS
    # -------------------------
    