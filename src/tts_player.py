import gi
import shutil
import threading
import re
gi.require_version('Gst', '1.0')

from gi.repository import Adw, Gtk, GLib, Gst
from .voice_dialog import get_voice_name, get_voice_language

Gst.init(None)


@Gtk.Template(resource_path='/dev/ahmediqbal/parrot/tts-player.ui')
class TtsPlayer(Adw.NavigationPage):
    __gtype_name__ = 'TtsPlayer'

    player_text_view = Gtk.Template.Child()
    seek_bar = Gtk.Template.Child()
    position_label = Gtk.Template.Child()
    duration_label = Gtk.Template.Child()
    play_pause_button = Gtk.Template.Child()
    rewind_button = Gtk.Template.Child()
    forward_button = Gtk.Template.Child()
    speed_button = Gtk.Template.Child()
    volume_button = Gtk.Template.Child()
    volume_scale = Gtk.Template.Child()
    export_button = Gtk.Template.Child()
    window_title = Gtk.Template.Child()

    _SKIP_NS = 10 * Gst.SECOND
    _SPEEDS = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]

    def __init__(self, text: str, voice_id: str, **kwargs):
        super().__init__(**kwargs)
        title = self._title_from_text(text)
        self.window_title.set_title(title)
        self.window_title.set_subtitle(f'{get_voice_name(voice_id)} • {get_voice_language(voice_id)}')
        self._pipeline = None
        self._audio_path = None
        self._position_timer = None
        self._seek_updating = False
        self._speed_idx = 2  # default 1.0×

        self.player_text_view.get_buffer().set_text(text)
        self.play_pause_button.set_sensitive(False)
        self.rewind_button.set_sensitive(False)
        self.forward_button.set_sensitive(False)
        self.speed_button.set_sensitive(False)
        self.volume_button.set_sensitive(False)
        self.export_button.connect('clicked', self._on_export_clicked)
        self.play_pause_button.connect('clicked', self._on_play_pause_clicked)
        self.rewind_button.connect('clicked', self._on_rewind_clicked)
        self.forward_button.connect('clicked', self._on_forward_clicked)
        self.speed_button.connect('clicked', self._on_speed_clicked)
        self.volume_scale.connect('value-changed', self._on_volume_changed)
        self.seek_bar.connect('value-changed', self._on_seek_changed)
        self.connect('hiding', self._on_hiding)

    @staticmethod
    def _title_from_text(text: str) -> str:
        words = text.split()[:5]
        cleaned = (re.sub(r'[^\w]', '', w) for w in words if w)
        slug = ' '.join(w for w in cleaned if w)
        return (slug[:48] or 'Speech').capitalize()

    @staticmethod
    def _fmt(ns):
        s = ns // Gst.SECOND
        return f'{s // 60}:{s % 60:02d}'

    def on_synthesis_done(self, path, _error):
        if path:
            self._audio_path = path
            self._pipeline = Gst.ElementFactory.make('playbin3', 'player')
            self._pipeline.set_property('uri', Gst.filename_to_uri(path))
            scaletempo = Gst.ElementFactory.make('scaletempo', None)
            if scaletempo:
                self._pipeline.set_property('audio-filter', scaletempo)
            bus = self._pipeline.get_bus()
            bus.add_signal_watch()
            bus.connect('message::eos', self._on_eos)
            bus.connect('message::error', self._on_error)
            bus.connect('message::async-done', self._on_async_done)
            self._pipeline.set_state(Gst.State.PAUSED)
            self.play_pause_button.set_sensitive(True)
            self.play_pause_button.set_tooltip_text('Play')
            self.rewind_button.set_sensitive(True)
            self.forward_button.set_sensitive(True)
            self.speed_button.set_sensitive(True)
            self.volume_button.set_sensitive(True)
            self.export_button.set_sensitive(True)
            self._pipeline.set_property('volume', self.volume_scale.get_value())
        return False

    def _on_async_done(self, _bus, _msg):
        ok, dur = self._pipeline.query_duration(Gst.Format.TIME)
        if ok and dur > 0:
            self.duration_label.set_label(self._fmt(dur))

    def _skip(self, delta_ns):
        if not self._pipeline:
            return
        ok, pos = self._pipeline.query_position(Gst.Format.TIME)
        ok_dur, dur = self._pipeline.query_duration(Gst.Format.TIME)
        if ok and ok_dur:
            new_pos = max(0, min(pos + delta_ns, dur))
            self._pipeline.seek(
                self._SPEEDS[self._speed_idx],
                Gst.Format.TIME,
                Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
                Gst.SeekType.SET,
                new_pos,
                Gst.SeekType.NONE,
                0,
            )
            self._seek_updating = True
            self.seek_bar.set_value((new_pos / dur) * 100)
            self._seek_updating = False
            self.position_label.set_label(self._fmt(new_pos))

    def _on_rewind_clicked(self, _button):
        self._skip(-self._SKIP_NS)

    def _on_forward_clicked(self, _button):
        self._skip(self._SKIP_NS)

    def _on_speed_clicked(self, _button):
        self._speed_idx = (self._speed_idx + 1) % len(self._SPEEDS)
        rate = self._SPEEDS[self._speed_idx]
        self.speed_button.set_label(f'{rate:g}×')
        if not self._pipeline:
            return
        ok, pos = self._pipeline.query_position(Gst.Format.TIME)
        if not ok:
            pos = 0
        _, state, _ = self._pipeline.get_state(0)
        if state in (Gst.State.PLAYING, Gst.State.PAUSED):
            self._pipeline.seek(
                rate,
                Gst.Format.TIME,
                Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
                Gst.SeekType.SET,
                pos,
                Gst.SeekType.NONE,
                0,
            )

    def _on_export_clicked(self, _button):
        dialog = Gtk.FileDialog()
        dialog.set_title('Export Speech')
        dialog.set_initial_name(self.window_title.get_title() + '.wav')
        dialog.save(self.get_root(), None, self._on_export_response)

    def _on_export_response(self, dialog, result):
        try:
            file = dialog.save_finish(result)
        except GLib.Error:
            return
        dest = file.get_path()
        if not dest:
            return
        threading.Thread(
            target=shutil.copy2,
            args=(self._audio_path, dest),
            daemon=True,
        ).start()

    def _on_volume_changed(self, scale):
        value = scale.get_value()
        if value == 0:
            icon = 'speaker-0-symbolic'
        elif value < 0.34:
            icon = 'speaker-1-symbolic'
        elif value < 0.67:
            icon = 'speaker-2-symbolic'
        else:
            icon = 'speaker-3-symbolic'
        self.volume_button.set_icon_name(icon)
        if self._pipeline:
            self._pipeline.set_property('volume', value)

    def _on_play_pause_clicked(self, _button):
        if not self._pipeline:
            return
        _, state, _ = self._pipeline.get_state(0)
        if state == Gst.State.PLAYING:
            self._pipeline.set_state(Gst.State.PAUSED)
            self.play_pause_button.set_icon_name('play-symbolic')
            self.play_pause_button.set_tooltip_text('Play')
            if self._position_timer:
                GLib.source_remove(self._position_timer)
                self._position_timer = None
        else:
            self._pipeline.set_state(Gst.State.PLAYING)
            self.play_pause_button.set_icon_name('pause-symbolic')
            self.play_pause_button.set_tooltip_text('Pause')
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
            self.position_label.set_label(self._fmt(pos))
            self.duration_label.set_label(self._fmt(dur))
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
            self.position_label.set_label(self._fmt(pos))
            self._pipeline.seek(
                self._SPEEDS[self._speed_idx],
                Gst.Format.TIME,
                Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
                Gst.SeekType.SET,
                pos,
                Gst.SeekType.NONE,
                0,
            )

    def _on_eos(self, _bus, _msg):
        if self._position_timer:
            GLib.source_remove(self._position_timer)
            self._position_timer = None
        self._pipeline.seek(
            1.0,
            Gst.Format.TIME,
            Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
            Gst.SeekType.SET,
            0,
            Gst.SeekType.NONE,
            0,
        )
        self._pipeline.set_state(Gst.State.PAUSED)
        self.play_pause_button.set_icon_name('play-symbolic')
        self.play_pause_button.set_tooltip_text('Play')
        self._seek_updating = True
        self.seek_bar.set_value(0)
        self._seek_updating = False
        self.position_label.set_label('0:00')

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
            bus = self._pipeline.get_bus()
            bus.remove_signal_watch()
            self._pipeline.set_state(Gst.State.NULL)
            self._pipeline = None
