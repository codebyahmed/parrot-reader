# window.py
#
# Copyright 2026 Ahmed
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import threading

from gi.repository import Adw, Gtk, Gio, GLib
from .voice_dialog import VoiceDialog, get_voice_name, get_voice_language
from .tts_player import TtsPlayer
from .loading_page import LoadingPage
from .tts import synthesize, title_from_text


@Gtk.Template(resource_path='/dev/ahmediqbal/parrot/window.ui')
class ParrotReaderWindow(Adw.ApplicationWindow):
    __gtype_name__ = 'ParrotReaderWindow'

    text_view = Gtk.Template.Child()
    voice_selector_button = Gtk.Template.Child()
    voice_selector_content = Gtk.Template.Child()
    start_listening_button = Gtk.Template.Child()
    toast_overlay = Gtk.Template.Child()
    navigation_view = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.settings = Gio.Settings(schema_id='dev.ahmediqbal.parrot')
        self.current_voice_id = self.settings.get_string('voice-id')
        self.voice_selector_content.set_label(get_voice_name(self.current_voice_id))
        self.voice_selector_button.connect('clicked', self._on_voice_button_clicked)
        self.text_view.get_buffer().connect('changed', self._on_text_changed)
        self.start_listening_button.set_sensitive(False)
        self.start_listening_button.connect('clicked', self._on_start_listening_clicked)

    def _on_text_changed(self, buffer):
        self.start_listening_button.set_sensitive(buffer.get_char_count() > 0)

    def _on_voice_button_clicked(self, _button):
        dialog = VoiceDialog(current_voice_id=self.current_voice_id)
        dialog.connect('voice-confirmed', self._on_voice_confirmed)
        dialog.present(self)

    def _on_voice_confirmed(self, _dialog, voice_id):
        self.current_voice_id = voice_id
        self.settings.set_string('voice-id', voice_id)
        self.voice_selector_content.set_label(get_voice_name(voice_id))

    def _on_start_listening_clicked(self, _button):
        buffer = self.text_view.get_buffer()
        start, end = buffer.get_bounds()
        text = buffer.get_text(start, end, False)
        if not text.strip():
            return

        out_dir = os.path.join(GLib.get_user_cache_dir(), 'parrot-reader')
        out_path = os.path.join(out_dir, 'current.wav')

        voice_info = f'{get_voice_name(self.current_voice_id)} • {get_voice_language(self.current_voice_id)}'
        loading_page = LoadingPage(
            audio_title=title_from_text(text),
            voice_info=voice_info,
        )
        self.navigation_view.push(loading_page)

        def on_progress(fraction):
            GLib.idle_add(loading_page.set_progress, fraction)

        threading.Thread(
            target=self._run_synthesis,
            args=(text, self.current_voice_id, out_path, on_progress),
            daemon=True,
        ).start()

    def _run_synthesis(self, text, voice_id, out_path, on_progress):
        try:
            path = synthesize(text, voice_id, out_path, on_progress)
            GLib.idle_add(self._on_synthesis_ready, text, voice_id, path, None)
        except Exception as exc:
            GLib.idle_add(self._on_synthesis_ready, text, voice_id, None, str(exc))

    def _on_synthesis_ready(self, text, voice_id, path, error):
        tts_player = TtsPlayer(text=text, voice_id=voice_id)
        tts_player.on_synthesis_done(path, error)
        loading_page = self.navigation_view.get_visible_page()
        self.navigation_view.push(tts_player)
        loading_page.connect('hidden', self._on_loading_hidden, tts_player)
        return False

    def _on_loading_hidden(self, _loading_page, tts_player):
        home = self.navigation_view.find_page('home')
        self.navigation_view.replace([home, tts_player])