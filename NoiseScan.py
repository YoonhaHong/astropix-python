"""
Take data with given time for each pixels
with online decoding

Author: Yoonha Hong
"""

from astropix import astropixRun
import os
import binascii
import pandas as pd
import numpy as np
import time
import logging
import argparse
from tqdm import tqdm
import warnings

from modules.setup_logger import logger

warnings.simplefilter(action='ignore', category=FutureWarning)

decode_fail_frame = pd.DataFrame({
                'readout': np.nan,
                'Chip ID': np.nan,
                'payload': np.nan,
                'location': np.nan,
                'isCol': np.nan,
                'timestamp': np.nan,
                'tot_msb': np.nan,
                'tot_lsb': np.nan,
                'tot_total': np.nan,
                'tot_us': np.nan,
                'hittime': np.nan
                }, index=[0]
)

#Init 
def main(args, row, col, fpgaCon:bool=True, fpgaDiscon:bool=True):

    # Ensures output directory exists
    if os.path.exists(args.outdir) == False:
        os.mkdir(args.outdir)

    if fpgaCon:
        # Prepare everything, create the object
        global astro 
        logger.info('Initiate FPGA connection')
        astro = astropixRun(chipversion=3) #initialize with always enabling injections (args.inject is always true)
    #Initiate asic with pixel mask as defined in yaml 
    astro.asic_init(yaml=args.yaml, analog_col=col)


    for r in range(0, 35, 1):
        for c in range(0, 35, 1):
            astro.disable_pixel(c, r)

    astro.enable_pixel(col=col, row=row)

    astro.init_voltages(vthreshold=args.threshold) 

    astro.enable_spi() 
    astro.asic_configure()
    logger.info("Chip configured")
    astro.dump_fpga()
    

    i = 0
    fname=args.name + f"_r{row}c{col}_"
    # Save final configuration to output file    

    if args.saveascsv: # Here for csv
        csvpath = args.outdir +'/' + fname + time.strftime("%Y%m%d-%H%M%S") + '.csv'
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
        while time.time() <= end_time:
            readout = astro.get_readout()


            if readout: # Checks if hits are present
                # Writes the hex version to hits
                bitfile.write(f"{i}\t{str(binascii.hexlify(readout))}\n")
                bitfile.flush()
                #print(binascii.hexlify(readout))

                string_readout=str(binascii.hexlify(readout))[2:-1]
                try:
                    hits = astro.decode_readout(readout, i, chip_version=3, printer = True)
                except IndexError:
                            errors += 1
                            logger.warning(f"Decoding failed. Failure on readout {i}")
                            # We write out the failed decode dataframe
                            hits = decode_fail_frame
                            hits.readout = i
                            hits.hittime = time.time()
                finally:
                    i+=1
                    # If we are saving a csv this will write it out. 
                    if args.saveascsv:
                        csvframe = pd.concat([csvframe, hits])
            else: time.sleep(0.001)


    # Ends program cleanly when a keyboard interupt is sent.
    except KeyboardInterrupt:
        logger.info("Keyboard interupt. Program halt!")
    # Catches other exceptions
    except Exception as e:
        logger.exception(f"Encountered Unexpected Exception! \n{e}")
    finally:
        if args.saveascsv: 
            csvframe.index.name = "dec_order"
            csvframe.to_csv(csvpath) 
        bitfile.close() # Close open file       
        if fpgaDiscon:
            astro.close_connection() # Closes SPI
            logger.info('FPGA Connection ended')
        logger.info("Program terminated successfully")

    

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Astropix Driver Code')
    parser.add_argument('-n', '--name', default='', required=False,
                    help='Option to give additional name to output files upon running')

    parser.add_argument('-o', '--outdir', default='.', required=False,
                    help='Output Directory for all datafiles')
    
    parser.add_argument('-y', '--yaml', action='store', type=str, default = 'testconfig_v3',
                    help = 'filepath (in config/ directory) .yml file containing chip configuration. Default: config/testconfig.yml (All pixels off)')
    
    parser.add_argument('-t', '--threshold', type = float, action='store', default=80,
                    help = 'Threshold voltage for digital ToT (in mV). DEFAULT 80mV')

    parser.add_argument('-C', '--colrange', action='store', default=[0, 34], type=int, nargs=2,
                    help =  'Loop over given range of columns. Default: 0 34')

    parser.add_argument('-R', '--rowrange', action='store', default=[0, 34], type=int, nargs=2,
                    help =  'Loop over given range of rows. Default: 0 34')
    
    parser.add_argument('-c', '--saveascsv', action='store_true', default=True, required=False, 
                    help='save output files as CSV. If False, save as txt. Default: FALSE')

    parser.add_argument('-a', '--analog', action='store', required=False, type=int, default = 0,
                    help = 'Turn on analog output in the given column. Default: Column 0.')

    parser.add_argument('-M', '--maxtime', type=float, action='store', default=5,
                    help = 'Maximum run time (in seconds)')

    parser.add_argument
    args = parser.parse_args()

    loglevel = logging.INFO
    formatter = logging.Formatter('%(asctime)s:%(msecs)d.%(name)s.%(levelname)s:%(message)s')
    sh = logging.StreamHandler()
    sh.setFormatter(formatter)

    logging.getLogger().addHandler(sh) 
    logging.getLogger().setLevel(loglevel)

    logger = logging.getLogger(__name__)


    first = True

    with tqdm(total=(args.rowrange[1] - args.rowrange[0] + 1), desc="Processing Rows", unit="row") as pbar_row:
        for r in range(args.rowrange[0], args.rowrange[1] + 1, 1):
            
            # Create the inner tqdm progress bar for columns
            with tqdm(total=(args.colrange[1] - args.colrange[0] + 1), desc=f"Row {r}", unit="col", leave=False) as pbar_col:
                for c in range(args.colrange[0], args.colrange[1] + 1, 1):

                    if c > 34: continue
                    if r > 34: continue

                    if first:  # first - connect to FPGA but leave open
                        main(args, r, c, fpgaDiscon=False)
                        first = False
                    elif c == args.colrange[1] and r == args.rowrange[1]:  # final - disconnect from FPGA upon completion
                        main(args, r, c, fpgaCon=False)
                    else:  # for bulk of pixels, FPGA is already open
                        main(args, r, c, fpgaCon=False, fpgaDiscon=False)

                    # Update the column progress bar
                    pbar_col.update(1)
                    os.system('cls' if os.name == 'nt' else 'clear')
                    # Optionally, add a small sleep for better visualization of progress
                    time.sleep(0.05)  # Adjust as necessary

                # Update the row progress bar after completing all columns for this row
                pbar_row.update(1)
                    
            
