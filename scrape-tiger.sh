#!/usr/bin/env bash
# Download and organize 2016 TIGER shapefile data

out_dir=tiger-2016
temp_directory=$out_dir/temp

cd "$(dirname "$0")"

mkdir -p $out_dir-src

# Download all zipped shapefile data from the 2016 TIGER website. I'm unsure how
# the url naming scheme works - there are gaps in the place numbers - so, to be
# safe, we try all place numbers from 00 to 99.
wget -P $out_dir \
    http://www2.census.gov/geo/tiger/TIGER2016/PLACE/tl_2016_{00..99}_place.zip

# One by one, unzip all of the zipped shapefile data and organize them
mkdir -p $temp_directory
trap "rm -rf $temp_directory" SIGINT SIGTERM

for zip in $out_dir/*.zip; do

    7za x -o$temp_directory $zip

    state=$(grep -Po "(?<=state, ).*(?=,)" -m 1 $temp_directory/*.shp.xml)

    mkdir -p "$out_dir/$state"
    mv -v $temp_directory/* "$out_dir/$state"
    mv -v $zip $out_dir-src

done

rm -rf $temp_directory
