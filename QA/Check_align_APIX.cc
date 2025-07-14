// Update 25.06.15: Now considering ToT as dead time

#include "TApplication.h"
#include "TCanvas.h"
#include "TFile.h"
#include "TGraph.h"
#include "TH1.h"
#include "TH2.h"
#include "TString.h"
#include "TStyle.h"
#include "TTree.h"

#include <iostream>
#include <fstream>
#include <numeric>
#include <vector>

const int NTOP = 10;

using namespace std;
TH1F* GetTop10BinsFrom2D(TH2F* h2, const char* histname = "hist_top10") {
    std::vector<std::tuple<int, int, float>> bins;

    for (int x = 1; x <= h2->GetNbinsX(); ++x) {
        for (int y = 1; y <= h2->GetNbinsY(); ++y) {
            float content = h2->GetBinContent(x, y);
            if (content > 0)
                bins.emplace_back(x, y, content);
        }
    }

    std::sort(bins.begin(), bins.end(), [](const auto& a, const auto& b) {
        return std::get<2>(a) > std::get<2>(b);
    });

    int nTop = std::min(NTOP, (int)bins.size());
    TH1F* h1 = new TH1F(histname, Form("Top %d Hitmap Bins;;Counts",NTOP), nTop, 0, nTop);

    for (int i = 0; i < nTop; ++i) {
        auto [xbin, ybin, content] = bins[i];
        int col = h2->GetXaxis()->GetBinCenter(xbin);
        int row = h2->GetYaxis()->GetBinCenter(ybin);
        TString label = Form("c%d r%d", col, row);
        h1->SetBinContent(i + 1, content);
        h1->GetXaxis()->SetBinLabel(i + 1, label);
    }

    h1->LabelsOption("v", "X"); // x축 라벨 세로 출력
    return h1;
}

int Check_align_APIX(const int RunNo = 7025, const char *inPath = "../decoded")
{

    /*
    int RunNo = 0;
    char* inPath = nullptr;
    if( argc == 2 ){
        RunNo = atoi(argv[1]);
        inPath = "../25KEKDATA";
    }else if( argc == 3 ){
        RunNo = atoi(argv[1]);
        inPath = argv[2];
    }else{
        cout << "Usage: [RunNo] or [RunNo] [inPat]" << endl;
        return 1;
    }
    */
    cout << "RunNo: " << RunNo << ", Input Path: " << inPath << endl;
    const int time_diff_cut = 20;
    const char *outPath = "../output";
    const char *figPath = "../fig";
    const bool bDebug = false;
    long nEventsToSee = 0;
    //cin >> nEventsToSee;

    //----Reading AstroPix data----
    const int nChips = 3;
    TFile *file_apix[nChips];
    TTree *tree_apix[nChips];
    long nevents_apix[nChips];
    ULong64_t coarsetime_apix[nChips];
    UShort_t col_apix[nChips][5000];   // AstroPix Col
    UShort_t row_apix[nChips][5000];   // AstroPix Row
    UShort_t colts_apix[nChips][5000]; // AstroPix Col Timestamp
    UShort_t rowts_apix[nChips][5000]; // AstroPix Row Timestamp
    UShort_t ctot_apix[nChips][5000];  // AstroPix ToT at column
    UShort_t rtot_apix[nChips][5000];  // AstroPix ToT at row
    ULong64_t cttot_apix[nChips];      // AstroPix Total ToT at column
    ULong64_t rttot_apix[nChips];      // AstroPix Total ToT at row
    int chit[nChips];
    int rhit[nChips];

    for (int i = 0; i < nChips; i++)
    {
        const char *filename_apix = Form("%s/APIX_daq_%d_%d.root", inPath, i, RunNo);
        file_apix[i] = new TFile(filename_apix);
        tree_apix[i] = (TTree *)file_apix[i]->Get("APIXData");
        nevents_apix[i] = (long)tree_apix[i]->GetEntriesFast();

        tree_apix[i]->SetBranchAddress("ctime", coarsetime_apix + i);
        tree_apix[i]->SetBranchAddress("cch", col_apix[i]);
        tree_apix[i]->SetBranchAddress("rch", row_apix[i]);
        tree_apix[i]->SetBranchAddress("cts", colts_apix[i]);
        tree_apix[i]->SetBranchAddress("rts", rowts_apix[i]);
        tree_apix[i]->SetBranchAddress("ctot", ctot_apix[i]);
        tree_apix[i]->SetBranchAddress("rtot", rtot_apix[i]);
        tree_apix[i]->SetBranchAddress("CHit", chit + i);
        tree_apix[i]->SetBranchAddress("RHit", rhit + i);
        tree_apix[i]->SetBranchAddress("cttot", cttot_apix + i);
        tree_apix[i]->SetBranchAddress("rttot", rttot_apix + i);
    }

    //----Reading AstroPix data end----
    TH1::AddDirectory(kFALSE);
    TH2::AddDirectory(kFALSE);

    long i_apix[nChips];
    TH2F *Hitmap_AstroPix[nChips];
    for (int i = 0; i < nChips; i++)
    {
        i_apix[i] = 0;
        Hitmap_AstroPix[i] = new TH2F(Form("Hitmap_AstroPix_%i", i), Form("AstroPix%d Hitmap;AstroPix Col;AstroPix Row", i), 35, 0, 35, 35, 0, 35);
    }
    //----Define Histograms and Correlation Histograms end----

    for (int ic = 0; ic < nChips; ic++)
    {

        while (i_apix[ic] < nevents_apix[ic])
        //while (i_apix[ic] < nevents_apix[ic] or i_apix[ic] < nEventsToSee)
        {
            for (int c = 0; c < chit[ic]; c++)
            {
                for (int r = 0; r < rhit[ic]; r++)
                {
                    if (col_apix[ic][c] > 34)
                        continue;
                    if (row_apix[ic][r] > 34)
                        continue;
                    if (abs((int)colts_apix[ic][c] - (int)rowts_apix[ic][r]) > 1)
                        continue;
                    if (ctot_apix[ic][c] <= 0 or rtot_apix[ic][r] <= 0)
                        continue;
                    if (fabs(ctot_apix[ic][c] - rtot_apix[ic][r]) / ctot_apix[ic][c] > 0.1)
                        continue;

                    Hitmap_AstroPix[ic]->Fill(col_apix[ic][c], row_apix[ic][r]);
                } // row
            } // col
            i_apix[ic]++;
            tree_apix[ic]->GetEntry(i_apix[ic]);
        } // events

    } // Chips

    /*
out_file -> cd();
out_tree -> Write();
TDirectory* dir_hitmap = out_file -> mkdir("Hitmap");
dir_hitmap -> cd();
for(int i=0; i<nChips; i++) {
    Hitmap_AstroPix[i] -> Write();
}
dir_hitmap -> Write();
    */

    const int nHist = 4;
    TCanvas *c1 = new TCanvas("c1", "", 500 * nHist, 500 * nChips);
    c1->Divide(nHist, nChips);
    gStyle->SetOptStat("emr");
    gStyle->SetStatX(0.42); 
    gStyle->SetStatStyle(0);  
    //gStyle->SetStatBorderSize(0);
    for (int i = 0; i < nChips; i++)
    {
        c1->cd(i*nHist + 1);
        Hitmap_AstroPix[i]->DrawCopy("COLZ");
    }
        gStyle -> SetOptFit(1);
        gStyle->SetStatX(0.75); 
        gStyle->SetStatY(0.45);  
    for (int i = 0; i < nChips; i++)
    {

        c1->cd(i*nHist + 3);
        TH1F* tempX = (TH1F*)Hitmap_AstroPix[i]->ProjectionX(Form("ProjectionX_%d", i));
        tempX -> SetTitle(Form("A%d ProjectionX", i));
        tempX -> Fit("gaus", "SQ","SQ", 3, 35);
        tempX -> DrawCopy();

        c1->cd(i*nHist + 4);
        TH1F* tempY = (TH1F*)Hitmap_AstroPix[i]->ProjectionY(Form("ProjectionY_%d", i));
        tempY -> SetTitle(Form("A%d ProjectionY", i));
        tempY -> Fit("gaus", "SQ","SQ", 0, 35);
        tempY -> DrawCopy();
    }
    for (int i = 0; i < nChips; i++)
    {
        gStyle -> SetOptStat(0);
        c1->cd(i*nHist + 2);
        TH1F* h_top10 = GetTop10BinsFrom2D(Hitmap_AstroPix[i], Form("top10_%d", i));
        h_top10 -> SetTitle(Form("A%d Top 10 pixels", i));
        h_top10 -> GetXaxis() -> SetLabelSize(0.05);
        h_top10 -> GetXaxis() -> SetLabelOffset(0.0);
        h_top10->Draw("HIST");
    }

    return 1;
}
