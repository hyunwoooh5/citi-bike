#!/bin/zsh

BASE_URL="https://s3.amazonaws.com/tripdata"

for i in {01..12};
do
    FILE_NAME="2024${i}-citibike-tripdata.zip"
    DOWNLOAD_URL="${BASE_URL}/${FILE_NAME}"

    wget -P ./ "${DOWNLOAD_URL}"

done


for i in {01..11};
do
    FILE_NAME="2025${i}-citibike-tripdata.zip"
    DOWNLOAD_URL="${BASE_URL}/${FILE_NAME}"

    wget -P ./data/ "${DOWNLOAD_URL}"

done


unzip "data/*.zip" -d "data/"
rm "data/*.zip"

