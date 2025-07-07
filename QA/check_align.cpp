
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
    hist -> Fit("gaus", "SQ", "", 3, 35);
    int hist_max_bin = hist->GetMaximumBin();        
    double hist_max = hist->GetBinCenter(hist_max_bin); 
    double hist_mean = hist->GetMean();
    double fit_mean = hist->GetFunction("gaus")->GetParameter(1);
    TLatex hist_max_label, mean_label, fit_label;
    hist->DrawCopy();
    //hist_max_label.DrawLatexNDC(0.1, 0.75, Form("Max at %d, %.2f mm from center", (int)hist_max, (hist_max - 17.5)*20./35.));
    mean_label.DrawLatexNDC(0.1, 0.65, Form("Mean at %.2f, %.2f mm from center", hist_mean, (hist_mean - 17.5)*20./35.));
    //fit_label.DrawLatexNDC(0.1, 0.55, Form("GMean at %.2f, %.2f mm from center", fit_mean, (fit_mean - 17.5)*20./35.));

}

#include <TSystemDirectory.h>
#include <TSystemFile.h>
#include <TList.h>
#include <TFile.h>
#include <TH1F.h>
#include <TH2I.h>
#include <TString.h>
#include <TObject.h>

#include <iostream>
#include <vector>
#include <string>
#include <algorithm>

using namespace std;

int check_align(const string& dirname) {

    TSystemDirectory dir("mydir", dirname.c_str());
    TList* files = dir.GetListOfFiles();

    if (!files) {
        cerr << "Failed to read directory: " << dirname << endl;
        return 1;
    }

    vector<string> file_names;

    // 1. 파일 이름 수집
    TIter next(files);
    TObject* obj;
    while ((obj = next())) {
        string fname = obj->GetName();
        if (fname == "." || fname == "..") continue;
        if (fname.rfind(".root") == string::npos) continue;
        file_names.push_back(fname);
    }

    // 2. 정렬 - 문자열 기준 (REF0.root → REF1.root → REF2.root ...)
    sort(file_names.begin(), file_names.end());

    // 3. 파일 오픈 및 히스토그램 추출
    TFile* root_files[10];
    vector<TH1F*> cols;
    vector<TH1F*> rows;
    vector<TH2I*> hitmaps;
    int nplane = 0;

    for (const auto& fname : file_names) {
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

        TH2I* hitmap = (TH2I*)root_file->Get("Hitmap");
        if (!hitmap) {
            cerr << "No 'Hitmap' found in " << fname << endl;
            root_file->Close();
            continue;
        }

        hitmap->SetTitle(fname.c_str());

        cols.push_back(col);
        rows.push_back(row);
        hitmaps.push_back(hitmap);
        nplane++;
    }



    cout << "Total planes loaded: " << nplane << endl;

    TCanvas* c1 = new TCanvas("canvas1", "", 500*nplane, 1500);
    c1->Divide(nplane, 3);
    for (int i = 1; i < nplane+1; ++i) {

        c1->cd(i);
        gPad -> SetRightMargin(0.2);
        //gPad -> SetLogz();
//        hitmaps[i-1] -> GetZaxis() -> SetRangeUser(0, 300);
        hitmaps[i-1] -> DrawCopy("COLZ");

        c1->cd(i + nplane * 1);
        cols[i-1]->SetTitle(";Col Buffer;Counts");
        draw_hist(cols[i-1]);

        c1->cd(i + nplane * 2);
        rows[i-1]->SetTitle(";Row Buffer;Counts");
        draw_hist(rows[i-1]);


    }
    c1 -> SaveAs(Form("%s.pdf", dirname.substr(24).c_str()));

    for (int i = 0; i < nplane; ++i) {
        root_files[i]->Close();
    }

    return 0;
}
