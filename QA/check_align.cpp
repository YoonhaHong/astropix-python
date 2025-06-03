
#include <TFile.h>
#include <TH1F.h>
#include <TSystemDirectory.h>
#include <TSystemFile.h>
#include <TList.h>
#include <TKey.h>
#include <TCanvas.h>
#include <TROOT.h>

#include <iostream>
#include <vector>
#include <string>

using namespace std;

void draw_hist(TH1F* hist) {
    hist -> Fit("gaus", "SQ", "", 0, 35);
    int hist_max_bin = hist->GetMaximumBin();        
    double hist_max = hist->GetBinCenter(hist_max_bin); 
    double hist_mean = hist->GetMean();
    double fit_mean = hist->GetFunction("gaus")->GetParameter(1);
    TLatex hist_max_label, mean_label, fit_label;
    hist->DrawCopy();
    hist_max_label.DrawLatexNDC(0.1, 0.75, Form("Max at %d, %.2f mm from center", (int)hist_max, (hist_max - 17.5)*20./35.));
    mean_label.DrawLatexNDC(0.1, 0.65, Form("Mean at %.2f, %.2f mm from center", hist_mean, (hist_mean - 17.5)*20./35.));
    fit_label.DrawLatexNDC(0.1, 0.55, Form("GMean at %.2f, %.2f mm from center", fit_mean, (fit_mean - 17.5)*20./35.));

}

int check_align(const string& dirname) {

    TSystemDirectory dir("mydir", dirname.c_str());
    TList* files = dir.GetListOfFiles();
    TFile* root_files[10];

    if (!files) {
        cerr << "Failed to read directory: " << dirname << endl;
        return 1;
    }

    vector<TH1F*> cols;
    vector<TH1F*> rows;
    int nplane = 0;

    TIter next(files);
    TObject* obj;

    while ((obj = next())) {
        string fname = obj->GetName();

        // Skip "." and ".." and non-.root files
        if (fname == "." || fname == ".." || fname.rfind(".root") == string::npos) continue;

        string filepath = dirname + "/" + fname;
        cout << "Checking alignment for " << fname << "..." << endl;

        root_files[nplane] = TFile::Open(filepath.c_str());
        TFile* &root_file = root_files[nplane];
        if (!root_file || root_file->IsZombie()) {
            cerr << "Failed to open " << fname << endl;
            continue;
        }

        TH1F* col = (TH1F*)root_file->Get("ColLocation");
        if (!col) {
            cerr << "No 'ColLocation' found in " << fname << endl;
            root_file->Close();
            continue;
        }

        TH1F* row = (TH1F*)root_file->Get("RowLocation");
        if (!row) {
            cerr << "No 'RowLocation' found in " << fname << endl;
            root_file->Close();
            continue;
        }

        cols.push_back(col);
        rows.push_back(row);
        nplane++;

    }

    cout << "Total planes loaded: " << nplane << endl;

    TCanvas* c1 = new TCanvas("canvas1", "", 500*nplane, 1500);
    c1->Divide(nplane, 3);
    for (int i = 1; i < nplane+1; ++i) {
        c1->cd(i);
        cols[i-1]->SetTitle(";Col Buffer;Counts");
        draw_hist(cols[i-1]);

        c1->cd(i + nplane);
        rows[i-1]->SetTitle(";Row Buffer;Counts");
        draw_hist(rows[i-1]);

        c1->cd(i + 2*nplane);


    }

    for (int i = 0; i < nplane; ++i) {
        root_files[i]->Close();
    }

    return 0;
}
