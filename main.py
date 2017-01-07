#!/usr/bin/python
'''
MasterGrid
Copyright (c) 2016 Robert Oscilowski

Multitouch MIDI keyboard using Kivy.

MasterGrid is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

MasterGrid is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with MasterGrid. If not, see <http://www.gnu.org/licenses/>
'''

import os
import kivy
from kivy.app import App
from kivy.core.window import Window
from kivy.event import EventDispatcher
from kivy.uix.widget import Widget
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.settings import SettingItem
from kivy.uix.slider import Slider
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.properties import ObjectProperty, NumericProperty, StringProperty
from kivy.utils import platform
if platform == 'android':
    from fluidsynth import fluidsynth
else:
    import pygame.midi
from functools import partial

class FluidMIDI(EventDispatcher):
    app = ObjectProperty(None)
    midi = ObjectProperty(None)

    def change_instrument(self, channel, instrument):
        self.midi.program_change(channel, instrument)

    def note_on(self, note, velocity, channel):
        self.midi.noteon(channel, note, velocity)

    def note_off(self, note, channel):
        self.midi.noteoff(channel, note)

    def mod_wheel(self, channel, value):
        self.midi.cc(channel, 1, value)

    def pitch_bend(self, channel, value):
        self.midi.pitch_bend(channel, value)

    def set_pitchbend_range(self, value):
        for channel in range(16):
            self.midi.pitch_wheel_sens(channel, value)

    def aftertouch(self, channel, note, value):
        self.midi.key_pressure(channel, note, value)

    def reverb(self, channel, value):
        self.midi.cc(channel, 91, value)

    def set_reverb(self, value):
        if self.app.pitchbend_enabled():
            for channel in range(16):
                self.reverb(channel, value)
        else:
            self.reverb(self.app.config.getint('MIDI', 'Channel'), value)

    def reset(self, channel):
        self.midi.cc(channel, 123, 0)

    def panic(self, value):
        for channel in range(16):
            self.reset_channel(channel)

class PyGameMIDI(EventDispatcher):
    app = ObjectProperty(None)
    midi = ObjectProperty(None)

    def change_instrument(self, channel, instrument):
        self.midi.set_instrument(instrument, channel=channel)

    def note_on(self, note, velocity, channel):
        self.midi.note_on(note, int(velocity), channel)

    def note_off(self, note, channel):
        self.midi.note_off(note, 0, channel)

    def mod_wheel(self, channel, value):
        self.midi.write_short(0xB0 + channel, 1, value)

    def pitch_bend(self, channel, value):
        self.midi.write_short(0xE0 + channel, value - int(value / 128) * 128, int(value / 128))

    def set_pitchbend_range(self, value):
        for channel in range(16):
            self.midi.write_short(0xB0 + channel, 100, 0)
            self.midi.write_short(0xB0 + channel, 101, 0)
            self.midi.write_short(0xB0 + channel, 6, self.app.config.getint('MIDI', 'PitchbendRange'))

    def aftertouch(self, channel, note, pressure):
        self.midi.write_short(0xA0 + channel, note, int(pressure))

    def reverb(self, channel, value):
        self.midi.write_short(0xB0 + channel, 91, value)

    def set_reverb(self, value):
        if self.app.pitchbend_enabled():
            for channel in range(16):
                self.reverb(channel, value)
        else:
            self.reverb(self.app.config.getint('MIDI', 'Channel'), value)

    def reset(self, channel):
        self.midi.write_short(0xB0 + channel, 123, 0)

    def panic(self, value):
        for channel in range(16):
            self.reset(channel)

class Sizer(BoxLayout):
    app = ObjectProperty(None)
    label = StringProperty()
    low = NumericProperty()
    high = NumericProperty()
    inputbox = ObjectProperty(None)

    def __init__(self, **kwargs):
        super(Sizer, self).__init__(**kwargs)
        label = Label(text=self.label)
        self.add_widget(label)
        controls = BoxLayout()
        minus = Button(text='-')
        minus.bind(on_press=self.minus)
        controls.add_widget(minus)
        self.inputbox = TextInput(text=self.get(), multiline=False, input_filter='int', input_type='number')
        self.inputbox.bind(on_text_validate=self.set)
        controls.add_widget(self.inputbox)
        plus = Button(text='+')
        plus.bind(on_press=self.plus)
        controls.add_widget(plus)
        self.add_widget(controls)

    def get(self):
        return self.app.config.get('MIDI', self.label)

    def set(self, instance):
        self.app.config.set('MIDI', self.label, instance)
        self.app.config.write()
        self.inputbox.text = str(instance)
        self.app.resize_grid()

    def plus(self, value):
        value = self.app.config.getint('MIDI', self.label)
        if self.low < value < self.high:
            self.set(value + 1)

    def minus(self, value):
        value = self.app.config.getint('MIDI', self.label)
        if self.low < value < self.high:
            self.set(value - 1)

class ControlBar(BoxLayout):
    app = ObjectProperty(None)
    device = ObjectProperty(None)

    def __init__(self, **kwargs):
        super(ControlBar, self).__init__(**kwargs)
        logo = Label(text="MasterGrid")
        self.add_widget(logo)
        menu = Button(text="Settings")
        menu.bind(on_press=self.app.open_settings)
        self.add_widget(menu)
        pitchbend = ToggleButton(text="Pitch Bend", state=self.get('Pitchbend'))
        pitchbend.bind(on_release=partial(self.set, 'Pitchbend'), on_state=partial(self.get, 'Pitchbend'))
        self.add_widget(pitchbend)
        aftertouch = ToggleButton(text="Aftertouch", state=self.get('Aftertouch'))
        aftertouch.bind(on_release=partial(self.set, 'Aftertouch'), on_state=partial(self.get, 'Aftertouch'))
        self.add_widget(aftertouch)
        rows = Sizer(label='Rows', app=self.app, orientation='vertical', low=8, high=36)
        self.add_widget(rows)
        keys = Sizer(label='Keys', app=self.app, orientation='vertical', low=8, high=36)
        self.add_widget(keys)
        if platform == 'android':
            instrument = Button(text="Instruments")
            instrument.bind(on_press=self.instrument_list)
        else:
            instrument = BoxLayout(orientation='vertical')
            prog_label = Label(text="Instrument")
            prog_input = TextInput(on_text_validate=self.set_instrument, multiline=False, input_filter='int', input_type='number')
            instrument.add_widget(prog_label)
            instrument.add_widget(prog_input)
        self.add_widget(instrument)
        modwheel = BoxLayout(orientation='vertical')
        modwheel_label = Label(text="Modulation")
        modwheel_slider = Slider(min=0, max=127)
        modwheel_slider.bind(on_value=self.mod_wheel)
        modwheel.add_widget(modwheel_label)
        modwheel.add_widget(modwheel_slider)
        self.add_widget(modwheel)
        reverb = BoxLayout(orientation='vertical')
        reverb_label = Label(text="Reverb")
        reverb_slider = Slider(min=0, max=127)
        reverb_slider.bind(on_value=self.set_reverb)
        reverb.add_widget(reverb_label)
        reverb.add_widget(reverb_slider)
        self.add_widget(reverb)
        panic = Button(text="Panic")
        panic.bind(on_press=self.device.panic)
        self.add_widget(panic)

    def get(self, label):
        enabled = self.app.config.getboolean('MIDI', label)
        return 'down' if enabled else 'normal'

    def set(self, label, value):
        enabled = self.app.config.getboolean('MIDI', label)
        self.app.config.set('MIDI', label, not enabled)
        if enabled and label is 'Pitchbend':
            self.device.set_pitchbend_range(self.app.config.getint('MIDI', 'PitchbendRange'))
        self.app.config.write()

    def set_instrument(self, instance):
        if isinstance(instance, int):
            instrument = instance
        else:
            if int(instance.text) > 127:
                instrument = 0
            else:
                instrument = int(instance.text)
        if self.app.pitchbend_enabled():
            for channel in range(16):
                self.device.change_instrument(channel, instrument)
        else:
            self.device.change_instrument(self.app.config.getint('MIDI', 'Channel'), instrument)

    def set_reverb(self, value):
        self.device.set_reverb(value)

    def mod_wheel(self, value):
        self.device.mod_wheel(self.app.lastchannel, value)

    def instrument_list():
        layout = GridLayout(cols=1, spacing=10, size_hint_y=None)
        layout.bind(minimum_height=layout.setter('height'))
        for i in range(128):
            btn = Button(text='{num:02d}: {}'.format(num(i), fluidsynth.GM_prog_name[i]), size_hint_y=None, font_size='15sp')
            layout.add_widget(btn)
            btn.bind(on_release=partial(set_instrument, i))
        instruments = ScrollView(size_hint=(1, None), size=(Window.width, Window.height))
        instruments.add_widget(layout)
        content = BoxLayout(orientation='vertical', spacing=10)
        popup = Popup(content=content, title='Choose an instrument:', size_hint=(.9, .9))
        content.add_widget(instruments)
        cancel = Button(text='Cancel', size_hint_y=None, font_size='15sp')
        cancel.bind(on_release=popup.dismiss)
        content.add_widget(cancel)
        popup.open()

class Key(Button):
    app = ObjectProperty(None)
    device = ObjectProperty(None)
    note = NumericProperty()
    row = NumericProperty()

    def pressure(self, touch):
        velocity = self.app.config.getint('MIDI', 'Velocity')
        if self.app.config.getboolean('MIDI', 'Aftertouch'):
            return max(0, velocity - round(abs(self.center_y - touch.y)) * self.app.config.getint('MIDI', 'Sensitivity'))
        else:
            return velocity

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos): return
        touch.ud['orig'] = touch.ud['prev'] = touch.ud['cur'] = self.note
        touch.ud['row'] = self.row
        channel = self.app.get_channel(touch)
        if self.app.pitchbend_enabled():
            self.device.pitch_bend(channel, 8192)
        self.device.note_on(self.note, self.pressure(touch), channel)

    def on_touch_up(self, touch):
        if not self.collide_point(*touch.pos): return
        channel = self.app.get_channel(touch)
        if self.app.pitchbend_enabled():
            self.device.reset(channel)
            self.app.free_channel(channel)
        else:
            self.device.note_off(touch.ud['cur'], channel)

    def on_touch_move(self, touch):
        if 'row' not in touch.ud: return
        if not self.app.grid.collide_point(*touch.pos) or touch.x == self.app.grid.width:
            self.device.note_off(self.note, self.app.get_channel(touch))
            return
        if not self.collide_point(*touch.pos): return
        channel = self.app.get_channel(touch)
        note = touch.ud['cur'] = self.note
        if self.app.pitchbend_enabled():
            pixel_distance = int(touch.x - touch.ox)
            pitch_value = int(pixel_distance * 8192.0 / (self.app.config.getint('MIDI', 'PitchbendRange') * self.width) + 0.5) + 8192
            if pitch_value > 16383:
                pitch_value = 16383
            elif pitch_value < 0:
                pitch_value = 0
            self.device.pitch_bend(channel, pitch_value)
        if not self.app.pitchbend_enabled() or self.row != touch.ud['row']:
            if touch.ud['prev'] != note:
                self.device.note_off(touch.ud['prev'], channel)
                self.device.note_on(note, self.pressure(touch), channel)
                touch.ud['prev'] = note
                if self.app.pitchbend_enabled():
                    touch.ud['orig'] = note
                    touch.ud['row'] = self.row
        if self.app.config.getboolean('MIDI', 'Aftertouch'):
            self.device.aftertouch(channel, note, self.pressure(touch))

class Grid(GridLayout):
    app = ObjectProperty(None)
    device = ObjectProperty(None)

    def __init__(self, **kwargs):
        super(Grid, self).__init__(**kwargs)

        rows = self.app.config.getint('MIDI', 'Rows')
        keys = self.app.config.getint('MIDI', 'Keys')
        lownote = self.app.config.getint('MIDI', 'LowNote')
        interval = self.app.config.getint('MIDI', 'Interval')

        notenames = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

        for row in range(rows):
            for note in reversed(range(lownote, lownote + keys)):
                accidental = True if note % 12 in [1, 3, 6, 8, 10] else False
                keycolor = [0,0,0,1] if accidental else [.4,0,0,1]
                textcolor = [.25,.25,.25,1] if accidental else [.5,.5,.5,1]
                label = notenames[note % 12]
                key = Key(app=self.app, device=self.device, note=note, row=row, text=label, background_color=keycolor, color=textcolor)
                self.add_widget(key, len(self.children))
            lownote += interval

class SettingMIDI(SettingItem):
    '''Implementation of an option list in top of :class:`SettingItem`.
    A label is used on the setting to show the current choice, and when you
    touch on it, a Popup will open with all the options displayed in list.
    '''

    '''
    :data:`options` is a :class:`~kivy.properties.ListProperty`, default to []
    '''

    popup = ObjectProperty(None, allownone=True)
    '''(internal) Used to store the current popup when it's shown

    :data:`popup` is a :class:`~kivy.properties.ObjectProperty`, default to
    None.
    '''

    def on_panel(self, instance, value):
        if value is None:
            return
        self.bind(on_release=self._create_popup)

    def _set_option(self, instance):
        self.value = instance.text
        # don't set the MIDI output here, but in the on_setting_change function!
        self.popup.dismiss()

    def _create_popup(self, instance):
        # create the popup containing a BoxLayout
        content = BoxLayout(orientation='vertical', spacing=10)
        self.popup = popup = Popup(content=content,
            title=self.title, size_hint=(None, None), size=(400, 400))
        popup.height = pygame.midi.get_count() * 30 + 150

        # add a spacer
        content.add_widget(Widget(size_hint_y=None, height=1))
        uid = str(self.uid)

        device_count = pygame.midi.get_count()

        # add all the selectable MIDI output devices
        for i in range(device_count):
            if pygame.midi.get_device_info(i)[3] == 1 and (pygame.midi.get_device_info(i)[4] == 0 or pygame.midi.get_device_info(i)[1].decode() == self.value):
                # if it's an output device and it's not already opened (unless it's the device opened by ME), display it in list.
                # if this is the device that was selected before, display it pressed
                state = 'down' if pygame.midi.get_device_info(i)[1].decode() == self.value else 'normal'
                btn = ToggleButton(text=str(pygame.midi.get_device_info(i)[1].decode()), state=state, group=uid)
                btn.bind(on_release=self._set_option)
                content.add_widget(btn)

        # finally, add a cancel button to return on the previous panel
        btn = Button(text='Cancel', size_hint_y=None, height=50)
        btn.bind(on_release=popup.dismiss)
        content.add_widget(btn)

        # and open the popup !
        popup.open()

class MasterGrid(App):
    title = 'MasterGrid'
    root = ObjectProperty(None)
    controls = ObjectProperty(None)
    grid = ObjectProperty(None)
    device = ObjectProperty(None)
    channels = [[c, None] for c in range(16)]
    span = 10
    lastchannel = 0

    def pitchbend_enabled(self):
        return self.config.getboolean('MIDI', 'Pitchbend')

    def get_channel(self, touch):
        if not self.pitchbend_enabled():
            return self.config.getint('MIDI', 'Channel')
        else:
            if 'channel' in touch.ud:
                return touch.ud['channel']
            else:
                return self.new_channel(touch)
        return self.new_channel(touch)

    def new_channel(self, touch):
        channels = self.channels
        lastchannel = self.lastchannel
        for span in range(self.span):
            candidate = lastchannel + 1 + span
            channel = candidate % self.span
            if channels[channel][1] == None:
                channels[channel][1] = touch.uid
                touch.ud['channel'] = channels[channel][0]
                lastchannel = touch.ud['channel']
                return touch.ud['channel']

    def free_channel(self, channel):
        self.channels[channel][1] = None

    def set_midi_device(self):
        c = pygame.midi.get_count()
        id_device_from_settings = -1
        for i in reversed(range(c)):
            if pygame.midi.get_device_info(i)[1].decode() == self.config.get('MIDI', 'Device'):
                id_device_from_settings = i

        if id_device_from_settings != -1:
            self.midi_device = id_device_from_settings
        else:
            self.midi_device = pygame.midi.get_default_output_id()

        if pygame.midi.get_device_info(self.midi_device)[4] == 1:
            print('Error: Unable to open MIDI device - Already in use!')

        self.midi = pygame.midi.Output(self.midi_device)

    def load_soundfont_from_filechooser(self, filechooser):
        self.config.set('MIDI', 'SoundFont', os.path.join(filechooser.path, filechooser.selection[0]))
        parent = self.root.parent
        parent.remove_widget(self.root)
        self.root = self.build_root()
        parent.add_widget(self.root)

    def cancel_soundfont_load(self, filechooser):
        if not self.config.get('MIDI', 'SoundFont'):
            content = Label(text='Please select a SoundFont.')
            popup = Popup(content=content, title='SoundFont required')
            btn = Button(text='OK')
            btn.bind(on_release=popup.dismiss)
            content.add_widget(btn)
            popup.open()
        else:
            filechooser.cancel()

    def build(self):
        if platform == 'android':
            filechooser = FileChooserListView(filters=['*.sf2', '*.sf3'])
            loadbtn = Button(text='Load SoundFont', on_release=self.load_soundfont_from_filechooser)
            cancelbtn = Button(text='Cancel', on_release=self.cancel_soundfont_load)
            settings = fluidsynth.FluidSettings()
            synth = fluidsynth.FluidSynth(settings)
            synth.load_soundfont(self.config.get('MIDI', 'SoundFont'))
            driver = fluidsynth.FluidAudioDriver(synth)
            self.device = FluidMIDI(app=self, midi=synth)
            return sfchooser
        else:
            pygame.midi.init()
            self.set_midi_device()
            self.device = PyGameMIDI(app=self, midi=self.midi)
            return self.build_root()

    def build_controls(self):
        self.controls = ControlBar(app=self, device=self.device, orientation='horizontal', size_hint=(1, .05))

    def build_grid(self):
        rows = self.config.getint('MIDI', 'Rows')
        keys = self.config.getint('MIDI', 'Keys')
        self.grid = Grid(app=self, device=self.device, rows=rows, cols=keys)

    def build_root(self):
        self.build_controls()
        self.build_grid()
        self.root = BoxLayout(orientation='vertical')
        self.root.add_widget(self.controls)
        self.root.add_widget(self.grid)
        return self.root

    def resize_grid(self):
        self.root.remove_widget(self.grid)
        self.build_grid()
        self.root.add_widget(self.grid)

    def build_config(self, config):
        config.adddefaultsection('MIDI')
        config.setdefault('MIDI', 'Device', 'FluidSynth')
        config.setdefault('MIDI', 'Channel', '0')
        config.setdefault('MIDI', 'Velocity', '127')
        config.setdefault('MIDI', 'Aftertouch', True)
        config.setdefault('MIDI', 'Pitchbend', False)
        config.setdefault('MIDI', 'PitchbendRange', '64')
        config.setdefault('MIDI', 'Sensitivity', '3')
        config.setdefault('MIDI', 'Rows', '13')
        config.setdefault('MIDI', 'Keys', '25')
        config.setdefault('MIDI', 'LowNote', '24')
        config.setdefault('MIDI', 'Interval', '5')

    def build_settings(self, settings):
        settings.register_type('midi', SettingMIDI)
        settings.add_json_panel('MasterGrid Settings', self.config, data='''[
            { "type": "midi", "title": "MIDI output device", "desc": "Device to use for MIDI", "section": "MIDI", "key": "Device"},
            { "type": "numeric", "title": "MIDI channel", "desc": "Global MIDI channel offset (ignored in continuous pitchbend mode)", "section": "MIDI", "key": "Channel"},
            { "type": "numeric", "title": "Velocity", "desc": "Default note velocity", "section": "MIDI", "key": "Velocity"},
            { "type": "bool", "title": "Aftertouch", "desc": "Polyphonic aftertouch expression", "section": "MIDI", "key": "Aftertouch"},
            { "type": "numeric", "title": "Aftertouch Sensitivity", "desc": "Velocity change multiplier", "section": "MIDI", "key": "Sensitivity"},
            { "type": "bool", "title": "Pitchbend", "desc": "Continuous pitchbend", "section": "MIDI", "key": "Pitchbend"},
            { "type": "numeric", "title": "Pitchbend Range", "desc": "Pitchbend range in semitones", "section": "MIDI", "key": "PitchbendRange"},
            { "type": "numeric", "title": "Lowest Note", "desc": "MIDI note number of the first note (bottom left key)", "section": "MIDI", "key": "LowNote"},
            { "type": "numeric", "title": "Rows", "desc": "Number of rows of keys", "section": "MIDI", "key": "Rows"},
            { "type": "numeric", "title": "Keys per row", "desc": "Number of notes per row", "section": "MIDI", "key": "Keys"},
            { "type": "numeric", "title": "Interval", "desc": "How many notes to shift each new row starting from the bottom", "section": "MIDI", "key": "Interval"}
        ]''')

    def on_config_change(self, config, section, key, value):
        token = (section, key)
        if token == ('MIDI', 'Device'):
            self.set_midi_device()
        elif token == ('MIDI', 'Channel'):
            pass
        elif token == ('MIDI', 'Velocity'):
            pass
        elif token == ('MIDI', 'Aftertouch'):
            pass
        elif token == ('MIDI', 'Sensitivity'):
            pass
        elif token == ('MIDI', 'Pitchbend'):
            pass
        elif token == ('MIDI', 'PitchbendRange'):
            self.device.set_pitchbend_range(value)
        elif token == ('MIDI', 'LowNote'):
            self.resize_grid()
        elif token == ('MIDI', 'Rows'):
            self.resize_grid()
        elif token == ('MIDI', 'Keys'):
            self.resize_grid()
        elif token == ('MIDI', 'Interval'):
            self.resize_grid()

if __name__ in ('__main__', '__android__'):
    MasterGrid().run()
