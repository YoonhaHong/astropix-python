import matplotlib.pyplot as plt
import os

class HitPlotter:
    """
    Class for 2-D visualization of astroPix hits in real time.
    """

    def __init__(self, nPix = (40,40), d=0.5, outdir=None):
        """
        Class for 2-D visualization of astroPix hits in real time.

        nPix: number of pixels in the array (int for square arrays or tuple)
        d: Width of bars for strip visualization.
        outdir: If not None, save problematic events as pdf images into this directory.
        """

        if isinstance(nPix, int):
            self.nPix = (nPix, nPix)
        else:
            self.nPix = nPix
        self.d = d
        self.outdir = outdir
        plt.gcf().set_size_inches(7,7, forward=True)
        plt.axes().set_aspect('equal')
        
        if outdir is not None and not os.path.isdir(self.outdir):
            os.makedirs(self.outdir)


    def plot_event(self, row, col, eventID=None):
        """
        Display the row/column hits for one astroPix event in real time.
        In this 2-D visualization, one colored strip is plotted for
        each row and column hit.
        Strip colors correspond to the overall number of hits:
            * Green for one row, one column.
            * Red for more than two rows or columns.
            * Orange otherwise.
    
        row: list or numpy.array of row hit locations
        col: list of numpy.array of column hit locations
        eventID: event number or timestamp (for plot title)
        """

        plt.clf()
        ax = plt.gca()

        plt.axis([-1, self.nPix[1], -1, self.nPix[0]])

        if (len(col) == 1) and (len(row) == 1):
            theColor="green"
            theSize = "x-large"
        elif (len(col) > 2) or (len(row) > 2):
            theColor="red"
            theSize="x-small"
        else:
            theColor = "orange"
            theSize = "small"

        for x in col:
            plt.axvspan(x-self.d, x+self.d, alpha=0.4, facecolor=theColor, edgecolor="None" )
        
        for y in row:
            plt.axhspan(y-self.d, y+self.d, alpha=0.4, facecolor=theColor, edgecolor="None")
            

        plt.xticks(col, weight = 'bold', color=theColor, size=theSize)
        plt.yticks(row, weight = 'bold', color=theColor, size=theSize)

        title = f"Event {eventID}, {len(row)} + {len(col)} hits"
        plt.title(title)

        plt.xlabel("Column")
        plt.ylabel("Row")
        plt.tight_layout()
        plt.pause(1e-6)
        
        if self.outdir is not None and theColor in ["orange", "red"]:
            plt.savefig(f"{self.outdir}/event_{eventID}.pdf")

    
