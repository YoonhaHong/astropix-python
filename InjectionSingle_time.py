"""
Updated version of beam_test.py using the astropix.py module

Author: Autumn Bauman 
Maintained by: Amanda Steinhebel, amanda.l.steinhebel@nasa.gov
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

from modules.setup_logger import logger


# This sets the logger name.
logdir = "./runlogs/"
if os.path.exists(logdir) == False:
    os.mkdir(logdir)
logname = "./runlogs/AstropixRunlog_" + time.strftime("%Y%m%d-%H%M%S") + ".log"

#Initialize
def main(args):

    # Ensures output directory exists
    if os.path.exists(args.outdir) == False:
        os.mkdir(args.outdir)
        
    # Prepare everything, create the object
    astro = astropixRun(chipversion=3, inject=args.inject) 

    #Initiate asic with pixel mask as defined in yaml and analog pixel in row0 defined with input argument -a
    astro.asic_init(yaml=args.yaml, analog_col = args.analog)

    for r in range(0, 35, 1):
        for c in range(0, 35, 1):
            astro.disable_pixel(c, r)

    astro.init_voltages(vthreshold=args.threshold)     

    astro.enable_pixel(args.inject[1],args.inject[0])    
    astro.init_injection(inj_voltage=args.vinj, 
                             pulseperset=1, initdelay=100, inj_period=args.inject_period, clkdiv=300,
                             onchip=onchipBool)

    #Enable final configuration
    astro.enable_spi() 
    astro.asic_configure()
    logger.info("Chip configured")
    astro.dump_fpga()


    astro.start_injection()
    
    i = 0
    errors = 0 # Sets the threshold 
    

    fname="" if not args.name else args.name+"_"

    # Save final configuration to output file    
    ymlpathout=args.outdir +"/"+args.yaml+"_"+time.strftime("%Y%m%d-%H%M%S")+".yml"
    try:
        astro.write_conf_to_yaml(ymlpathout)
    except FileNotFoundError:
        ypath = args.yaml.split('/')
        ymlpathout=args.outdir+"/"+ypath[1]+"_"+time.strftime("%Y%m%d-%H%M%S")+".yml"
        astro.write_conf_to_yaml(ymlpathout)
    # Prepare text files/logs
    bitpath = args.outdir + '/' + fname + time.strftime("%Y%m%d-%H%M%S") + '.log'
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
                        pbar.update(elapsed_time - pbar.n)  # pbar.n is the current progress




    # Ends program cleanly when a keyboard interupt is sent.
    except KeyboardInterrupt:
        logger.info("Keyboard interupt. Program halt!")
    # Catches other exceptions
    except Exception as e:
        logger.exception(f"Encountered Unexpected Exception! \n{e}")
    finally:
        astro.stop_injection()   
        bitfile.close() # Close open file        
        astro.close_connection() # Closes SPI
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
        
        f=np.loadtxt(bitpath, skiprows=7, dtype=str)
        #isolate only bitstream without b'...' structure 
        strings = [a[2:-1] for a in f[:,1]]

        for i,s in enumerate(strings):
            #convert hex to binary and decode
            rawdata = list(binascii.unhexlify(s))
            try:
                hits = astro.decode_readout(rawdata, i, printer = False, chip_version=3)
                #Lose hittime - computed during decoding so this info is lost when decoding offline (don't even get relative times because they are processed in offline decoding at machine speed)
                hits['hittime']=0.0
                #Populate csv
                csvframe = pd.concat([csvframe, hits])
            except IndexError: #cannot decode empty bitstream so skip it
                continue

        #Save csv
        csvframe.index.name = "dec_order"
        logger.info(f"Saving to {csvpath}")
        csvframe.to_csv(csvpath)
        




    # END OF PROGRAM
    
if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Astropix Driver Code')
    parser.add_argument('-n', '--name', default='APSw101s04', required=False,
                    help='Option to give additional name to output files upon running')

    parser.add_argument('-o', '--outdir', default='/home/becal-astropix/AstroPix_yoonha/data_v3/data_astropix-python/eff_W08S05', required=False,
                    help='Output Directory for all datafiles')

    parser.add_argument('-y', '--yaml', action='store', type=str, default = 'testconfig_v3',
                    help = 'filepath (in config/ directory) .yml file containing chip configuration. Default: config/testconfig.yml (All pixels off)')

    parser.add_argument('-t', '--threshold', type = float, action='store', default=400,
                        help = 'Threshold voltage for digital ToT (in mV). DEFAULT value in yml OR 100mV if voltagecard not in yml')
        
    parser.add_argument('-v','--vinj', action='store', default = 500, type=float,
                    help = 'Specify injection voltage (in mV). DEFAULT None (uses value in yml)')
    
    parser.add_argument('-i', '--inject', action='store', default=[10, 10], type=int, nargs=2,
                help =  'Turn on injection in the given row and column. Default: No injection')

    parser.add_argument('-p', '--inject_period', action='store', default=2, type=int,
                help =  'Period of injection 1: ~ 1 KHz, 2: ~ 500 Hz')

    parser.add_argument('-a', '--analog', action='store', required=False, type=int, default = 0,
                    help = 'Turn on analog output in the given column. Default: Column 0.')

    parser.add_argument('-M', '--maxtime', type=float, action='store', default=12,
                    help = 'Maximum run time (in seconds)')

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
    formatter = logging.Formatter('%(asctime)s:%(msecs)d.%(name)s.%(levelname)s:%(message)s')
    fh = logging.FileHandler(logname)
    fh.setFormatter(formatter)
    sh = logging.StreamHandler()
    sh.setFormatter(formatter)

    logging.getLogger().addHandler(sh) 
    logging.getLogger().addHandler(fh)
    logging.getLogger().setLevel(loglevel)

    logger = logging.getLogger(__name__)

    #If using v2, use injection created by injection card
    #If using v3, use injection created with integrated DACs on chip
    onchipBool = True 

    main(args)
