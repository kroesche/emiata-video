#!/usr/bin/env python

# SPDX-License-Identifier: MIT
#
# Copyright 2022 Joseph Kroesche
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import datetime
import argparse
import tempfile
import cv2 as cv
import ffmpeg
import os

_verbose = False
_quiet = False

# TODO make all this stuff configurable
font = cv.FONT_HERSHEY_PLAIN
fontscale = 0.9
lineheight = 16
logarea = (640, 180)
logpos = (20, 20)
logpadl = 10
logpadt = 20
logfg = (255, 255, 255)
logbg = (40, 40, 40)
logalpha = 0.4

textposx = logpos[0] + logpadl
textposy = logpos[1] + logpadt
logtl = logpos
logbr = (logpos[0] + logarea[0], logpos[1] + logarea[1])

# maintains a list of text lines in the log display buffer
# based on log file timestamps
# can be iterated to get the present set of lines
class LogBuffer(object):
    def __init__(self, filename, maxlines=10):
        self._fmt = "%Y-%m-%d %H:%M:%S.%f"
        self._max = maxlines
        self._file = open(filename, "rt")
        self._nextline = self._file.readline().strip()
        self._offset = datetime.datetime.strptime(self._nextline[:26], self._fmt).timestamp()
        self._nextts = self._offset
        self._file.seek(0)
        self._buf = []

    # update the buffer content according to the timestamp
    # it will iterate through lines in the input text log file and compare
    # the timestamp of the line against the timestamp arg to this function
    # once the input timestamp is the same or past the time of the log file line,
    # then that line is added to the log buffer. older lines are removed to
    # not exceed the max number of lines
    # more than one line can be added as a result of this function call
    def update(self, timestamp):
        if self._nextline:
            while (timestamp + self._offset) >= self._nextts:
                self._buf.append(self._nextline)
                self._nextline = self._file.readline().strip()
                self._nextts = datetime.datetime.strptime(self._nextline[:26], self._fmt).timestamp()
            while len(self._buf) > self._max:
                self._buf.pop(0)

    def close(self):
        self._file.close()

    # access the lines of the log buffer as an iterator
    def __iter__(self):
        return iter(self._buf)

def add_log_overlay(infile, logfile, outfile):
    # open the video capture
    cap = cv.VideoCapture(infile)
    if not cap.isOpened():
        print(f"error opening input video file {infile}")
        exit()

    # get the frame rate and size of the input video
    # and some other properties just for information
    fps = cap.get(cv.CAP_PROP_FPS)
    width = int(cap.get(cv.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv.CAP_PROP_FRAME_HEIGHT))
    codec = int(cap.get(cv.CAP_PROP_FOURCC))
    numframes = cap.get(cv.CAP_PROP_FRAME_COUNT)
    bitrate = cap.get(cv.CAP_PROP_BITRATE)

    codecstr = "".join([chr((int(codec) >> (8 * i)) & 0xFF) for i in range(4)])

    if not _quiet:
        print(f"Opening video {infile} for overlay processing.")

    if _verbose:
        print(f"Properties: {width}x{height}, {fps} fps, {codecstr}, {bitrate} bps")

    # open the output video writer
    # TODO should the video format be configurable
    # or should it use the same format as input
    fourcc = cv.VideoWriter_fourcc(*'avc1')
    writer = cv.VideoWriter(outfile, fourcc, fps, (width, height))

    if _verbose:
        print(f"Writing to output file {outfile}")

    # create the log buffer
    lb = LogBuffer(logfile)

    if not _quiet:
        progress_delta = int(numframes / 50)

    # iterate over all frames to add text overlay
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if not _quiet:
            framenum = cap.get(cv.CAP_PROP_POS_FRAMES)
            if framenum % progress_delta == 0:
                print(".", flush=True, end="")

        # create a rectangle overlay for text
        overlay = frame.copy()
        cv.rectangle(overlay, logtl, logbr, logbg, -1)
        newframe = cv.addWeighted(overlay, logalpha, frame, 1-logalpha, 0)

        # get the current video time and update the log buffer
        play_time = int(cap.get(cv.CAP_PROP_POS_MSEC)) # gives msec
        lb.update(play_time / 1000.0) # convert to seconds timestampt fmt

        # write the text into the overlay box
        for linenum, text in enumerate(lb):
            cv.putText(newframe, text,
                       (textposx, textposy + (linenum * lineheight)),
                       font, fontscale, logfg, 1, cv.LINE_AA)

        # at this point we could write newframe to the output and it would
        # create the video file output with the gray box and text
        # however the putText can allow the text to overflow the overlay
        # box. So copy just the overlay box (which will include the text)
        # back to the original frame. This will have the effect of cropping
        # any text that overflows the overlay box.

        # copy pixels from one numpy frame to the other
        frame[logtl[1]:logbr[1], logtl[0]:logbr[0]] = newframe[logtl[1]:logbr[1], logtl[0]:logbr[0]]

        # save the updated frame
        writer.write(frame)

    if not _quiet:
        print("\nFinished creating text overlay")
    lb.close()
    writer.release()
    cap.release()

"""
ffmpeg -i $OUTPUT1 -i $INSTFILE -filter_complex "[1:v]scale=400:280 [overlay], [0:v][overlay]overlay=800:20" tempout.mp4
"""

def combine_dash(infile, dashfile, audfile, outfile):
    if not _quiet:
        print(f"Processing dash instruments file {dashfile}")
    vid = ffmpeg.input(infile)
    dash = ffmpeg.input(dashfile)
    audio = ffmpeg.input(audfile)
    astream = audio.audio

    scaled = dash.filter("scale", size="400x280")
    overlaid = vid.overlay(scaled, eof_action="pass", x="800", y="20")
    out = ffmpeg.output(overlaid, astream, outfile)
    if _verbose:
        print("ffmpeg args:")
        print(out.get_args())
        print("running ffmpeg")
    out.run(quiet=not _verbose, overwrite_output=True)
    if not _quiet:
        print("Finished processing dash instruments")

def cli():
    global _verbose
    global _quiet

    parser = argparse.ArgumentParser(description="eMiata Video Processor")
    parser.add_argument('-v', "--verbose", action="store_true",
                        help="turn on extra output")
    parser.add_argument('-q', "--quiet", action="store_true",
                        help="silence all output")
    parser.add_argument('-i', "--input", required=True, help="input video file")
    parser.add_argument('-l', "--logfile", required=True, help="input log text file")
    parser.add_argument('-d', "--dash", required=True, help="input dash instruments video cap")
    parser.add_argument('-o', "--output", default="processed.mp4",
                        help="output video file (default=processed.mp4)")

    args = parser.parse_args()

    # set verbosity level
    _verbose = True if args.verbose else False

    # set quiet level
    _quiet = True if args.quiet else False

    # create a temporary file for the intermediate product
    _, tmpfile = tempfile.mkstemp(suffix=".mp4")

    add_log_overlay(args.input, args.logfile, tmpfile)
    combine_dash(tmpfile, args.dash, args.input, args.output)
    os.remove(tmpfile)

if __name__ == "__main__":
    cli()
