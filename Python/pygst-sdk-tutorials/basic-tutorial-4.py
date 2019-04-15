#!/usr/bin/env python3
"""
basic-tutorial-4: Time management
https://gstreamer.freedesktop.org/documentation/tutorials/basic/time-management.html
"""

import sys

import gi

gi.require_version('Gst', '1.0')
from gi.repository import Gst

Gst.init(None)


def handle_message(data, msg):
    if message.type == Gst.MessageType.ERROR:
        err, debug_info = message.parse_error()
        print("Error received from element %s: %s" % (message.src.get_name(), err), file=sys.stderr)
        print("Debugging information: %s" % debug_info, file=sys.stderr)
        data.terminate = True
    elif message.type == Gst.MessageType.EOS:
        print("End-Of-Stream reached.")
        data.terminate = True
    elif message.type == Gst.MessageType.DURATION_CHANGED:
        # The duration has changed, mark the current one as invalid
        data.duration = Gst.CLOCK_TIME_NONE
    elif message.type == Gst.MessageType.STATE_CHANGED:
        if message.src == data.playbin:
            old_state, new_state, pending_state = message.parse_state_changed()
            print("Pipeline state changed from %s to %s." %
                  (old_state.value_nick, new_state.value_nick))

            # Remember whether we are in the PLAYING state or not
            data.playing = (new_state == Gst.State.PLAYING)
            if data.playing:
                # We just moved to PLAYING. Check if seeking is possible
                query = Gst.Query.new_seeking(Gst.Format.TIME)
                if data.playbin.query(query):
                    (_, data.seek_enabled, start, end) = query.parse_seeking()
                    if data.seek_enabled:
                        print("Seeking is ENABLED from %s to %s" %
                              (Gst.TIME_ARGS(start), Gst.TIME_ARGS(end)))
                    else:
                        print("Seeking is DISABLED for this stream.")
                else:
                    print("Seeking query failed.", file=sys.stderr)
    else:
        print("Unexpected message received.", file=sys.stderr)


class CustomData:
    def __init__(self):
        self.playbin = None
        self.playing = False
        self.terminate = False
        self.seek_enabled = False
        self.seek_done = False
        self.duration = Gst.CLOCK_TIME_NONE


data = CustomData()

data.playing = False
data.terminate = False
data.seek_enabled = False
data.seek_done = False
data.duration = Gst.CLOCK_TIME_NONE

# Create the elements
data.playbin = Gst.ElementFactory.make("playbin", "playbin")

if not data.playbin:
    print("Not all elements could be created.", file=sys.stderr)
    exit(-1)

# Set the URI to play
data.playbin.set_property(
    "uri", "https://www.freedesktop.org/software/gstreamer-sdk/data/media/sintel_trailer-480p.webm")

# Start playing
ret = data.playbin.set_state(Gst.State.PLAYING)
if ret == Gst.StateChangeReturn.FAILURE:
    print("Unable to set the pipeline to the playing state.", file=sys.stderr)
    exit(-1)

# Listen to the bus
bus = data.playbin.get_bus()
while not data.terminate:
    message = bus.timed_pop_filtered(100 * Gst.MSECOND,
                                     Gst.MessageType.STATE_CHANGED |
                                     Gst.MessageType.ERROR |
                                     Gst.MessageType.EOS |
                                     Gst.MessageType.DURATION_CHANGED)

    # Parse message
    if message:
        handle_message(data, message)
    else:
        if data.playing:
            fmt = Gst.Format.TIME
            current = -1
            # Query the current position of the stream
            _, current = data.playbin.query_position(fmt)
            if not current:
                print("Could not query current position", file=sys.stderr)

            # If we didn't know it yet, query the stream duration
            if data.duration == Gst.CLOCK_TIME_NONE:
                _, data.duration = data.playbin.query_duration(fmt)
                if not data.duration:
                    print("Could not query current duration", file=sys.stderr)

            print("Position %s / %s" % (
                Gst.TIME_ARGS(current), Gst.TIME_ARGS(data.duration)))
            sys.stdout.flush()

            # If seeking is enabled, we have not done it yet, and the time is right, seek
            if data.seek_enabled and not data.seek_done and current > 10 * Gst.SECOND:
                print("\nReached 10s, performing seek...")
                data.playbin.seek_simple(Gst.Format.TIME,
                                         Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
                                         30 * Gst.SECOND)
                data.seek_done = True

# Free resources
data.playbin.set_state(Gst.State.NULL)
