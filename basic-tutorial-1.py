#!/usr/bin/env python3
"""
Basic tutorial 1: Hello world!
https://gstreamer.freedesktop.org/documentation/tutorials/basic/hello-world.html
"""

import gi

gi.require_version('Gst', '1.0')
from gi.repository import Gst


def main():
    Gst.init(None)

    # Build the pipeline
    pipeline = Gst.parse_launch(
        "playbin uri=https://www.freedesktop.org/software/gstreamer-sdk/data/media/sintel_trailer-480p.webm"
    )

    # Start playing
    pipeline.set_state(Gst.State.PLAYING)

    # Wait until error or EOS
    bus = pipeline.get_bus()
    msg = bus.timed_pop_filtered(
        Gst.CLOCK_TIME_NONE,
        Gst.MessageType.ERROR | Gst.MessageType.EOS
    )

    # Free resources
    pipeline.set_state(Gst.State.NULL)


if __name__ == '__main__':
    main()
