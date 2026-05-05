from gi.repository import Adw, Gtk


@Gtk.Template(resource_path='/dev/ahmediqbal/parrot/loading-page.ui')
class LoadingPage(Adw.NavigationPage):
    __gtype_name__ = 'LoadingPage'

    progress_bar = Gtk.Template.Child()

    def set_progress(self, fraction: float):
        self.progress_bar.set_fraction(fraction)
        return False
