"""
Take data with given time, and then decode offline

Author: Yoonha Hong
"""
 # aiming for fast readout
 # injection wit high rate 
 # with out decoding

#from msilib.schema import File
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

#from http.client import SWITCHING_PROTOCOLS
from astropix import astropixRun
import modules.hitplotter as hitplotter
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

def main(args):
        
    # Prepare everything, create the object 
    astro = astropixRun(chipversion=3, fpga_index=args.fpga_index) 

    #Initiate asic with pixel mask as defined in yaml and analog pixel in row0 defined with input argument -a

    astro.asic_init(yaml=args.yaml, analog_col = args.analog)

    for r in range(0, 35, 1):
        for c in range(3, 35, 1):
            astro.enable_pixel(c, r)
    
    # Disable pixels
    if args.masking is not None:
        pattern = r"c(\d+)r(\d+)"
        for match in re.findall(pattern, args.masking):
            col, row = map(int, match)
            print(f"Disabling pixel at Col: {col}, Row: {row}")
            astro.disable_pixel(col, row)

    astro.init_voltages(vthreshold=args.threshold)     

    #Enable final configuration
    astro.enable_spi() 
    astro.asic_configure()
    logger.info("Chip configured")
    astro.dump_fpga()

    i = 0
    ymlpath = os.path.join(args.outdir, args.name) + ".yml"
    bitpath = os.path.join(args.outdir, args.name) + ".log"

    """
    fname="" if not args.name else args.name+"_"

    # Save final configuration to output file    
    ymlpathout=args.outdir + "/"+ fname + time.strftime("%Y%m%d-%H%M%S")+".yml"
    try:
        astro.write_conf_to_yaml(ymlpathout)
    except FileNotFoundError:
        ypath = args.yaml.split('/')
        ymlpathout=args.outdir+"/"+ypath[1]+"_"+time.strftime("%Y%m%d-%H%M%S")+".yml"
        astro.write_conf_to_yaml(ymlpathout)
    # Prepare text files/logs
    bitpath = args.outdir + '/' + fname + time.strftime("%Y%m%d-%H%M%S") + '.log'
    # textfiles are always saved so we open it up 
    # Writes all the config information to the file
    """
    astro.write_conf_to_yaml(ymlpath)
    bitfile = open(bitpath,'w')
    bitfile.write(astro.get_log_header())
    bitfile.write(str(args))
    bitfile.write("\n")

    astro.dump_fpga()
    logger.info("Starting Run")

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

                        i+= 1  # Increment readout count

                        if i % 50 == 0:  # Print every 200 readouts(1.2s)
                            logger.info(f"{i}th readout: \n {binascii.hexlify(readout)[0:100]}...")  # Print first 100 characters of hex readout
                            #astro.decode_readout(readout, i, printer=True, chip_version=3) 




    # Ends program cleanly when a keyboard interupt is sent.
    except KeyboardInterrupt:
        logger.info("Keyboard interupt. Program halt!")
    # Catches other exceptions
    except Exception as e:
        logger.exception(f"Encountered Unexpected Exception! \n{e}")
    finally:
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

    parser.add_argument('fpga_index', type=int, action='store', default=0,
                    help='FPGA index to use. Default: 0')

    parser.add_argument('-n', '--name', default='w02s03', required=False,
                    help='Option to give additional name to output files upon running')

    parser.add_argument('-o', '--outdir', default='../data', required=False,
                    help='Output Directory for all datafiles')

    parser.add_argument('-y', '--yaml', action='store', type=str, default = 'config_v3_none_may28',
                    help = 'filepath (in config/ directory) .yml file containing chip configuration.')

    parser.add_argument('-t', '--threshold', type = float, action='store', default=200,
                        help = 'Threshold voltage for digital ToT (in mV). DEFAULT value in yml OR 200mV if voltagecard not in yml')
    
    parser.add_argument('-m', '--masking', action='store', required=False, type=str, default = None,
                        help = "Pixels to be masked. If None, no masking is applied. Format: 'c0r0,c1r1,c2r2' where cXrY is column X row Y. Default: None")
    
    parser.add_argument('-c', '--saveascsv', action='store_true', default=False, required=False, 
                    help='save output files as CSV. If False, save as txt. Default: FALSE')

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
    sh = logging.StreamHandler()
    sh.setFormatter(formatter)

    logging.getLogger().addHandler(sh) 
    logging.getLogger().setLevel(loglevel)

    logger = logging.getLogger(__name__)

    main(args)
