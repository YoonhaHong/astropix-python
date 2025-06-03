import ROOT
import os
import argparse

parser = argparse.ArgumentParser(description='Astropix Driver Code')
parser.add_argument('dirname', type=str, help='Directory containing the files to check alignment.')
args = parser.parse_args()

c1 = ROOT.TCanvas("c1", "", 1000, 1000)
nplane = 0
files = [f for f in os.listdir(args.dirname) if f.endswith('.root')]
if not files:
    print("No .root files found in the directory.")
    exit(1)

cols = []
rows = []
for file in files:
    filepath = os.path.join(args.dirname, file)
    print(f"Checking alignment for {file}...")

    # Open the ROOT file
    root_file = ROOT.TFile(filepath)
    if not root_file.IsOpen():
        print(f"Failed to open {file}.")
        continue

    # Check for alignment tree
    col = root_file.Get("ColLocation")
    if not col:
        print(f"No 'ColLocation' found in {file}.")
        continue

    row = root_file.Get("RowLocation")
    if not row:
        print(f"No 'RowLocation' found in {file}.")
        continue

    col.Draw()

    cols.append(col)
    rows.append(row)
    nplane += 1

    root_file.Close()

print(f"Found {nplane} planes with alignment data.")
c1.Divide(nplane, 2)
for i, (col, row) in enumerate(zip(cols, rows)):
    c1.cd(i + 1)
    col.Draw("col:row")
    col.SetTitle(f"Column Location for Plane {i + 1}")
    c1.cd(i + 1 + nplane)
    row.Draw("row:col")
    row.SetTitle(f"Row Location for Plane {i + 1}")