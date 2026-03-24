import pyvisa
import time

class SR830:
    
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
    
    def __init__(self, connection,  backend, timeout_ms=5000):
        self.connection = connection
        self.backend = backend # 
        self._timeout_ms = timeout_ms # operation timeout in milliseconds
        
    
    def connect(self):
        "Connect to the SR830 lock-in amplifier using the VISA connection"

        # argument '@py' if using pyvisa-py (if no NI-VISA installed)
        #rm = pyvisa.ResourceManager()
        
        while self.amplifier == None:
            print("Trying to connect to SR830...")
            rm = pyvisa.ResourceManager(self.backend)
            self.amplifier = rm.open_resource(self.connection)
            time.sleep(1)
        
        print("Connected to: ", self.amplifier.query("*IDN?"))
        
    
    def disconnect(self):
        "Disconnect from the SR830 lock-in amplifier."
        pass
    
    
    def __enter__(self):
        self.connect()
        return self
    
    
    def __exit__(self):
        self.disconnect()
                             
                             
    def query(self, command):
        "Send a query command to the SR830 and return the response."
        response = self.amplifier.query(command)
        return response
    
    
    def write(self, command):
        "Send a write command to the SR830."
        self.amplifier.write(command)
        
            
    """
    print(self.amplifier.query("FREQ?"))

    self.amplifier.write("OFLT 10")
    print(self.amplifier.query("OFLT ?"))

    self.amplifier.write("SENS 11")
    print(self.amplifier.query("SENS ?"))

    self.amplifier.write("SYNC 1")
    print(self.amplifier.query("SYNC ?"))
    """