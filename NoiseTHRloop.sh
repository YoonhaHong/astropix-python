for thr in 80 130 140 170 200
do
	echo "THR = ${thr}"
	python3.12 NoiseScan_loop.py -o ../data/NoiseScan/HV200_THR${thr} -c -f -t ${thr} -M 0.25
done	


