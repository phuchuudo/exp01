import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib

Gst.init(None)

# Tạo pipeline GStreamer
pipeline = Gst.parse_launch("rtspsrc location=rtsp://localhost:8554/test ! decodebin ! autovideosink")

# Khởi động pipeline
pipeline.set_state(Gst.State.PLAYING)

# Giữ chương trình chạy
loop = GLib.MainLoop()
loop.run()
