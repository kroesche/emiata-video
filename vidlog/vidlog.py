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
import configparser
import ast
from progress.bar import IncrementalBar

_verbose = False
_quiet = False
"""
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
"""

class Config(object):
    def __init__(self, cfgfile=None):
        self._cfg = configparser.ConfigParser()
        if cfgfile:
            self._cfg.read(cfgfile)

        if self._cfg.has_section('LogOverlay'):
            cfglog = self._cfg['LogOverlay']
            self._log = LogConfig(config=cfglog)
        else:
            self._log = LogConfig()

        if self._cfg.has_section('DashOverlay'):
            cfgdash = self._cfg['DashOverlay']
            self._dash = DashConfig(config=cfgdash)
        else:
            self._dash = DashConfig()

        if self._cfg.has_section('TimeOverlay'):
            cfgdash = self._cfg['TimeOverlay']
            self._time = TimeConfig(config=cfgdash)
        else:
            self._time = TimeConfig()

    @property
    def log(self):
        return self._log

    @property
    def dash(self):
        return self._dash

    @property
    def time(self):
        return self._time

class LogConfig(object):
    _fontmap = {
            "FONT_HERSHEY_PLAIN": cv.FONT_HERSHEY_PLAIN
        }
    _default = {
        "lines": "36",
        "font": "FONT_HERSHEY_PLAIN",
        "fontscale": "0.9",
        "lineheight": "16",
        "width": "800",
        "height": "600",
        "x": "20",
        "y": "20",
        "padx": "10",
        "pady": "20",
        "fgcolor": "(255, 255, 255)",
        "bgcolor": "(40, 40, 40)",
        "alpha": "0.4"
        }

    def __init__(self, config=None):
        if config:
            cfg = config
        else:
            cfg = LogConfig._default

        self._cfg = cfg
        self.lines = int(cfg['lines'])
        self.font = LogConfig._fontmap[cfg['font']]
        self.fontscale = float(cfg['fontscale'])
        self.lineheight = int(cfg['lineheight'])
        self.width = int(cfg['width'])
        self.height = int(cfg['height'])
        self.x = int(cfg['x'])
        self.y = int(cfg['y'])
        self.padx = int(cfg['padx'])
        self.pady = int(cfg['pady'])
        self.fgcolor = ast.literal_eval(cfg['fgcolor'])
        self.bgcolor = ast.literal_eval(cfg['bgcolor'])
        self.alpha = float(cfg['alpha'])

class DashConfig(object):
    _default = {
        "width": "840",
        "height": "600",
        "x": "2990",
        "y": "20"
        }

    def __init__(self, config=None):
        if config:
            cfg = config
        else:
            cfg = DashConfig._default

        self._cfg = cfg
        self.width = int(cfg['width'])
        self.height = int(cfg['height'])
        self.x = int(cfg['x'])
        self.y = int(cfg['y'])

class TimeConfig(object):
    _default = {
        "font": "FONT_HERSHEY_PLAIN",
        "fontscale": "1.5",
        "width": "400",
        "height": "28",
        "x": "1720",
        "y": "20",
        "padx": "10",
        "pady": "20",
        "fgcolor": "(255, 255, 255)",
        "bgcolor": "(40, 40, 40)",
        "alpha": "0.4"
        }

    def __init__(self, config=None):
        if config:
            cfg = config
        else:
            cfg = TimeConfig._default

        self._cfg = cfg
        self.font = LogConfig._fontmap[cfg['font']]
        self.fontscale = float(cfg['fontscale'])
        self.width = int(cfg['width'])
        self.height = int(cfg['height'])
        self.x = int(cfg['x'])
        self.y = int(cfg['y'])
        self.padx = int(cfg['padx'])
        self.pady = int(cfg['pady'])
        self.fgcolor = ast.literal_eval(cfg['fgcolor'])
        self.bgcolor = ast.literal_eval(cfg['bgcolor'])
        self.alpha = float(cfg['alpha'])

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
            #while (timestamp + self._offset) >= self._nextts:
            while timestamp >= self._nextts:
                self._buf.append(self._nextline)
                self._nextline = self._file.readline().strip()
                if self._nextline:
                    self._nextts = datetime.datetime.strptime(self._nextline[:26], self._fmt).timestamp()
                else:
                    self._nextline = None
                    self._buf.append("---end of log---")
                    if _verbose:
                        print("end of text log")
                    break
            while len(self._buf) > self._max:
                self._buf.pop(0)

    def close(self):
        self._file.close()

    #@property
    #def timestamp(self):
    #    return self._offset

    # access the lines of the log buffer as an iterator
    def __iter__(self):
        return iter(self._buf)

# represents the video with log overlays
class VidLog(object):
    def __init__(self, vidfile, outfile, start=0, duration=0, cfg=None):
        self._props = VidProps(vidfile)
        if _verbose:
            print(self._props)
        self._timestamp = self._props.timestamp
        self._vidfile = vidfile
        self._outfile = outfile
        self._tmpfile = None
        self._start = start
        if duration == 0:
            self._duration = int(self._props.duration - self._start)
        else:
            self._duration = duration
        if cfg:
            self._cfg = cfg
        else:
            self._cfg = Config()

    def add_overlay(self, logfile):
        cfg = self._cfg.log  # convenience variable
        tfg = self._cfg.time

        # create a temporary file for the intermediate product
        _, tmpfile = tempfile.mkstemp(suffix=".mp4")
        self._tmpfile = tmpfile

        # open the video capture
        cap = cv.VideoCapture(self._vidfile)
        if not cap.isOpened():
            raise RuntimeError(f"error opening input video file {self._vidfile}")

        # get the frame rate and size of the input video
        # and some other properties just for information
        fps = cap.get(cv.CAP_PROP_FPS)
        width = int(cap.get(cv.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv.CAP_PROP_FRAME_HEIGHT))
        codec = int(cap.get(cv.CAP_PROP_FOURCC))
        numframes = cap.get(cv.CAP_PROP_FRAME_COUNT)
        bitrate = cap.get(cv.CAP_PROP_BITRATE)

        # assemble codec chars into a string ex: 'h', 'e', 'v', 'c'
        codecstr = "".join([chr((int(codec) >> (8 * i)) & 0xFF) for i in range(4)])

        if not _quiet:
            print(f"Opening video {self._vidfile} for overlay processing.")

        if _verbose:
            print(f"Properties: {width}x{height}, {fps} fps, {codecstr}, {bitrate} bps")

        # open the output video writer
        # TODO should the video format be configurable
        # or should it use the same format as input
        # gopro format seems to be hevc
        fourcc = cv.VideoWriter_fourcc(*'avc1')
        writer = cv.VideoWriter(tmpfile, fourcc, fps, (width, height))

        if _verbose:
            print(f"Adding logfile overlay from: {logfile}")
            print(f"Writing to output file {tmpfile}")

        # create the log buffer
        lb = LogBuffer(logfile, maxlines=cfg.lines)

        if not _quiet:
            bar = IncrementalBar("Seconds processed", max=self._duration)
            next_bar = (self._start * 1000) + 500

        # skip ahead N frames to start position
        if self._start > 0:
            start_frames = fps * self._start
            cap.set(cv.CAP_PROP_POS_FRAMES, start_frames)

        # iterate over all frames to add text overlay
        play_time = 0
        stop_time = (self._start + self._duration) * 1000
        while play_time < stop_time:
            ret, frame = cap.read()
            if not ret:
                if _verbose:
                    print("reached end of input video stream")
                break

            # get the current video time within this file (0-origin)
            # this is in msec
            play_time = int(cap.get(cv.CAP_PROP_POS_MSEC)) # gives msec
            # import pdb; pdb.set_trace()

            # compute the actual time in seconds, in timestamp format
            real_time = self._timestamp + (play_time / 1000.0)

            # maintain progress bar
            if not _quiet:
                if play_time > next_bar:
                    next_bar += 1000
                    bar.next()

            # create box overlay for time code
            overlay = frame.copy()
            topleft = (tfg.x, tfg.y)
            botright = (tfg.x + tfg.width, tfg.y + tfg.height)
            cv.rectangle(overlay, topleft, botright, tfg.bgcolor, -1)
            tcframe = cv.addWeighted(overlay, tfg.alpha, frame, 1-tfg.alpha, 0)
            # get the current position as timestamp
            # convert to human readable text
            tcstamp = datetime.datetime.fromtimestamp(real_time)
            tctext = tcstamp.isoformat(sep=' ')
            cv.putText(tcframe, tctext,
                       (tfg.x + tfg.padx, tfg.y + tfg.pady),
                       tfg.font, tfg.fontscale, tfg.fgcolor, 1, cv.LINE_AA)

            # copy timecode box into output frame
            frame[       tfg.y:tfg.y+tfg.height, tfg.x:tfg.x+tfg.width] = \
                 tcframe[tfg.y:tfg.y+tfg.height, tfg.x:tfg.x+tfg.width]

            # create a rectangle overlay for text
            overlay = frame.copy()
            topleft = (cfg.x, cfg.y)
            botright = (cfg.x + cfg.width, cfg.y + cfg.height)
            cv.rectangle(overlay, topleft, botright, cfg.bgcolor, -1)
            newframe = cv.addWeighted(overlay, cfg.alpha, frame, 1-cfg.alpha, 0)

            # import pdb; pdb.set_trace()
            #lb.update(play_time / 1000.0) # convert to seconds timestampt fmt
            lb.update(real_time)

            # write the text into the overlay box
            for linenum, text in enumerate(lb):
                cv.putText(newframe, text,
                           (cfg.x + cfg.padx,
                            cfg.y + cfg.pady + (linenum * cfg.lineheight)),
                            cfg.font, cfg.fontscale, cfg.fgcolor, 1, cv.LINE_AA)

            # at this point we could write newframe to the output and it would
            # create the video file output with the gray box and text
            # however the putText can allow the text to overflow the overlay
            # box. So copy just the overlay box (which will include the text)
            # back to the original frame. This will have the effect of cropping
            # any text that overflows the overlay box.

            # copy pixels from one numpy frame to the other
            frame[       cfg.y:cfg.y+cfg.height, cfg.x:cfg.x+cfg.width] = \
                newframe[cfg.y:cfg.y+cfg.height, cfg.x:cfg.x+cfg.width]

            # save the updated frame
            writer.write(frame)

        if not _quiet:
            bar.finish()
            print("\nFinished creating text overlay")
        lb.close()
        writer.release()
        cap.release()

    """
    ffmpeg -i $OUTPUT1 -i $INSTFILE -filter_complex "[1:v]scale=400:280 [overlay], [0:v][overlay]overlay=800:20" tempout.mp4
    """

    def add_dash(self, dashfile):
        cfg = self._cfg.dash  # convenience variable
        if not _quiet:
            print(f"Processing dash instruments file {dashfile}")
        vid = ffmpeg.input(self._tmpfile)
        dash = ffmpeg.input(dashfile, ss=self._start, t=self._duration)
        audio = ffmpeg.input(self._vidfile, ss=self._start, t=self._duration)
        astream = audio.audio

        size = f"{cfg.width}x{cfg.height}"
        scaled = dash.filter("scale", size=size)
        dashx = str(cfg.x)
        dashy = str(cfg.y)
        #overlaid = vid.overlay(scaled, eof_action="pass", x=dashx, y=dashy, enable="gte(t,5)")
        overlaid = vid.overlay(scaled, eof_action="pass", x=dashx, y=dashy)
        out = ffmpeg.output(overlaid, astream, self._outfile)
        if _verbose:
            print("ffmpeg args:")
            print(out.get_args())
            print("running ffmpeg")
        out.run(quiet=not _verbose, overwrite_output=True)
        if not _quiet:
            print("Finished processing dash instruments")


class VidProps(object):
    def __init__(self, vidfile):
        self._filename = vidfile
        probe = ffmpeg.probe(vidfile) 
        vidstream = None
        for stream in probe['streams']:
            if stream['codec_type'] == 'video':
                vidstream = stream
                break
        if vidstream:
            self._props = vidstream
            # get creation time string, remove trailing 'Z'
            ctstr = vidstream['tags']['creation_time'][:-1]
            ctdt = datetime.datetime.fromisoformat(ctstr)
            # get the timecode, which is just a time
            tcstr = vidstream['tags']['timecode']
            tcframes = tcstr[-2:]    # extract num frames
            tcstr = tcstr[:-3]      # chop off frames
            tc = datetime.time.fromisoformat(tcstr) # get time as whole seconds
            frac_sec = float(tcframes) / 30.0
            usecs = int(frac_sec * 1000000)
            tc = tc.replace(microsecond=usecs)  # add in the usecs
            # now we have timecode, and creation_time from file metadata
            # timecode is just time, not date, but time is accurate start time
            # wherease creation_time seems to be ~1 second off, but it has the date
            # take the date from creation_time, and use timecode to form new
            # timestamp
            timestamp = datetime.datetime.combine(ctdt.date(), tc)
            self._ts = timestamp.timestamp()
        else:
            raise RuntimeError(f"could not find video stream in file {vidfile}")

    @property
    def filename(self):
        return self._filename

    @property
    def dimension(self):
        w = self._props['width']
        h = self._props['height']
        return (w, h)

    @property
    def description(self):
        return self._props['codec_long_name']

    @property
    def bitrate(self):
        return int(self._props['bit_rate'])

    @property
    def framerate(self):
        fpsstr = self._props['avg_frame_rate']
        parts = fpsstr.split("/")
        if len(parts) == 1:
            return float(parts[0])
        else:
            return float(parts[0]) / float(parts[1])

    @property
    def duration(self):
        return float(self._props['duration'])

    @property
    def timestamp(self):
        return self._ts

    def __str__(self):
        desc = f"Video file '{self.filename}' properties:\n"
        desc += f"codec: {self.description}\n"
        desc += f"bitrate: {self.bitrate}, framerate: {self.framerate}\n"
        desc += f"duration: {self.duration}\n"
        desc += "start time: "
        desc += datetime.datetime.fromtimestamp(self.timestamp).isoformat(sep=' ')
        desc += '\n'
        return desc

def cli():
    global _verbose
    global _quiet

    #import pdb; pdb.set_trace()
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
    parser.add_argument('-t', "--duration", type=int, help="duration in seconds")
    parser.add_argument('-ss', "--start", type=int, help="start position in seconds")

    args = parser.parse_args()

    # set verbosity level
    _verbose = True if args.verbose else False

    # set quiet level
    _quiet = True if args.quiet else False

    vid = VidLog(vidfile=args.input, outfile=args.output, start=args.start, duration=args.duration)
    vid.add_overlay(args.logfile)
    vid.add_dash(args.dash)

#    props = VidProps(args.input)
#    print(props)
#    add_log_overlay(args.input, args.logfile, tmpfile)
#    combine_dash(tmpfile, args.dash, args.input, args.output)
#    os.remove(tmpfile)

if __name__ == "__main__":
    cli()
