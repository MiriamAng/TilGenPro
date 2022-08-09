#!/bin/bash

# This script is controlled by the function "tilesGenerator" from the "preprocessing.py" script.

if [ $# -eq 2 ]
then 
  qupath script -p="$1" "$2" > /dev/null & PID=$!
else
  qupath script -i="$1" -p="$2" "$3" > /dev/null & PID=$ 
fi

echo "Please be patient while tiles are being generated, it may take a while."
printf "["
# While process is running...
while kill -0 $PID 2> /dev/null; do 
    printf  "#"
    sleep 1
done
printf "] done!"