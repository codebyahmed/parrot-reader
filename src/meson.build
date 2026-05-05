pkgdatadir = get_option('prefix') / get_option('datadir') / meson.project_name()
moduledir = pkgdatadir / 'parrot_reader'
gnome = import('gnome')
blueprints = custom_target('blueprints',
  input: files(
    'loading-page.blp',
    'tts-player.blp',
    'shortcuts-dialog.blp',
    'voice-dialog.blp',
    'window.blp',
  ),
  output: '.',
  command: [find_program('blueprint-compiler'), 'batch-compile', '@OUTPUT@', '@CURRENT_SOURCE_DIR@', '@INPUT@'],
)

gnome.compile_resources('parrot-reader',
  'parrot-reader.gresource.xml',
  gresource_bundle: true,
  install: true,
  install_dir: pkgdatadir,
  dependencies: blueprints,
)

python = import('python')

conf = configuration_data()
conf.set('PYTHON', python.find_installation('python3').full_path())
conf.set('VERSION', meson.project_version())
conf.set('localedir', get_option('prefix') / get_option('localedir'))
conf.set('pkgdatadir', pkgdatadir)

configure_file(
  input: 'parrot-reader.in',
  output: 'parrot-reader',
  configuration: conf,
  install: true,
  install_dir: get_option('bindir'),
  install_mode: 'rwxr-xr-x'
)

configure_file(
  input: '_config.py.in',
  output: '_config.py',
  configuration: conf,
  install: true,
  install_dir: moduledir,
)

parrot_reader_sources = [
  '__init__.py',
  'loading_page.py',
  'main.py',
  'tts_player.py',
  'trim.py',
  'tts.py',
  'voice_dialog.py',
  'window.py',
]

install_data(parrot_reader_sources, install_dir: moduledir)
