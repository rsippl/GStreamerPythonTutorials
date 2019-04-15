#!/usr/bin/env python
"""
basic-tutorial-5: GUI toolkit integration
https://Gstreamer.freedesktop.org/documentation/tutorials/basic/toolkit-integration.html
"""

import sys

import gi

gi.require_version('Gst', '1.0')
gi.require_version('Gtk', '3.0')
gi.require_version("GstVideo", "1.0")
from gi.repository import Gst, Gtk, GLib, GstVideo


# Class to contain all our information, so we can pass it around
class CustomData:
    def __init__(self):
        self.playbin = None
        self.slider = None
        self.streams_list = None
        self.slider_update_signal_id = 0
        self.state = Gst.State.NULL
        self.duration = Gst.CLOCK_TIME_NONE


# This function is called when the GUI toolkit creates the physical window that will hold the video.
# At this point we can retrieve its handler (which has a different meaning depending on the windowing system)
# and pass it to GStreamer through the XOverlay interface.
def realize_cb(widget, data):
    window = widget.get_window()
    # TODO this works on Linux only!
    # see https://gitlab.gnome.org/GNOME/pygobject/issues/112
    window_handle = window.get_xid()

    # Pass it to playbin, which implements VideoOverlay and will forward it to the video sink
    data.playbin.set_window_handle(window_handle)


# This function is called when the PLAY button is clicked
def play_cb(button, data):
    data.playbin.set_state(Gst.State.PLAYING)


# This function is called when the PAUSE button is clicked
def pause_cb(button, data):
    data.playbin.set_state(Gst.State.PAUSED)


# This function is called when the STOP button is clicked
def stop_cb(button, data):
    data.playbin.set_state(Gst.State.READY)


# This function is called when the main window is closed
def delete_event_cb(widget, event, data):
    stop_cb(None, data)
    Gtk.main_quit()


# This function is called everytime the video window needs to be redrawn (due to damage/exposure,
# rescaling, etc). GStreamer takes care of this in the PAUSED and PLAYING states, otherwise,
# we simply draw a black rectangle to avoid garbage showing up.
def draw_cb(widget, cr, data):
    if data.state < Gst.State.PAUSED:
        allocation = widget.get_allocation()

        cr.set_source_rgb(0, 0, 0)
        cr.rectangle(0, 0, allocation.width, allocation.height)
        cr.fill()

    return False


# This function is called when the slider changes its position. We perform a seek to the
# new position here.
def slider_cb(range, data):
    value = data.slider.get_value()
    data.playbin.seek_simple(Gst.Format.TIME,
                             Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
                             value * Gst.SECOND)


# This creates all the GTK+ widgets that compose our application, and registers the callbacks
def create_ui(data):
    main_window = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
    main_window.connect("delete-event", delete_event_cb, data)

    video_window = Gtk.DrawingArea()
    video_window.connect("realize", realize_cb, data)
    video_window.connect("draw", draw_cb, data)

    play_button = Gtk.Button(stock=Gtk.STOCK_MEDIA_PLAY);
    play_button.connect("clicked", play_cb, data)

    pause_button = Gtk.Button(stock=Gtk.STOCK_MEDIA_PAUSE)
    pause_button.connect("clicked", pause_cb, data)

    stop_button = Gtk.Button(stock=Gtk.STOCK_MEDIA_STOP)
    stop_button.connect("clicked", stop_cb, data)

    data.slider = Gtk.HScale()
    data.slider.set_draw_value(0)
    data.slider_update_signal_id = data.slider.connect("value-changed", slider_cb, data)

    data.streams_list = Gtk.TextView()
    data.streams_list.set_editable(False)

    controls = Gtk.HBox(homogeneous=False, spacing=0)
    controls.pack_start(play_button, False, False, 2)
    controls.pack_start(pause_button, False, False, 2)
    controls.pack_start(stop_button, False, False, 2)
    controls.pack_start(data.slider, True, True, 2)

    main_hbox = Gtk.HBox(homogeneous=False, spacing=0);
    main_hbox.pack_start(video_window, True, True, 0)
    main_hbox.pack_start(data.streams_list, False, False, 2)

    main_box = Gtk.VBox(homogeneous=False, spacing=0)
    main_box.pack_start(main_hbox, True, True, 0)
    main_box.pack_start(controls, False, False, 0)
    main_window.add(main_box)
    main_window.set_default_size(640, 480)

    main_window.show_all()


# This function is called periodically to refresh the GUI
def refresh_ui(data):
    current = -1

    # We do not want to update anything unless we are in the PAUSED or PLAYING states 
    if data.state < Gst.State.PAUSED:
        return True

    # If we didn't know it yet, query the stream duration
    if data.duration == Gst.CLOCK_TIME_NONE:
        _, data.duration = data.playbin.query_duration(Gst.Format.TIME)
        if not data.duration:
            print("Could not query current duration", file=sys.stderr)
        else:
            # Set the range of the slider to the clip duration, in SECONDS
            data.slider.set_range(0, data.duration / Gst.SECOND)

    _, current = data.playbin.query_position(Gst.Format.TIME)
    if current:
        # Block the "value-changed" signal, so the slider_cb function is not called
        # (which would trigger a seek the user has not requested)
        data.slider.handler_block(data.slider_update_signal_id)
        # Set the position of the slider to the current pipeline position, in SECONDS
        data.slider.set_value(current / Gst.SECOND)
        # Re-enable the signal
        data.slider.handler_unblock(data.slider_update_signal_id)

    return True


# This function is called when new metadata is discovered in the stream
def tags_cb(playbin, stream, data):
    # We are possibly in a GStreamer working thread, so we notify the main
    # thread of this event through a message in the bus */
    playbin.post_message(Gst.Message.new_application(playbin, Gst.Structure("tags-changed")))


# This function is called when an error message is posted on the bus
def error_cb(bus, msg, data):
    # Print error details on the screen
    err, debug_info = msg.parse_error()
    print("Error received from element %s: %s" % (msg.src.get_name(), err), file=sys.stderr)
    print("Debugging information: %s" % debug_info, file=sys.stderr)

    # Set the pipeline to READY (which stops playback)
    data.playbin.set_state(Gst.State.READY)


# This function is called when an End-Of-Stream message is posted on the bus.
# We just set the pipeline to READY (which stops playback) */
def eos_cb(bus, msg, data):
    print("End-Of-Stream reached.")
    data.playbin.set_state(Gst.State.READY)


# This function is called when the pipeline changes states. We use it to
# keep track of the current state.
def state_changed_cb(bus, msg, data):
    old_state, new_state, pending_state = msg.parse_state_changed()
    if msg.src == data.playbin:
        data.state = new_state
        print("State set to %s" % new_state.value_name)
        if old_state == Gst.State.READY and new_state == Gst.State.PAUSED:
            # For extra responsiveness, we refresh the GUI as soon as we reach the PAUSED state
            refresh_ui(data)


# Extract metadata from all the streams and write it to the text widget in the GUI
def analyze_streams(data):
    # Clean current contents of the widget
    text = data.streams_list.get_buffer()
    text.set_text("")

    # Read some properties
    n_video = data.playbin.get_property("n-video")
    n_audio = data.playbin.get_property("n-audio")
    n_text = data.playbin.get_property("n-text")

    for i in range(n_video):
        tags = data.playbin.emit("get-video-tags", i)
        if tags:
            text.insert_at_cursor("video stream %d:\n" % i)
            ret, str = tags.get_string(Gst.TAG_VIDEO_CODEC)
            if ret:
                text.insert_at_cursor("  codec: %s\n" % str or "unknown")

    for i in range(n_audio):
        tags = data.playbin.emit("get-audio-tags", i)
        if tags:
            text.insert_at_cursor("\naudio stream %d:\n" % i)
            ret, str = tags.get_string(Gst.TAG_AUDIO_CODEC)
            if ret:
                text.insert_at_cursor("  codec: %s\n" % str or "unknown")
            ret, str = tags.get_string(Gst.TAG_LANGUAGE_CODE)
            if ret:
                text.insert_at_cursor("  language: %s\n" % str or "unknown")
            ret, str = tags.get_uint(Gst.TAG_BITRATE)
            if ret:
                text.insert_at_cursor("  bitrate: %s\n" % str or "unknown")

    for i in range(n_text):
        tags = data.playbin.emit("get-text-tags", i)
        if tags:
            text.insert_at_cursor("\nsubtitle stream %d:\n" % i)
            ret, str = tags.get_string(Gst.TAG_LANGUAGE_CODE)
            if ret:
                text.insert_at_cursor("  language: %s\n" % str or "unknown")


# This function is called when an "application" message is posted on the bus.
# Here we retrieve the message posted by the tags_cb callback
def application_cb(bus, msg, data):
    if msg.get_structure().get_name() == "tags-changed":
        analyze_streams(data)


def main():
    Gtk.init(None)
    Gst.init(None)

    data = CustomData()

    # Create the elements
    data.playbin = Gst.ElementFactory.make("playbin", "playbin")

    if not data.playbin:
        print("Not all elements could be created.", file=sys.stderr)
        exit(-1)

    # Set the URI to play
    data.playbin.set_property(
        "uri",
        "https://www.freedesktop.org/software/gstreamer-sdk/data/media/sintel_trailer-480p.webm"
    )

    # Connect to interesting signals in playbin
    data.playbin.connect("video-tags-changed", tags_cb, data)
    data.playbin.connect("audio-tags-changed", tags_cb, data)
    data.playbin.connect("text-tags-changed", tags_cb, data)

    # Create the GUI
    create_ui(data)

    # Instruct the bus to emit signals for each received message, and connect to the interesting signals
    bus = data.playbin.get_bus()
    bus.add_signal_watch()
    bus.connect("message::error", error_cb, data)
    bus.connect("message::eos", eos_cb, data)
    bus.connect("message::state-changed", state_changed_cb, data)
    bus.connect("message::application", application_cb, data)

    # Start playing
    ret = data.playbin.set_state(Gst.State.PLAYING)
    if ret == Gst.StateChangeReturn.FAILURE:
        print("Unable to set the pipeline to the playing state.", file=sys.stderr)
        exit(-1)

    # Register a function that GLib will call every second
    GLib.timeout_add_seconds(1, refresh_ui, data)

    # Start the GTK main loop. We will not regain control until Gtk_main_quit is called.
    Gtk.main()

    # Free resources
    data.playbin.set_state(Gst.State.NULL)


if __name__ == '__main__':
    main()
