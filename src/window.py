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

from gi.repository import Adw, Gtk
from .voice_dialog import VoiceDialog, get_voice_name


@Gtk.Template(resource_path='/dev/ahmediqbal/parrot/window.ui')
class ParrotReaderWindow(Adw.ApplicationWindow):
    __gtype_name__ = 'ParrotReaderWindow'

    text_view = Gtk.Template.Child()
    voice_selector_button = Gtk.Template.Child()
    voice_selector_content = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_voice_id = 'bf_emma'
        self.voice_selector_content.set_label(get_voice_name(self.current_voice_id))
        self.voice_selector_button.connect('clicked', self._on_voice_button_clicked)

    def _on_voice_button_clicked(self, _button):
        dialog = VoiceDialog(current_voice_id=self.current_voice_id)
        dialog.connect('voice-confirmed', self._on_voice_confirmed)
        dialog.present(self)

    def _on_voice_confirmed(self, _dialog, voice_id):
        self.current_voice_id = voice_id
        self.voice_selector_content.set_label(get_voice_name(voice_id))