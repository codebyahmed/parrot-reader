from gi.repository import Adw, Gtk


@Gtk.Template(resource_path='/dev/ahmediqbal/parrot/loading-page.ui')
class LoadingPage(Adw.NavigationPage):
    __gtype_name__ = 'LoadingPage'
