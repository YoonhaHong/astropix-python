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

def main(args):

    # Ensures output directory exists
    if os.path.exists(args.outdir) == False:
        os.mkdir(args.outdir)
        
    # Prepare everything, create the object
    astro = astropixRun(chipversion=4) 

    #Initiate asic with pixel mask as defined in yaml and analog pixel in row0 defined with input argument -a
    astro.asic_init(yaml=args.yaml, analog_col = args.analog)

    for r in range(0, 13, 1):
        for c in range(0, 16, 1):
            astro.enable_pixel(c, r)

    if args.noisescandir is not None:
        noise_scan_summary = f"{args.noisescandir}/{args.name}_{args.threshold:.0f}_summary.csv"
        nss = pd.read_csv(noise_scan_summary)
        pixels_to_mask = nss[nss['disable'] > 0]
        nmask=0
        

        for index, row in pixels_to_mask.iterrows():
            print(f"Row: {row['row']}, Col: {row['col']}, Disable: {row['disable']}")
            astro.disable_pixel(int(row['col']), int(row['row']))
            nmask+=1
        print(nmask, " pixels are masked! ")

    astro.init_voltages(vthreshold=args.threshold)     

    #Enable final configuration
    astro.enable_spi() 
    astro.asic_configure()
    astro.update_asic_tdac_row(0)
    logger.info("Chip configured")
    astro.dump_fpga()

    i = 0
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
                        pbar.update(round(elapsed_time - pbar.n,2))  # pbar.n is the current progress




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
            'id',
            'payload',
            'row',
            'col',
            'ts1',
            'tsfine1',
            'ts2',
            'tsfine2',
            'tsneg1',
            'tsneg2',
            'tstdc1',
            'tstdc2',
            'ts_dec1',
            'ts_dec2',
            'tot_us'
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
                hits = astro.decode_readout(rawdata, i, printer=False, chip_version=4)
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
    parser.add_argument('-n', '--name', default='v4+Ba133', required=False,
                    help='Option to give additional name to output files upon running')

    parser.add_argument('-o', '--outdir', default='/home/becal-astropix/AstroPix_yoonha/data/250225', required=False,
                    help='Output Directory for all datafiles')

    parser.add_argument('-y', '--yaml', action='store', type=str, default = 'testconfig_v4',
                    help = 'filepath (in config/ directory) .yml file containing chip configuration. Default: config/testconfig.yml (All pixels off)')

    parser.add_argument('-t', '--threshold', type = float, action='store', default=130,
                        help = 'Threshold voltage for digital ToT (in mV). DEFAULT value in yml OR 100mV if voltagecard not in yml')
    
    parser.add_argument('-ns', '--noisescandir', action='store', required=False, type=str, default = None,
                    help = 'directory path noise scan summary file containing chip noise infomation.')
    
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

    main(args)
