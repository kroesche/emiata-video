# video.py/Open GoPro, Version 2.0 (C) Copyright 2021 GoPro, Inc. (http://gopro.com/OpenGoPro).
# This copyright was auto-generated on Wed, Sep  1, 2021  5:05:46 PM

# This program derived from Open GoPro 'video' demo program

"""Entrypoint for taking a video demo."""

import time
import logging
import argparse
from pathlib import Path
from typing import Tuple, Optional

from rich.console import Console

from open_gopro import GoPro, Params
from open_gopro.util import setup_logging

import datetime

logger = logging.getLogger(__name__)
console = Console()  # rich consoler printer


def main() -> int:
    """Main program functionality

    Returns:
        int: program return code
    """
    identifier, log_location, wifi_interface = parse_arguments()

    global logger
    logger = setup_logging(logger, log_location)

    gopro: Optional[GoPro] = None
    return_code = 0
    try:
        with GoPro(identifier, wifi_interface=wifi_interface) as gopro:
            # Configure settings to prepare for video
            if gopro.is_encoding:
                gopro.ble_command.set_shutter(Params.Shutter.OFF)

            # Get the media list before
            #media_set_before = set(x["n"] for x in gopro.wifi_command.get_media_list())
            #media_set_before = set(x for x in gopro.wifi_command.get_media_list())
            file_list = gopro.wifi_command.get_media_list().flatten
            print("File List")
            print("---------")
            for f in file_list:
                ts = int(f['mod'])
                isotime  = datetime.datetime.fromtimestamp(ts).isoformat(sep=' ')
                print(f"{f['n']:20s} {isotime:24s} {f['s']:>12}")

            # Get the media list after
            #media_set_after = set(x["n"] for x in gopro.wifi_command.get_media_list().flatten)
            # The video (is most likely) the difference between the two sets
            #video = media_set_after.difference(media_set_before).pop()
            # Download the video
            #console.print("Downloading the video...")
            #gopro.wifi_command.download_file(camera_file=video, local_file=output_location)
            #console.print(f"Success!! :smiley: File has been downloaded to {output_location}")

    except KeyboardInterrupt:
        logger.warning("Received keyboard interrupt. Shutting down...")
    if gopro is not None:
        gopro.close()
    console.print("Exiting...")
    return return_code


def parse_arguments() -> Tuple[Optional[str], Path, Optional[str]]:
    """Parse command line arguments

    Returns:
        Tuple[str, Path, Path, float, Optional[str]]: (identifier, path to save log, path to store video,
            record_time, wifi interface)
    """
    parser = argparse.ArgumentParser(description="Connect to a GoPro camera, take a video, then download it.")
    parser.add_argument(
        "-i",
        "--identifier",
        type=str,
        help="Last 4 digits of GoPro serial number, which is the last 4 digits of the default camera SSID. If \
            not used, first discovered GoPro will be connected to",
        default=None,
    )
    parser.add_argument(
        "-l",
        "--log",
        type=Path,
        help="Location to store detailed log",
        default=Path("video.log"),
    )
    parser.add_argument(
        "-w",
        "--wifi_interface",
        type=str,
        help="System Wifi Interface. If not set, first discovered interface will be used.",
        default=None,
    )
    args = parser.parse_args()

    return args.identifier, args.log, args.wifi_interface


if __name__ == "__main__":
    # main()
    main()
