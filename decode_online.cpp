#include <iostream>
#include <fstream>
#include <string>
#include <thread>
#include <chrono>
#include <vector>
#include <iomanip>
#include <bitset>
#include "TFile.h"
#include "TTree.h"
#include "TH1D.h"
#include "TString.h"
#include <iostream>
#include <csignal>
#include <atomic>

#define SAMPLE_CLOCK_PERIOD_NS 5

using namespace std;
using namespace std::chrono;

const int WAIT_TIME_MS = 5000; // Initial wait time in milliseconds
const int CYCLE_READ_MS = 100; // Time to wait for new lines in milliseconds
const int CYCLE_DECODE_MS = 600; // Time to decode lines in milliseconds

std::atomic<bool> stop(false);  // 시그널 핸들러에서 안전하게 공유할 변수

void signal_handler(int signum) {
    std::cout << "\n[!] Interrupt signal (" << signum << ") received.\n";
    stop = true;
}

// Function to convert a hex string to a binary string
std::string hexToBinary(const std::string& hex) {
    std::string binary;
    for (char c : hex) {
        int value;
        if (c >= '0' && c <= '9') value = c - '0';
        else if (c >= 'a' && c <= 'f') value = 10 + c - 'a';
        else if (c >= 'A' && c <= 'F') value = 10 + c - 'A';
        else continue; // Skip invalid characters

        std::bitset<4> bits(value);
        binary += bits.to_string();
    }
    return binary;
}

// Function to extract isCol and index from the binary string
void extractInfo(const std::string& binary, bool& isCol, int& index, int& timestamp, float& ToT) {
    //std::cout << binary << std::endl;

    isCol = binary[7] == '1';

    index = 0;
    for(int i=0; i<6; i++){
        int p = 1 << i;
        if(binary[i]=='1') index += p;
    }

    timestamp = 0;
    for(int i=8; i<16; i++){
        int p = 1 << (i-8);
        if(binary[i]=='1') timestamp += p;
    }

    int ToT_MSB = 0;
    for(int i=16; i<20; i++){
        int p = 1 << (i-16);
        if(binary[i]=='1') ToT_MSB += p;
    }

    int ToT_LSB = 0;
    for(int i=24; i<32; i++){
        int p = 1 << (i-24);
        if(binary[i]=='1') ToT_LSB += p;
    }

    long ToT_total  = (ToT_MSB << 8) + ToT_LSB;
    ToT = (ToT_total * SAMPLE_CLOCK_PERIOD_NS) / 1000.0;

}

int decode_online(string filename){
    this_thread::sleep_for(chrono::milliseconds(WAIT_TIME_MS));
    ifstream file(filename);
    if (!file.is_open()) {
        cerr << "Error opening file: " << filename << endl;
        return 1;
    }
    std::signal(SIGINT, signal_handler);

    // ****************************** 
    // Define variables for the TTree
    // and histograms
    string inputFileName = filename;
    string RootFileName = filename; RootFileName.erase(RootFileName.end()-4, RootFileName.end());
    TFile* F = new TFile(Form("%s_online.root", RootFileName.c_str()), "recreate");
    TTree* T = new TTree("fpga", "fpga");
    string bstr("");
    vector<string> vstr;
    int fHitPacket;
    bool fIsCol[1000];
    int fIndex[1000];
    int fTimestamp[1000];
    float fToT[1000];
    //below is for matched hits 
    int fHit;
    int fRow[1000];
    int fCol[1000];
    float fToT_Mean[1000];
    float fToT_Col[1000];
    float fToT_Row[1000];
    int fTimestamp_Col[1000];
    int fTimestamp_Row[1000];

    //T->Branch("bstr", &bstr);
    T->Branch("vstr", &vstr);
    T->Branch("nhitpacket", &fHitPacket, "nhitpacket/i");
    T->Branch("iscol", fIsCol, "iscol[nhitpacket]/O");
    T->Branch("index", fIndex, "index[nhitpacket]/i");
    T->Branch("timestamp", fTimestamp, "timestamp[nhitpacket]/i");
    T->Branch("tot", fToT, "tot[nhitpacket]/F");
    //below is for matched hits 
    T->Branch("nhit", &fHit, "nhit/i");
    T->Branch("irow", fRow, "irow[nhit]/i");
    T->Branch("icol", fCol, "icol[nhit]/i");
    T->Branch("tot_mean", fToT_Mean, "tot_mean[nhit]/F");
    T->Branch("tot_col", fToT_Col, "tot_col[nhit]/F");
    T->Branch("tot_row", fToT_Row, "tot_row[nhit]/F");
    T->Branch("timestamp_col", fTimestamp_Col, "timestamp_col[nhit]/i");
    T->Branch("timestamp_row", fTimestamp_Row, "timestamp_row[nhit]/i");

    TH1F* ColLocation = new TH1F("ColLocation", ";Location;", 35, 0, 35);
    TH1F* RowLocation = new TH1F("RowLocation", ";Location;", 35, 0, 35);
    TH2F* ColToTvsLocation = new TH2F("ColToT", ";Col Location;ToT [us]", 35, 0, 35, 150, 0, 30);
    TH2F* RowToTvsLocation = new TH2F("RowToT", ";Row Location;ToT [us]", 35, 0, 35, 150, 0, 30);
    TH2I* Hitmap = new TH2I("Hitmap", ";Col;Row", 35, 0, 35, 35, 0, 35);
    // ****************************** 

    int nLine=0;
    T->Branch("nline", &nLine);
    file.seekg(0, ios::end);
    string line;
    vector<string> buffer;


    int nNoLine = 0;
    while(!stop){
        auto cycle_start = steady_clock::now();

        while(true){
            streampos pos = file.tellg();
            if( getline(file, line) ){
                buffer.push_back(line);
            } else {
                file.clear(); // Clear EOF flag
                file.seekg(pos); // Reset to previous position
                this_thread::sleep_for(milliseconds(CYCLE_READ_MS)); // Wait before next read
            }

            if(duration_cast<milliseconds>(steady_clock::now() - cycle_start).count() >= CYCLE_DECODE_MS){
                break;
            }
        }

        if(!buffer.empty()){
            for(auto& line : buffer){
                nLine++;
                vstr.clear();
                bstr = line;

                vector<int> RowIndex;
                vector<int> RowTimestamp;
                vector<float>	RowToT;

                vector<int> ColIndex;
                vector<int> ColTimestamp;
                vector<float>	ColToT;
                
                size_t pos = line.find("b'"); // Find the position of "b'"
                line = line.substr(pos + 2); // Extract the substring after "b'"
                line = line.substr(0, line.find("ffff")); // Remove everything after "ffff"

                while(line.length() > 10){
                    while( line.rfind("bc") == line.length()-2){
                        line = line.substr(0, line.length()-2);
                    }
                    if( line.rfind("20",line.length()-10) == line.length()-10){
                        size_t pos = line.rfind("20",line.length()-10);
                        vstr.push_back( line.substr(pos+2, 8));
                        line = line.substr(0,line.length()-10);
                    }else if( line.rfind("bc") == line.length()-2){
                        line = line.substr(0,line.length()-2);
                    }else{
                        break;
                    }
                }

                fHitPacket = 0;
                for (auto hex : vstr)
                {
                    std::string binary = hexToBinary(hex);
        
                    // Extract isCol and index
                    bool isCol;
                    int index;
                    int timestamp;
                    float ToT;
                    extractInfo(binary, isCol, index, timestamp, ToT);
        
                    if (1)
                    {
                        // Output the results
                        char ColRow = isCol ? 'c' : 'r';
                        std::cout << nLine << ' ' << hex;
                        std::cout << ": location " << ColRow << (int)index << ", timestamp = " << (int)timestamp
                                  << ", ToT = " << ToT << std::endl;
                    }
                    fIsCol[fHitPacket] = isCol;
                    fIndex[fHitPacket] = index;
                    fTimestamp[fHitPacket] = timestamp;
                    fToT[fHitPacket] = ToT;
                    fHitPacket++;
        
                    if (isCol)
                    {
                        ColIndex.push_back(index);
                        ColTimestamp.push_back(timestamp);
                        ColToT.push_back(ToT);
        
                        ColLocation->Fill(index);
                        ColToTvsLocation->Fill(index, ToT);
                    }
                    else
                    {
                        RowIndex.push_back(index);
                        RowTimestamp.push_back(timestamp);
                        RowToT.push_back(ToT);
        
                        RowLocation->Fill(index);
                        RowToTvsLocation->Fill(index, ToT);
                    }
                }
        
                fHit = 0;
                for(int c=0; c<ColIndex.size(); c++){
                    for(int r=0; r<RowIndex.size(); r++){
                        if(ColIndex[c] > 34) continue;
                        if(RowIndex[r] > 34) continue;
                        if(abs((int)ColTimestamp[c] - (int)RowTimestamp[r]) > 1) continue;
                        if(ColToT[c] <= 0 or RowToT[r] <= 0) continue;
                        if(fabs(ColToT[c] - RowToT[r]) / ColToT[c] > 0.1) continue;
        
                        fRow[fHit] = RowIndex[r];
                        fCol[fHit] = ColIndex[c];
                        Hitmap -> Fill(fCol[fHit], fRow[fHit]);

                        fToT_Mean[fHit] = (ColToT[c] + RowToT[r])/2.;
                        fToT_Col[fHit] = ColToT[c];
                        fToT_Row[fHit] = RowToT[r];
                        fTimestamp_Col[fHit] = ColTimestamp[c];
                        fTimestamp_Row[fHit] = RowTimestamp[r];
                        fHit++;


        
                    }
                }//Matching

                T->Fill();


            }
            buffer.clear(); // Clear the buffer after processing
        } else {
            nNoLine++;
            //cout << "No new lines to process... " << nNoLine << endl;
        }

        if(nNoLine >= 100){
            cout << "No new lines for 100 cycles, exiting..." << endl;
            stop=true; // Exit after 10 cycles with no new lines
        }
    }

    file.close();
    F->Write();
    F->Close();
    return 0;
}