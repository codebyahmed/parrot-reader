from gi.repository import Adw, Gtk


@Gtk.Template(resource_path='/dev/ahmediqbal/parrot/tts-player.ui')
class TtsPlayer(Adw.NavigationPage):
    __gtype_name__ = 'TtsPlayer'

    player_text_view = Gtk.Template.Child()
    seek_bar = Gtk.Template.Child()
    play_pause_button = Gtk.Template.Child()

    def __init__(self, text: str, **kwargs):
        super().__init__(**kwargs)
        self.audio_path = None
        self.player_text_view.get_buffer().set_text(text)
        self.play_pause_button.set_sensitive(False)

    def on_synthesis_done(self, path, _error):
        if path:
            self.audio_path = path
            self.play_pause_button.set_sensitive(True)
        return False