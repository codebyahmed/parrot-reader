from gi.repository import Adw, Gtk, GObject

VOICE_IDS = [
    "af_alloy", "af_aoede", "af_bella", "af_heart", "af_jessica",
    "af_kore", "af_nicole", "af_nova", "af_river", "af_sarah", "af_sky",
    "am_adam", "am_echo", "am_eric", "am_fenrir", "am_liam",
    "am_michael", "am_onyx", "am_puck", "am_santa", "bf_alice", 
    "bf_emma", "bf_isabella", "bf_lily", "bm_daniel", "bm_fable", 
    "bm_george", "bm_lewis", "ef_dora", "em_alex", "em_santa",
    "ff_siwis", "hf_alpha", "hf_beta", "hm_omega", "hm_psi",
    "if_sara", "im_nicola", "jf_alpha", "jf_gongitsune", "jf_nezumi", 
    "jf_tebukuro", "jm_kumo", "pf_dora", "pm_alex", "pm_santa",
    "zf_xiaobei", "zf_xiaoni", "zf_xiaoxiao", "zm_yunjian",
]

_LANG = {
    'a': "American English",
    'b': "British English",
    'e': "Spanish",
    'f': "French",
    'h': "Hindi",
    'i': "Italian",
    'j': "Japanese",
    'p': "Brazilian Portuguese",
    'z': "Mandarin Chinese",
}

_GENDER = {'f': "Female", 'm': "Male"}

LANGUAGES = sorted(_LANG.values())


def get_voice_name(voice_id):
    return voice_id.split('_', 1)[1].capitalize()

def get_voice_language(voice_id):
    return _LANG.get(voice_id[0], "Unknown")

def get_voice_gender(voice_id):
    return _GENDER.get(voice_id[1], "Unknown")


@Gtk.Template(resource_path='/dev/ahmediqbal/parrot/voice-dialog.ui')
class VoiceDialog(Adw.Dialog):
    __gtype_name__ = 'VoiceDialog'

    __gsignals__ = {
        'voice-confirmed': (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    }

    voice_list = Gtk.Template.Child()
    confirm_voice_button = Gtk.Template.Child()
    language_dropdown = Gtk.Template.Child()

    def __init__(self, current_voice_id, **kwargs):
        super().__init__(**kwargs)
        self.selected_voice_id = current_voice_id if current_voice_id in VOICE_IDS else VOICE_IDS[0]

        self.language_dropdown.set_model(Gtk.StringList.new(LANGUAGES))
        initial_lang = get_voice_language(self.selected_voice_id)
        self.language_dropdown.set_selected(LANGUAGES.index(initial_lang) if initial_lang in LANGUAGES else 0)

        self._populate_voices()
        self.voice_list.set_filter_func(self._filter_row)

        self.language_dropdown.connect('notify::selected', self._on_language_changed)
        self.voice_list.connect('row-selected', self._on_row_selected)
        self.confirm_voice_button.connect('clicked', self._on_confirm)

    def _populate_voices(self):
        for vid in VOICE_IDS:
            row = Adw.ActionRow(title=get_voice_name(vid), subtitle=get_voice_gender(vid))
            row._voice_id = vid
            self.voice_list.append(row)

            if vid == self.selected_voice_id:
                self.voice_list.select_row(row)

    def _filter_row(self, row):
        selected = self.language_dropdown.get_selected()
        return get_voice_language(row._voice_id) == LANGUAGES[selected]

    def _on_language_changed(self, *_):
        self.voice_list.invalidate_filter()

    def _on_row_selected(self, _list_box, row):
        if row:
            self.selected_voice_id = row._voice_id

    def _on_confirm(self, _button):
        self.emit('voice-confirmed', self.selected_voice_id)
        self.close()