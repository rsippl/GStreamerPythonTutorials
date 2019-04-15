#!/usr/bin/env python
"""
Basic tutorial 6: Media formats and Pad Capabilities
https://gstreamer.freedesktop.org/documentation/tutorials/basic/media-formats-and-pad-capabilities.html
"""

import sys

import gi

gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib


# Functions below print the Capabilities in a human-friendly format
def print_field(field, value, pfx):
    str = Gst.value_serialize(value)
    print("{0:s}  {1:15s}: {2:s}".format(
        pfx, GLib.quark_to_string(field), str))
    return True


def print_caps(caps, pfx):
    if caps is None:
        return
    if caps.is_any():
        print("%sANY" % pfx)
        return
    if caps.is_empty():
        print("%sEMPTY" % pfx)
        return
    for i in range(caps.get_size()):
        structure = caps.get_structure(i)
        print("%s%s" % (pfx, structure.get_name()))
        structure.foreach(print_field, pfx)


# Prints information about a Pad Template, including its Capabilities
def print_pad_templates_information(factory):
    print("Pad Templates for %s:" % (factory.get_name()))
    if not factory.get_num_pad_templates():
        print("  none")
        return
  
    padstemplates = factory.get_static_pad_templates()
    for padtemplate in padstemplates:
        if padtemplate.direction == Gst.PadDirection.SRC:
            print("  SRC template: '%s'" % padtemplate.name_template)
        elif padtemplate.direction == Gst.PadDirection.SINK:
            print("  SINK template: '%s'"% padtemplate.name_template)
        else:
            print("  UNKNOWN!!! template: '%s'"% padtemplate.name_template)

        if padtemplate.presence == Gst.PadPresence.ALWAYS:
            print("    Availability: Always")
        elif padtemplate.presence == Gst.PadPresence.SOMETIMES:
            print("    Availability: Sometimes")
        elif padtemplate.presence == Gst.PadPresence.REQUEST:
            print("    Availability: On request")
        else:
            print("    Availability: UNKNOWN!!!")

        if padtemplate.static_caps.string:
            print("    Capabilities:")
            print_caps(padtemplate.get_caps(), "      ") 

        print("")

# Shows the CURRENT capabilities of the requested pad in the given element
def print_pad_capabilities(element, pad_name):

    # Retrieve pad
    pad = element.get_static_pad(pad_name)
    if not pad:
        print("Could not retrieve pad '%s'" % pad_name, file=sys.stderr)
        return
  
    # Retrieve negotiated caps (or acceptable caps if negotiation is not finished yet)
    caps = pad.get_current_caps()
    if not caps:
        caps = pad.get_allowed_caps()

    # Print
    print("Caps for the %s pad:" % pad_name)
    print_caps(caps, "      ")


def main():
    Gst.init(None)

    # Create the element factories
    source_factory = Gst.ElementFactory.find("audiotestsrc")
    sink_factory = Gst.ElementFactory.find("autoaudiosink")
    if not source_factory or not sink_factory:
        print("Not all element factories could be created.", file=sys.stderr)
        exit(-1)

    # Print information about the pad templates of these factories
    print_pad_templates_information(source_factory)
    print_pad_templates_information(sink_factory)

    # Ask the factories to instantiate actual elements
    source = source_factory.create("source")
    sink = sink_factory.create("sink")

    # Create the empty pipeline
    pipeline = Gst.Pipeline.new("test-pipeline")

    if not pipeline or not source or not sink:
        print("Not all elements could be created.", file=sys.stderr)
        exit(-1)

    # Build the pipeline
    pipeline.add(source, sink)
    if not Gst.Element.link(source, sink):
        print("Elements could not be linked.", file=sys.stderr)
        exit(-1)

    # Print initial negotiated caps (in NULL state)
    print("In NULL state:")
    print_pad_capabilities(sink, "sink")

    # Start playing
    ret = pipeline.set_state(Gst.State.PLAYING)
    if ret == Gst.StateChangeReturn.FAILURE:
        print("Unable to set the pipeline to the playing state "
              "(check the bus for error messages).", file=sys.stderr)

    # Wait until error, EOS or State Change
    bus = pipeline.get_bus()
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
                # Print the current capabilities of the sink element
                print_pad_capabilities (sink, "sink")
        else:
            # We should not reach here because we only asked for ERRORs, EOS and STATE_CHANGED
            print("Unexpected message received.", file=sys.stderr)

    # Free resources
    pipeline.set_state(gst.STATE_NULL)

if __name__ == '__main__':
    main()