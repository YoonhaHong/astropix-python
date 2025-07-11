# -*- coding: utf-8 -*-
""""""
"""
Created on Fri Jun 25 16:28:27 2021

@author: Nicolas Striebig
"""
from bitstring import BitArray

from core.nexysio import Nexysio


class Voltageboard(Nexysio):
    """Configure GECCO Voltageboard"""

    def __init__(self, handle, pos: int, dacvalues: tuple[int, list[float]]) -> None:

        self._handle = handle

        self._pos = 0  # pos
        self._dacvalues = []  # dacvalues

        self._vcal = 1.0
        self._vsupply = 3.3

        self.pos = pos
        self.dacvalues = dacvalues

    def __vb_vector(self, pos: int, dacs: list[float]) -> BitArray:
        """Generate VB bitvector from position and dacvalues

        :param pos: Card slot
        :param dacs: List with DAC values

        :returns: Voltageboard config vector
        """

        vdacbits = BitArray()

        # Reverse List of dacs in-place
        dacs.reverse()

        for vdac in dacs:

            dacvalue = int(vdac * 16383 / self.vsupply / self.vcal)

            vdacbits.append(BitArray(uint=dacvalue, length=14))
            vdacbits.append(BitArray(uint=0, length=2))

        vdacbits.append(BitArray(uint=(0b10000000 >> (pos - 1)), length=8))

        return vdacbits

    @property
    def vcal(self) -> float:
        """Voltageboard calibration value

        Set DAC to 1V and write measured value to vcal
        """
        return self._vcal

    @vcal.setter
    def vcal(self, voltage: float) -> None:
        if 0.9 <= voltage <= 1.1:
            self._vcal = voltage

    @property
    def vsupply(self) -> float:
        """Voltage supply voltage

        Set voltageboard supply voltage
        """
        return self._vsupply

    @vsupply.setter
    def vsupply(self, voltage: float) -> None:
        if 2.7 <= voltage <= 3.3:
            self._vsupply = voltage

    @property
    def dacvalues(self) -> list[float]:
        """DAC voltages Tuple(Number of DACS, List Dacvalues)"""
        return self._dacvalues

    @dacvalues.setter
    def dacvalues(self, dacvalues: tuple[int, list[float]]) -> None:

        # Get number of dacs and values from tuple
        length, values = dacvalues

        # if length(values) > length strip values
        # if length(values) < length append zeros
        values = values[:length] + [0] * (length - len(values))

        for index, value in enumerate(values):

            # If DAC out of range, set 0
            if not 0 <= value <= 1.8:
                values[index] = 0

        self._dacvalues = values

    @property
    def pos(self) -> int:
        """VB card position"""
        return self._pos

    @pos.setter
    def pos(self, pos: int) -> None:
        if 1 <= pos <= 8:
            self._pos = pos

    def update_vb(self) -> None:
        """Update voltageboard"""

        # Generate vector
        vdacbits = self.__vb_vector(self.pos, self.dacvalues)

        # print(f'update_vb pos: {self.pos} value: {self.dacvalues}\n')

        # Generate pattern
        vbbits = self.gen_gecco_pattern(12, vdacbits, 8)

        # Write to nexys
        self.write(vbbits)
