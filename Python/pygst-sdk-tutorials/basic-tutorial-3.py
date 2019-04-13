#!/usr/bin/env python3
"""
basic-tutorial-3: Dynamic pipelines
https://gstreamer.freedesktop.org/documentation/tutorials/basic/dynamic-pipelines.html
"""

import sys

import gi

gi.require_version('Gst', '1.0')
from gi.repository import Gst

Gst.init(None)


# Handler for the pad-added signal
def pad_added_handler(src, new_pad, data):
    print("Received new pad '%s' from '%s':" % (new_pad.get_name(),
                                                src.get_name()))

    # convert element is passed in as data
    sink_pad = data.get_static_pad("sink")

    # If our converter is already linked, we have nothing to do here
    if sink_pad.is_linked():
        print("We are already linked. Ignoring.")
        return

    # Check the new pad's type
    new_pad_caps = new_pad.get_current_caps()
    new_pad_struct = new_pad_caps.get_structure(0)
    new_pad_type = new_pad_struct.get_name()

    # This works, too:
    # new_pad_type = new_pad.query_caps(None).to_string()

    if not new_pad_type.startswith("audio/x-raw"):
        print("It has type '%s' which is not raw audio. Ignoring." %
              new_pad_type)
        return

    # Attempt the link
    if new_pad.link(sink_pad) != Gst.PadLinkReturn.OK:
        print("Type is '%s' but link failed." % new_pad_type)
    else:
        print("Link succeeded (type '%s')." % new_pad_type)


# Create the elements
source = Gst.ElementFactory.make("uridecodebin", "source")
convert = Gst.ElementFactory.make("audioconvert", "convert")
sink = Gst.ElementFactory.make("autoaudiosink", "sink")

# Create the empty pipeline
pipeline = Gst.Pipeline.new("test-pipeline")

if not source or not convert or not sink or not pipeline:
    print("Not all elements could be created.", file=sys.stderr)
    exit(-1)

# Build the pipeline
# Note that we are NOT linking the source at this point. We will do it later.
pipeline.add(source)
pipeline.add(convert)
pipeline.add(sink)

if not Gst.Element.link(convert, sink):
    print("Elements could not be linked.", file=sys.stderr)
    exit(-1)

# Set the URI to play
source.set_property(
    "uri",
    "https://www.freedesktop.org/software/gstreamer-sdk/data/media/sintel_trailer-480p.webm"
)

# Connect to the pad-added signal
source.connect("pad-added", pad_added_handler, convert)

# Start playing
ret = pipeline.set_state(Gst.State.PLAYING)
if ret == Gst.StateChangeReturn.FAILURE:
    print("Unable to set the pipeline to the playing state.", file=sys.stderr)
    exit(-1)

# Wait until error or EOS
bus = pipeline.get_bus()

# Parse message
while True:
    message = bus.timed_pop_filtered(
        Gst.CLOCK_TIME_NONE,
        Gst.MessageType.STATE_CHANGED |
        Gst.MessageType.ERROR |
        Gst.MessageType.EOS
    )
    if message.type == Gst.MessageType.ERROR:
        err, debug_info = message.parse_error()
        print("Error received from element %s: %s" % (
            message.src.get_name(), err), file=sys.stderr)
        print("Debugging information: %s" % debug_info, file=sys.stderr)
        break
    elif message.type == Gst.MessageType.EOS:
        print("End-Of-Stream reached.")
        break
    elif message.type == Gst.MessageType.STATE_CHANGED:
        if message.src == pipeline:
            old_state, new_state, pending_state = message.parse_state_changed()
            print("Pipeline state changed from %s to %s." %
                  (old_state.value_nick, new_state.value_nick))
    else:
        print("Unexpected message received.", file=sys.stderr)

# Free resources
pipeline.set_state(Gst.State.NULL)
