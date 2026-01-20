# -*- coding: utf-8 -*-
""""""
"""
Created on Tue Dec 28 19:03:40 2021

@author: Nicolas Striebig
"""
import time
from tqdm import tqdm


def wait_progress(seconds: int):
    for _ in tqdm(range(seconds), desc=f'Wait {seconds} s'):
        time.sleep(1)
