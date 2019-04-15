#!/usr/bin/env python
"""
Basic tutorial 7: Multithreading and Pad Availability
https://gstreamer.freedesktop.org/documentation/tutorials/basic/multithreading-and-pad-availability.html
"""

import sys

import gi

gi.require_version('Gst', '1.0')
from gi.repository import Gst


def main():
    Gst.init(None)

    # Create the elements
    audio_source = Gst.ElementFactory.make("audiotestsrc", "audio_source")
    tee = Gst.ElementFactory.make("tee", "tee")
    audio_queue = Gst.ElementFactory.make("queue", "audio_queue")
    audio_convert = Gst.ElementFactory.make("audioconvert", "audio_convert")
    audio_resample = Gst.ElementFactory.make("audioresample", "audio_resample")
    audio_sink = Gst.ElementFactory.make("autoaudiosink", "audio_sink")
    video_queue = Gst.ElementFactory.make("queue", "video_queue")
    visual = Gst.ElementFactory.make("wavescope", "visual")
    video_convert = Gst.ElementFactory.make("videoconvert", "csp")
    video_sink = Gst.ElementFactory.make("autovideosink", "video_sink")

    # Create the empty pipeline
    pipeline = Gst.Pipeline.new("test-pipeline")

    if (not audio_source or not tee or not audio_queue or not audio_convert or not audio_resample
            or not audio_sink or not video_queue or not visual or not video_convert
            or not video_sink or not pipeline):
        print("Not all elements could be created.", file=sys.stderr)
        exit(-1)

    # Configure elements
    audio_source.set_property("freq", 215.0)
    visual.set_property("shader", 0)
    visual.set_property("style", 1)

    # Link all elements that can be automatically linked because they have "Always" pads

    pipeline.add(audio_source, tee, audio_queue, audio_convert, audio_resample,
                 audio_sink, video_queue, visual, video_convert, video_sink)
    ret = audio_source.link(tee)
    ret = ret and audio_queue.link(audio_convert)
    ret = ret and audio_convert.link(audio_resample)
    ret = ret and audio_resample.link(audio_sink)
    ret = ret and video_queue.link(visual)
    ret = ret and visual.link(video_convert)
    ret = ret and video_convert.link(video_sink)
    if not ret:
        print("Elements could not be linked.", file=sys.stderr)
        exit(-1)

    # Manually link the Tee, which has "Request" pads
    tee_src_pad_template = tee.get_pad_template("src_%u")
    tee_audio_pad = tee.request_pad(tee_src_pad_template, None, None)
    print("Obtained request pad %s for audio branch." % tee_audio_pad.get_name())
    queue_audio_pad = audio_queue.get_static_pad("sink")
    tee_video_pad = tee.request_pad(tee_src_pad_template, None, None)
    print("Obtained request pad %s for video branch." % tee_video_pad.get_name())
    queue_video_pad = video_queue.get_static_pad("sink")
    if (tee_audio_pad.link(queue_audio_pad) != Gst.PadLinkReturn.OK
            or tee_video_pad.link(queue_video_pad) != Gst.PadLinkReturn.OK):
        print("Tee could not be linked.", file=sys.stderr)
        exit(-1)

    # Start playing the pipeline
    ret = pipeline.set_state(Gst.State.PLAYING)
    if ret == Gst.StateChangeReturn.FAILURE:
        print("Unable to set the pipeline to the playing state.", file=sys.stderr)
        exit(-1)

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
