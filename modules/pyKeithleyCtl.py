import numpy as np 
import pyvisa as visa
import yaml 
import time
import pandas as pd

VISA_RM = visa.ResourceManager('@py')
class KeithleySupply():
    
    '''Used to control a single Keithley 2450 Source Meter.'''
    
    
    def __init__(self, address, n_ch=1, visa_resource_manager=VISA_RM):
        resource_str = f'TCPIP0::{address:s}::INSTR'
        self.resource = VISA_RM.open_resource(resource_str, write_termination='\n', read_termination='\n')

        self.write = self.resource.write
        self.query = self.resource.query
        
        self.clear = self.resource.clear
        self.close = self.resource.close
                
    @property
    def IDN(self):
        return self.ask("*IDN?")
    
    @property
    def IDENTITY(self):
        return f"IDN: {self.IDN.split(',')[-2]} IP: {self.IP}"
        
    def ask(self, question, verbose=False):
        response = self.query(question)
        if verbose:
            print("Question: {0:s} - Response: {1:s}".format(question, str(response)))
        return response
    
    def tell(self, statement):
        return self.write(statement)
        
    def reset(self):
        return self.write("*RST")
    
    def init(self):
        return self.write("INIT")
        
    def wait(self):
        return self.write("*WAI")

    def enable_output(self):
        return self.tell(f"OUTP:STAT ON")
    
    def disable_output(self):
        return self.tell(f"OUTP:STAT OFF")
    
    def set_voltage(self, voltage):
        self.tell(f":SOURCE:FUNC VOLT")
        self.tell(f":SOURCE:VOLT {voltage}")

    def get_voltage(self):
        return self.ask(":SOURCE:VOLT?")
    
    def measure_current( self ):
        return self.ask(":MEASURE:CURRENT:DC?")
        
    def measure_voltage( self ):
        return self.ask(":MEASURE:VOLTAGE:DC?")

    def set_ocp(self, ocp):
        self.tell(f":SOURCe:VOLTage:ILIMit {ocp}")
    
    def get_ocp(self):
        return self.ask(":SOURCe:VOLTage:ILIMit?")
        
    def start_measurement(self, max_duration_s = 60*60, delay_s = 0.05):
        self.tell('SENS:FUNC "CURR"')
        self.tell("SENS:CURR:RANG:AUTO ON")
        
        self.tell(':TRACE:DELete "myBuffer"')
        bufferSize = int(2.0*max_duration_s/delay_s)
        
        
        self.tell(f'TRACE:MAKE "myBuffer", {bufferSize}' )
        self.tell(f':TRIGger:LOAD "LoopUntilEvent", COMM, 100, ENT, 1, "myBuffer"' )
        self.init()

    def stop_measurement(self, max_duration_s = 60*60, delay_s = 0.05):
        self.write('*TRG')
        nRow = int(self.ask(':TRAC:ACTUAL? "myBuffer"') )
        print(nRow)
        result =  self.ask(f':TRAC:DATA? 1, {nRow}, "myBuffer", REL, SEC, FRAC, SOUR, SOURSTAT, STAT, READ')
        
        return result, nRow

    def to_csv(self, result, nRow):
        
        nCol=7
        data=np.reshape( np.fromstring(result, sep=','), (nRow, nCol) )
        
        df =  pd.DataFrame(data, columns = "REL SEC FRAC SOUR SOURSTAT STAT READ".split() )
        
        df.SOURSTAT = df.SOURSTAT.astype(int)
        df.STAT = df.STAT.astype(int)
    
        return df