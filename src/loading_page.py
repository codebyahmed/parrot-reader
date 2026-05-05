from gi.repository import Adw, Gtk


@Gtk.Template(resource_path='/dev/ahmediqbal/parrot/loading-page.ui')
class LoadingPage(Adw.NavigationPage):
    __gtype_name__ = 'LoadingPage'

    progress_bar = Gtk.Template.Child()
    audio_title_label = Gtk.Template.Child()
    voice_label = Gtk.Template.Child()

    def __init__(self, audio_title: str = '', voice_info: str = '', **kwargs):
        super().__init__(**kwargs)
        self.audio_title_label.set_label(audio_title)
        self.voice_label.set_label(voice_info)

    def set_progress(self, fraction: float):
        self.progress_bar.set_fraction(fraction)
        return False
