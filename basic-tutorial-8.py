#!/usr/bin/env python
"""
Basic tutorial 8: Short-cutting the pipeline
https://gstreamer.freedesktop.org/documentation/tutorials/basic/short-cutting-the-pipeline.html
"""

import sys
from array import array

import gi

gi.require_version('Gst', '1.0')
gi.require_version('GLib', '2.0')
gi.require_version('GstAudio', '1.0')
from gi.repository import Gst, GLib, GstAudio

CHUNK_SIZE = 1024  # Amount of bytes we are sending in each buffer
SAMPLE_RATE = 44100  # Samples per second we are sending


# Structure to contain all our information, so we can pass it to callbacks
class CustomData:
    def __init__(self):
        self.pipeline = None
        self.app_source = None
        self.tee = None
        self.audio_queue = None
        self.audio_convert1 = None
        self.audio_resample = None
        self.audio_sink = None
        self.video_queue = None
        self.audio_convert2 = None
        self.visual = None
        self.video_convert = None
        self.video_sink = None
        self.app_queue = None
        self.app_sink = None
        self.num_samples = 0
        self.a = 0
        self.b = 1
        self.c = 0
        self.d = 1
        self.sourceid = 0
        self.main_loop = None


# This method is called by the idle GSource in the mainloop, to feed CHUNK_SIZE bytes into appsrc.
# The idle handler is added to the mainloop when appsrc requests us to start sending data (need-data signal)
# and is removed when appsrc has enough data (enough-data signal)
def push_data(data):
    num_samples = round(CHUNK_SIZE / 2)  # Because each sample is 16 bits

    # Generate some psychodelic waveforms
    data.c += data.d
    data.d -= data.c / 1000
    freq = 1100 + 1000 * data.d

    raw = array('H')
    for i in range(num_samples):
        data.a += data.b
        data.b -= data.a / freq
        a5 = (int(500 * data.a)) % 65535
        raw.append(a5)
    b_data = raw.tostring()

    data.num_samples += num_samples
    buffer = Gst.Buffer.new_wrapped(b_data)

    # Set its timestamp and duration
    buffer.timestamp = Gst.util_uint64_scale(data.num_samples, Gst.SECOND, SAMPLE_RATE)
    buffer.duration = Gst.util_uint64_scale(CHUNK_SIZE, Gst.SECOND, SAMPLE_RATE)

    # Push the buffer into the appsrc
    ret = data.app_source.emit("push-buffer", buffer)
    if ret != Gst.FlowReturn.OK:
        return False
    return True


# This signal callback triggers when appsrc needs data. Here, we add an idle handler
# to the mainloop to start pushing data into the appsrc
def start_feed(source, size, data):
    if data.sourceid == 0:
        print("\nStart feeding")
        data.sourceid = GLib.idle_add(push_data, data)


# This callback triggers when appsrc has enough data and we can stop sending.
# We remove the idle handler from the mainloop
def stop_feed(source, data):
    if data.sourceid != 0:
        print("\nStop feeding")
        GLib.source_remove(data.sourceid)
        data.sourceid = 0


# The appsink has received a buffer
def new_sample(sink, data):
    # Retrieve the buffer
    sample = sink.emit("pull-sample")
    if sample:
        # The only thing we do in this example is print a * to indicate a received buffer
        sys.stdout.write('*')
        sys.stdout.flush()
        return Gst.FlowReturn.OK
    return Gst.FlowReturn.ERROR


# This function is called when an error message is posted on the bus
def error_cb(bus, msg, data):
    err, debug_info = msg.parse_error()
    print("Error received from element %s: %s" % (msg.src.get_name(), err), file=sys.stderr)
    print("Debugging information: %s" % debug_info, file=sys.stderr)
    data.main_loop.quit()


def main():
    Gst.init(None)

    data = CustomData()

    # Create the elements
    data.app_source = Gst.ElementFactory.make("appsrc", "app_source")
    data.tee = Gst.ElementFactory.make("tee", "tee")
    data.audio_queue = Gst.ElementFactory.make("queue", "audio_queue")
    data.audio_convert1 = Gst.ElementFactory.make("audioconvert", "audio_convert1")
    data.audio_resample = Gst.ElementFactory.make("audioresample", "audio_resample")
    data.audio_sink = Gst.ElementFactory.make("autoaudiosink", "audio_sink")
    data.video_queue = Gst.ElementFactory.make("queue", "video_queue")
    data.audio_convert2 = Gst.ElementFactory.make("audioconvert", "audio_convert2")
    data.visual = Gst.ElementFactory.make("wavescope", "visual")
    data.video_convert = Gst.ElementFactory.make("videoconvert", "video_convert")
    data.video_sink = Gst.ElementFactory.make("autovideosink", "video_sink")
    data.app_queue = Gst.ElementFactory.make("queue", "app_queue")
    data.app_sink = Gst.ElementFactory.make("appsink", "app_sink")

    data.pipeline = Gst.Pipeline.new("test-pipeline")

    if (not data.app_source or not data.tee or not data.audio_queue
            or not data.audio_convert1 or not data.audio_resample
            or not data.audio_sink or not data.video_queue
            or not data.audio_convert2 or not data.visual
            or not data.video_convert or not data.video_sink
            or not data.app_queue or not data.app_sink
            or not data.pipeline):
        print("Not all elements could be created.", file=sys.stderr)
        exit(-1)

    # Configure wavescope
    data.visual.set_property("shader", 0)
    data.visual.set_property("style", 0)

    # Configure appsrc
    info = GstAudio.AudioInfo.new()
    info.set_format(GstAudio.AudioFormat.S16, SAMPLE_RATE, 1, None)
    audio_caps = info.to_caps()
    data.app_source.set_property("caps", audio_caps)
    data.app_source.set_property("format", Gst.Format.TIME)
    data.app_source.connect("need-data", start_feed, data)
    data.app_source.connect("enough-data", stop_feed, data)

    # Configure appsink
    data.app_sink.set_property("emit-signals", True)
    data.app_sink.set_property("caps", audio_caps)
    data.app_sink.connect("new-sample", new_sample, data)

    # Link all elements that can be automatically linked because they have "Always" pads
    data.pipeline.add(data.app_source, data.tee,
                      data.audio_queue, data.audio_convert1, data.audio_resample, data.audio_sink,
                      data.video_queue, data.audio_convert2, data.visual, data.video_convert, data.video_sink,
                      data.app_queue, data.app_sink)
    if (not data.app_source.link(data.tee)
            or not data.audio_queue.link(data.audio_convert1)
            or not data.audio_convert1.link(data.audio_resample)
            or not data.audio_resample.link(data.audio_sink)
            or not data.video_queue.link(data.audio_convert2)
            or not data.audio_convert2.link(data.visual)
            or not data.visual.link(data.video_convert)
            or not data.video_convert.link(data.video_sink)
            or not data.app_queue.link(data.app_sink)):
        print("Elements could not be linked.", file=sys.stderr)
        exit(-1)

    # Manually link the Tee, which has "Request" pads
    tee_src_pad_template = data.tee.get_pad_template("src_%u")
    tee_audio_pad = data.tee.request_pad(tee_src_pad_template, None, None)
    print("Obtained request pad {0} for audio branch".format(tee_audio_pad.get_name()))
    queue_audio_pad = data.audio_queue.get_static_pad("sink")
    tee_video_pad = data.tee.request_pad(tee_src_pad_template, None, None)
    print("Obtained request pad {0} for video branch".format(tee_video_pad.get_name()))
    queue_video_pad = data.video_queue.get_static_pad("sink")
    tee_app_pad = data.tee.request_pad(tee_src_pad_template, None, None)
    print("Obtained request pad {0} for app branch".format(tee_app_pad.get_name()))
    queue_app_pad = data.app_queue.get_static_pad("sink")

    if (tee_audio_pad.link(queue_audio_pad) != Gst.PadLinkReturn.OK
            or tee_video_pad.link(queue_video_pad) != Gst.PadLinkReturn.OK
            or tee_app_pad.link(queue_app_pad) != Gst.PadLinkReturn.OK):
        print("Tee could not be linked.", file=sys.stderr)
        exit(-1)

    # Instruct the bus to emit signals for each received message, and connect to the interesting signals
    bus = data.pipeline.get_bus()
    bus.add_signal_watch()
    bus.connect("message::error", error_cb, data)

    # Start playing the pipeline
    ret = data.pipeline.set_state(Gst.State.PLAYING)

    # Create a GLib Mainloop and set it to run
    data.main_loop = GLib.MainLoop.new(None, False)
    data.main_loop.run()

    # Free resources
    data.pipeline.set_state(Gst.State.NULL)


if __name__ == '__main__':
    main()
