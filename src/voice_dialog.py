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


def get_voice_name(voice_id):
    return voice_id.split('_', 1)[1].capitalize()

def get_voice_language(voice_id):
    return _LANG.get(voice_id[0], "Unknown")

def get_voice_gender(voice_id):
    return _GENDER.get(voice_id[1], "Unknown")
