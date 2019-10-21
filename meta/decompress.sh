#!/bin/sh
# Run it in the project path to extract meta files.

if [ ! -f meta/meta/Tripitaka.csv ] ; then
    tgz_file=$1
    if [ -z $1 ] ; then
        tgz_file=meta/meta.tgz
    fi
    tar zxvf $tgz_file
fi

if [ ! -f sample/GL/GL_924_2_35.jpg ] ; then
    tgz_file=$1
    if [ -z $1 ] ; then
        tgz_file=meta/sample.tgz
    fi
    tar zxvf $tgz_file
fi
