"""
Take data with given time, and then decode offline

Author: Yoonha Hong
"""
 # aiming for fast readout
 # injection wit high rate 
 # with out decoding

#from msilib.schema import File
#from http.client import SWITCHING_PROTOCOLS
from astropix import astropixRun
import modules.hitplotter as hitplotter
import os
import binascii
import pandas as pd
import numpy as np
import time
import logging
import argparse
import re
from tqdm import tqdm
import warnings

from modules.setup_logger import logger

warnings.simplefilter(action='ignore', category=FutureWarning)

def injection_each_pixel(args, astro, col, row):


    print(f"Start injecting for COL{col} ROW{row}")

    for r in range(0, 35, 1):
        for c in range(0, 35, 1):
            astro.disable_pixel(c, r)
            
    astro.asic.set_inj_col(col, True)
    astro.asic.set_inj_row(row, True)
    astro.enable_pixel(col=col, row=row)
    
    #Enable final configuration
    astro.enable_spi(args.clkdiv) 
    astro.asic_configure()
    logger.info("Chip configured")
    astro.dump_fpga()

    astro.start_injection()

    i = 0
    # Prepare text files/logs
    bitpath = os.path.join(args.outdir, f"c{col}r{row}.log")
    # textfiles are always saved so we open it up 
    bitfile = open(bitpath,'w')
    # Writes all the config information to the file
    bitfile.write(astro.get_log_header())
    bitfile.write(str(args))
    bitfile.write("\n")

    astro.dump_fpga()

    try: # By enclosing the main loop in try/except we are able to capture keyboard interupts cleanly

        start_time = time.time()
        end_time=start_time + float(args.maxtime)
        with tqdm(total=args.maxtime, desc="Processing", unit="s") as pbar:
                while time.time() <= end_time:
                    readout = astro.get_readout()

                    if readout:  # if there is data contained in the readout stream
                        # Writes the hex version to hits
                        bitfile.write(f"{i}\t{str(binascii.hexlify(readout))}\n")
                        bitfile.flush()  # simulate streaming
                        
                        # Update the progress bar every iteration or based on your desired frequency
                        elapsed_time = time.time() - start_time
                        pbar.update(round(elapsed_time - pbar.n,2))  # pbar.n is the current progress




    # Ends program cleanly when a keyboard interupt is sent.
    except KeyboardInterrupt:
        logger.info("Keyboard interupt. Program halt!")
    # Catches other exceptions
    except Exception as e:
        logger.exception(f"Encountered Unexpected Exception! \n{e}")
    finally:
        astro.stop_injection()
        bitfile.close() # Close open file        

        logger.info("Program terminated successfully")

        csvname = os.path.basename(bitpath)[:-4] + '_offline.csv'
        csvpath = os.path.join( os.path.abspath(args.outdir) , csvname )
        csvframe =pd.DataFrame(columns = [
                    'readout',
                    'Chip ID',
                    'payload',
                    'location',
                    'isCol',
                    'timestamp',
                    'tot_msb',
                    'tot_lsb',
                    'tot_total',
                    'tot_us',
                    'hittime'
            ])
        
    if args.saveascsv:
        f=np.loadtxt(bitpath, skiprows=7, dtype=str)
        #isolate only bitstream without b'...' structure 
        strings = [a[2:-1] for a in f[:,1]]
       
        for i, s in tqdm(enumerate(strings), desc=f'decoding... to {csvname}', ncols=100, unit='readouts', total=len(strings),
                         bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{percentage:3.0f}%]'):
            # Convert hex to binary and decode
            rawdata = list(binascii.unhexlify(s))
            try:
                hits = astro.decode_readout(rawdata, i, printer=False, chip_version=3)
                # Lose hittime - computed during decoding so this info is lost when decoding offline
                hits['hittime'] = 0.0
                # Populate csv
                csvframe = pd.concat([csvframe, hits])
            except IndexError:  # Cannot decode empty bitstream, so skip it
                continue

        #Save csv
        csvframe.index.name = "dec_order"
        logger.info(f"Saving to {csvpath}")
        csvframe.to_csv(csvpath)

        




    # END OF PROGRAM
    
if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Astropix Driver Code')
    parser.add_argument('-o', '--outdir', default='../data', required=False,
                    help='Output Directory for all datafiles')

    parser.add_argument('-y', '--yaml', action='store', type=str, default = 'config_v3_none_may28',
                    help = 'filepath (in config/ directory) .yml file containing chip configuration.')
    
    parser.add_argument('-clk', '--clkdiv', type = int, action='store', default=5,
                        help = 'SPI clk divider')

    parser.add_argument('-t', '--threshold', type = float, action='store', default=250,
                        help = 'Threshold voltage for digital ToT (in mV). DEFAULT value in yml OR 200mV if voltagecard not in yml')
    
    parser.add_argument('-v','--vinj', action='store', default = 700, type=float,
                    help = 'Specify injection voltage (in mV). DEFAULT None (uses value in yml)')
            
    parser.add_argument('-C', '--colrange', action='store', default=[3, 35], type=int, nargs=2,
                help =  'Column range for injection scan')
                
    parser.add_argument('-R', '--rowrange', action='store', default=[0, 35], type=int, nargs=2,
                help =  'Row range for injection scan')

    parser.add_argument('-p', '--inject_period', action='store', default=2, type=int,
                help =  'Period of injection 1: ~ 1 KHz, 2: ~ 500 Hz')

    parser.add_argument('-M', '--maxtime', type=float, action='store', default=12,
                    help = 'Maximum run time (in seconds)')
    
    parser.add_argument('-c', '--saveascsv', action='store_true', default=False, required=False, 
                    help='save output files as CSV. If False, save as txt. Default: FALSE')

    parser.add_argument('-a', '--analog', action='store', required=False, type=int, default = 0,
                    help = 'Turn on analog output in the given column. Default: Column 0.')


    parser.add_argument('-L', '--loglevel', type=str, choices = ['D', 'I', 'E', 'W', 'C'], action="store", default='I',
                    help='Set loglevel used. Options: D - debug, I - info, E - error, W - warning, C - critical. DEFAULT: I')

    parser.add_argument
    args = parser.parse_args()

    # Sets the loglevel
    ll = args.loglevel
    if ll == 'D':
        loglevel = logging.DEBUG
    elif ll == 'I':
        loglevel = logging.INFO
    elif ll == 'E':
        loglevel = logging.ERROR
    elif ll == 'W':
        loglevel = logging.WARNING
    elif ll == 'C':
        loglevel = logging.CRITICAL
    
    # Logging 

        # Ensures output directory exists
    if os.path.exists(args.outdir) == False:
        os.mkdir(args.outdir)
        
    # Prepare everything, create the object
    astro = astropixRun(chipversion=3) 

    #Initiate asic with pixel mask as defined in yaml and analog pixel in row0 defined with input argument -a
    astro.asic_init(yaml=args.yaml, analog_col = args.analog)
    


    astro.init_voltages(vthreshold=args.threshold)     

    astro.init_injection(inj_voltage=args.vinj, 
                             pulseperset=1, initdelay=100, inj_period=args.inject_period, clkdiv=300,
                             onchip=True) #If using v3, use injection created with integrated DACs on chip
    
    for col in range(args.colrange[0], args.colrange[1], 1):
        for row in range(args.rowrange[0], args.rowrange[1], 1):
            injection_each_pixel(args, astro, col, row)
            time.sleep(2) # Sleep to avoid overloading the SPI connection

    astro.close_connection() # Closes SPI