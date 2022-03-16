#!/bin/bash

# TODO add command line options

# assumes video file and instrument video have already been
# trimmed to the desired length and that they match duration.
# The fps does not need to be the same because ffmpeg will fix that.

PYTHON=venv/bin/python
VIDFILE=test_clip.mov
AUDFILE=test_clip.aac
INSTFILE=vokoscreen.mp4
OUTPUT1=output.mp4
REDUCED=output_reduced.mp4
BITRATE=1000k

if [ ! -d venv ]; then
    python3 -m venv venv
    $PYTHON -m pip install -U pip wheel setuptools
    $PYTHON -m pip install opencv-python ffpyplayer
fi

# clean up prior products
rm -f $AUDFILE
rm -f $OUTPUT1
rm -f $REDUCED
rm -f tempout.mp4

# extract the audio from the original
# assumes audio is AAC. this should be changed to match whatever it really is
# does not re-encode if the types match
ffmpeg -i $VIDFILE -c copy -vn $AUDFILE

# generate text overlay video
# all file names are hard coded for now
# produces $OUTPUT1 with no audio
$PYTHON cv.py

# re-add audio to the output video
# does not re-encode
ffmpeg -i $OUTPUT1 -i $AUDFILE -c copy tempout.mp4
rm -f $OUTPUT1
mv tempout.mp4 $OUTPUT1

# add the instrument overlay
ffmpeg -i $OUTPUT1 -i $INSTFILE -filter_complex "[1:v]scale=400:280 [overlay], [0:v][overlay]overlay=800:20" tempout.mp4
rm -f $OUTPU1
mv tempout.mp4 $OUTPUT1

# clean the audio file
rm -f $AUDFILE

# generate a reduced bit rate version
ffmpeg -i $OUTPUT1 -b $BITRATE $REDUCED
