#!/bin/zsh

BASE_URL="https://s3.amazonaws.com/tripdata"

for i in {01..12};
do
    FILE_NAME="2024${i}-citibike-tripdata.zip"
    DOWNLOAD_URL="${BASE_URL}/${FILE_NAME}"

    wget -P ./ "${DOWNLOAD_URL}"

done

unzip "*.zip"
rm "*.zip"