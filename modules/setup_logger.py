# -*- coding: utf-8 -*-
""""""
"""
Created on Tue Dec 28 19:03:40 2021

@author: Nicolas Striebig
"""

import logging

# This sets the logger name.
# logname = "./runlogs/AstropixRunlog_" + datetime.datetime.strftime("%Y%m%d-%H%M%S") + ".log"
"""
# Loglevel
logging.basicConfig(filename=logname,
                    filemode='a',
                    format='%(asctime)s:%(msecs)d.%(name)s.%(levelname)s:%(message)s',
                    datefmt='%H:%M:%S',
                    level=logging.DEBUG)
"""

#formatter = logging.Formatter('%(asctime)s:%(msecs)d.%(name)s.%(levelname)s:%(message)s')
logger = logging.getLogger(__name__)
