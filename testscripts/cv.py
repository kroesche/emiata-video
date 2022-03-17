import numpy as np
import cv2 as cv
from ffpyplayer.player import MediaPlayer
import time
import datetime

save_video = True
show_video = False

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

    def update(self, timestamp):
        if self._nextline:
            while (timestamp + self._offset) >= self._nextts:
                self._buf.append(self._nextline)
                self._nextline = self._file.readline().strip()
                self._nextts = datetime.datetime.strptime(self._nextline[:26], self._fmt).timestamp()
            while len(self._buf) > self._max:
                self._buf.pop(0)

    def __iter__(self):
        return iter(self._buf)

lb = LogBuffer("test_log.txt")

if save_video:
    fourcc = cv.VideoWriter_fourcc(*'avc1')
    out = cv.VideoWriter('output.mp4', fourcc, 30.0, (1280, 720))

cap = cv.VideoCapture("test_clip.mov")
if not cap.isOpened():
    print("Cannot open file")
    exit()

#player = MediaPlayer("test_clip.mov")
#start_time = time.time()

while True:
    ret, frame = cap.read()
    if not ret:
        print("cant read frame")
        break

#    _, val = player.get_frame(show=False)
#    if val == 'eof':
#        break

    overlay = frame.copy()

    cv.rectangle(overlay, logtl, logbr, logbg, -1)
    newframe = cv.addWeighted(overlay, logalpha, frame, 1 - logalpha, 0)

    play_time = int(cap.get(cv.CAP_PROP_POS_MSEC))
    lb.update(play_time / 1000.0)

    textframe = newframe.copy()

    for linenum, text in enumerate(lb):
        cv.putText(textframe, text, (textposx, textposy + (linenum * lineheight)),
                   font, fontscale, logfg, 1, cv.LINE_AA)

    frame[logtl[1]:logbr[1], logtl[0]:logbr[0]] = textframe[logtl[1]:logbr[1], logtl[0]:logbr[0]]

#    cv.putText(frame, msec, (640, 360), font, 4, (255, 255, 255), 2, cv.LINE_AA)
    if show_video:
        cv.imshow('frame', frame)
    if save_video:
        out.write(frame)

#    elapsed = (time.time() - start_time) * 1000
#    sleep = max(1, int(play_time - elapsed))

#    if cv.waitKey(sleep) == ord('q'):
#        break

#player.close_player()
cap.release()
cv.destroyAllWindows()

"""
Some notes

https://stackoverflow.com/questions/68364187/audio-and-video-synchronization-with-opencv-and-ffpyplayer
https://pyimagesearch.com/2016/03/07/transparent-overlays-with-opencv/
"""
