#!/usr/bin/env bash

DATAPATH=/home/npl/AstroPix/data/20250724_CERN
LASTFOLDER=`ls -ltrh $DATAPATH | tail -1`
LDATAFOLDER=`echo $LASTFOLDER | awk '{ print $9 }'`
echo $LDATAFOLDER
ls -ltrh $DATAPATH/$LDATAFOLDER/*.log 
