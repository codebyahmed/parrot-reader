import gi
gi.require_version('Gst', '1.0')

from gi.repository import Adw, Gtk, GLib, Gst

Gst.init(None)


@Gtk.Template(resource_path='/dev/ahmediqbal/parrot/tts-player.ui')
class TtsPlayer(Adw.NavigationPage):
    __gtype_name__ = 'TtsPlayer'

    player_text_view = Gtk.Template.Child()
    seek_bar = Gtk.Template.Child()
    play_pause_button = Gtk.Template.Child()
    rewind_button = Gtk.Template.Child()
    forward_button = Gtk.Template.Child()

    _SKIP_NS = 10 * Gst.SECOND

    def __init__(self, text: str, **kwargs):
        super().__init__(**kwargs)
        self._pipeline = None
        self._position_timer = None
        self._seek_updating = False

        self.player_text_view.get_buffer().set_text(text)
        self.play_pause_button.set_sensitive(False)
        self.rewind_button.set_sensitive(False)
        self.forward_button.set_sensitive(False)
        self.play_pause_button.connect('clicked', self._on_play_pause_clicked)
        self.rewind_button.connect('clicked', self._on_rewind_clicked)
        self.forward_button.connect('clicked', self._on_forward_clicked)
        self.seek_bar.connect('value-changed', self._on_seek_changed)
        self.connect('hiding', self._on_hiding)

    def on_synthesis_done(self, path, _error):
        if path:
            self._pipeline = Gst.ElementFactory.make('playbin3', 'player')
            self._pipeline.set_property('uri', Gst.filename_to_uri(path))
            bus = self._pipeline.get_bus()
            bus.add_signal_watch()
            bus.connect('message::eos', self._on_eos)
            bus.connect('message::error', self._on_error)
            self.play_pause_button.set_sensitive(True)
            self.rewind_button.set_sensitive(True)
            self.forward_button.set_sensitive(True)
        return False

    def _skip(self, delta_ns):
        if not self._pipeline:
            return
        ok, pos = self._pipeline.query_position(Gst.Format.TIME)
        ok_dur, dur = self._pipeline.query_duration(Gst.Format.TIME)
        if ok and ok_dur:
            new_pos = max(0, min(pos + delta_ns, dur))
            self._pipeline.seek(
                1.0,
                Gst.Format.TIME,
                Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
                Gst.SeekType.SET,
                new_pos,
                Gst.SeekType.NONE,
                0,
            )

    def _on_rewind_clicked(self, _button):
        self._skip(-self._SKIP_NS)

    def _on_forward_clicked(self, _button):
        self._skip(self._SKIP_NS)

    def _on_play_pause_clicked(self, _button):
        if not self._pipeline:
            return
        _, state, _ = self._pipeline.get_state(0)
        if state == Gst.State.PLAYING:
            self._pipeline.set_state(Gst.State.PAUSED)
            self.play_pause_button.set_icon_name('media-playback-start-symbolic')
            if self._position_timer:
                GLib.source_remove(self._position_timer)
                self._position_timer = None
        else:
            self._pipeline.set_state(Gst.State.PLAYING)
            self.play_pause_button.set_icon_name('media-playback-pause-symbolic')
            self._position_timer = GLib.timeout_add(200, self._update_seek_bar)

    def _update_seek_bar(self):
        if not self._pipeline:
            return False
        ok_pos, pos = self._pipeline.query_position(Gst.Format.TIME)
        ok_dur, dur = self._pipeline.query_duration(Gst.Format.TIME)
        if ok_pos and ok_dur and dur > 0:
            self._seek_updating = True
            self.seek_bar.set_value((pos / dur) * 100)
            self._seek_updating = False
        return True

    def _on_seek_changed(self, scale):
        if self._seek_updating or not self._pipeline:
            return
        _, state, _ = self._pipeline.get_state(0)
        if state not in (Gst.State.PLAYING, Gst.State.PAUSED):
            return
        ok, dur = self._pipeline.query_duration(Gst.Format.TIME)
        if ok:
            pos = int((scale.get_value() / 100) * dur)
            self._pipeline.seek(
                1.0,
                Gst.Format.TIME,
                Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
                Gst.SeekType.SET,
                pos,
                Gst.SeekType.NONE,
                0,
            )

    def _on_eos(self, _bus, _msg):
        self._pipeline.set_state(Gst.State.NULL)
        self.play_pause_button.set_icon_name('media-playback-start-symbolic')
        self._seek_updating = True
        self.seek_bar.set_value(0)
        self._seek_updating = False
        if self._position_timer:
            GLib.source_remove(self._position_timer)
            self._position_timer = None

    def _on_error(self, _bus, msg):
        err, _ = msg.parse_error()
        self._stop()
        print(f'GStreamer error: {err}')

    def _on_hiding(self, _page):
        self._stop()

    def _stop(self):
        if self._position_timer:
            GLib.source_remove(self._position_timer)
            self._position_timer = None
        if self._pipeline:
            self._pipeline.set_state(Gst.State.NULL)
