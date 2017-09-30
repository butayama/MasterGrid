#!/usr/bin/python
'''
MasterGrid
Copyright (c) 2017 Robert Oscilowski

Multitouch Musical Instrument

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

from __future__ import division
import os
import kivy
from functools import partial
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.event import EventDispatcher
from kivy.uix.widget import Widget
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.slider import Slider
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.settings import SettingItem
from kivy.uix.colorpicker import ColorPicker
from kivy.properties import BooleanProperty, ObjectProperty, NumericProperty, StringProperty
from kivy.utils import rgba
from kivy.utils import platform
if platform == 'android':
    from jnius import autoclass
else:
    import pygame.midi

global app
global midi

class PyGameMIDI(EventDispatcher):
    global midi

    def __init__(self, **kwargs):
        super(PyGameMIDI, self).__init__(**kwargs)
        self.select_device()

    def select_device(self):
        c = pygame.midi.get_count()
        id_device_from_settings = -1
        for i in reversed(range(c)):
            if pygame.midi.get_device_info(i)[1] == app.config.get('MIDI', 'Device'):
                id_device_from_settings = i

        if id_device_from_settings != -1:
            midi_device = id_device_from_settings
        else:
            midi_device = pygame.midi.get_default_output_id()

        if pygame.midi.get_device_info(midi_device)[4] == 1:
            print('Error: Unable to open MIDI device - Already in use!')

        self.midi = pygame.midi.Output(midi_device)

    def set_instrument(self, instrument, channel):
        self.midi.set_instrument(instrument, channel=channel)

    def note_on(self, note, velocity, channel):
        self.midi.note_on(note, int(velocity), channel)

    def note_off(self, note, channel):
        self.midi.note_off(note, 0, channel)

    def mod(self, channel, value):
        self.midi.write_short(0xB0 + channel, 1, value)

    def breath(self, channel, value):
        self.midi.write_short(0xB0 + channel, 2, value)

    def foot(self, channel, value):
        self.midi.write_short(0xB0 + channel, 4, value)

    def expression(self, channel, value):
        self.midi.write_short(0xB0 + channel, 11, value)

    def pitchbend(self, channel, value):
        self.midi.write_short(0xE0 + channel, value - int(value / 128) * 128, int(value / 128))

    def set_pitchbend_range(self, value):
        for channel in range(16):
            self.midi.write_short(0xB0 + channel, 100, 0)
            self.midi.write_short(0xB0 + channel, 101, 0)
            self.midi.write_short(0xB0 + channel, 6, app.config.getint('Expression', 'PitchbendRange'))

    def poly_aftertouch(self, channel, note, pressure):
        self.midi.write_short(0xA0 + channel, note, int(pressure))

    def channel_aftertouch(self, channel, note, pressure):
        self.midi.write_short(0xD0 + channel, int(pressure))

    def aftertouch(self, channel, note, pressure):
        if app.config.get('Expression', 'PolyAftertouch'):
            self.poly_aftertouch(channel, note, pressure)
        else:
            self.channel_aftertouch(channel, note, pressure)

    def reverb(self, channel, value):
        self.midi.write_short(0xB0 + channel, 91, value)

    def set_reverb(self, value):
        if app.config.getboolean('Expression', 'Pitchbend'):
            for channel in range(16):
                self.reverb(channel, value)
        else:
            self.reverb(app.config.getint('MIDI', 'Channel'), value)

    def reset(self, channel):
        self.midi.write_short(0xB0 + channel, 123, 0)

    def panic(self):
        for channel in range(16):
            self.reset(channel)

class Key(Button):
    note = NumericProperty()
    row = NumericProperty()

    def __init__(self, **kwargs):
        super(Key, self).__init__(**kwargs)
        self.key_color_normal = self.background_color
        self.text_color_normal = self.color
        self.highlight = rgba(app.config.get('Grid', 'Highlight'))

    def pressure(self, touch):
        velocity = app.config.getint('MIDI', 'Volume')
        sens = app.config.getint('Expression', 'Sensitivity')
        if app.config.getboolean('Expression', 'Vertical'):
            return max(0, velocity - int(abs(self.center_y - touch.y)) * sens)
        elif app.config.getboolean('Expression', 'Pressure') \
            and 'pressure' in touch.profile:
            return int(round(touch.pressure / 2))
        else:
            return velocity

    def dead_key(self, touch):
        return False if self.note != None else True

    def on_touch_down(self, touch):
        if app.grid_disabled or self.dead_key(touch):
            return

        if not self.collide_point(*touch.pos):
            return super(Key, self).on_touch_down(touch)

        velocity = self.pressure(touch)
        touch.ud['note'] = touch.ud['prev'] = self.note
        touch.ud['row'] = self.row
        touch.ud['channel'] = channel = app.get_channel(touch)
        touch.ud['center'] = self.center_x

        if app.config.getboolean('Expression', 'Pitchbend'):
            midi.pitchbend(channel, 8192)
        midi.note_on(self.note, velocity, channel)

        self.background_color = self.highlight
        self.color = [0,0,0,1]
        touch.ud['key'] = self

    def on_touch_up(self, touch):
        if app.grid_disabled or self.dead_key(touch):
            return

        if not self.collide_point(*touch.pos) or app.controls.collide_point(*touch.opos):
            return super(Key, self).on_touch_up(touch)

        channel = touch.ud['channel']
        app.free_channel(channel)

        midi.note_off(touch.ud['note'], channel)

        self.background_color = self.key_color_normal
        self.color = self.text_color_normal

    def on_touch_move(self, touch):
        if app.grid_disabled or self.dead_key(touch):
            return

        if not self.collide_point(*touch.pos) or app.controls.collide_point(*touch.opos):
            return super(Key, self).on_touch_move(touch)

        channel = touch.ud['channel']
        note = touch.ud['note']
        velocity = self.pressure(touch)

        pitchbend_enabled = app.config.getboolean('Expression', 'Pitchbend')
        if pitchbend_enabled:
            bend_range = app.config.getint('Expression', 'PitchbendRange')
            distance = touch.x - touch.ud['center']    
            if distance and abs(app.grid.width / distance) < self.width / 6:
                if distance < 0:
                    distance += app.grid.width / distance
                if distance > 0:
                    distance -= app.grid.width / distance
            elif abs(distance) < self.width / 6:
                distance = 0
            if app.config.get('Grid', 'Layout') == 'Janko':
                distance *= 2 
            pitch = int(distance * 8192.0 / (bend_range * self.width)) + 8192
            if pitch > 16383:
                pitch = 16383
            elif pitch < 0:
                pitch = 0
            midi.pitchbend(channel, pitch)

        if not pitchbend_enabled or self.row != touch.ud['row']:
            if touch.ud['prev'] != self.note:
                midi.note_off(touch.ud['note'], channel)
                touch.ud['prev'] = touch.ud['note']
                touch.ud['note'] = self.note
                touch.ud['row'] = self.row
                midi.note_on(touch.ud['note'], self.pressure(touch), channel)

        if app.config.getboolean('Expression', 'Aftertouch'):
            midi.aftertouch(channel, note, velocity)

        if touch.ud['key'] != self:
            touch.ud['key'].background_color = touch.ud['key'].key_color_normal
            touch.ud['key'].color = touch.ud['key'].text_color_normal
            self.background_color = self.highlight
            self.color = [0,0,0,1]
            touch.ud['key'] = self

class Sonome(GridLayout):
    def __init__(self, **kwargs):
        super(Sonome, self).__init__(**kwargs)
        notenames = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        rows = app.config.getint('Grid', 'Rows')
        keys = app.config.getint('Grid', 'Keys')
        octave = app.config.getint('Grid', 'Octave')
        start = octave * 12

        for row in range(rows):
            for note in reversed(range(start, start + keys)):
                accidental = True if note % 12 in [1, 3, 6, 8, 10] else False
                keycolor = [0,0,0,1] if accidental else [255,255,255,1]
                textcolor = [1,1,1,1] if accidental else [0,0,0,1]
                label = notenames[note % 12]
                key = Key(note=note, row=row,
                          text=label, background_color=keycolor, color=textcolor,
                          background_normal='', highlight=[.75,.75,.75,.75])
                self.add_widget(key, len(self.children))
            start += 5

class JankoRow(BoxLayout):
    rownum = NumericProperty()
    start = NumericProperty()

    def __init__(self, **kwargs):
        super(JankoRow, self).__init__(**kwargs)
        notenames = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        keys = app.config.getint('Grid', 'Keys')
        rownum = self.rownum
        start = self.start

        if not rownum % 2:
            start += 1
        for note in range(start, start + keys * 2, 2):
            accidental = True if note % 12 in [1, 3, 6, 8, 10] else False
            keycolor = [0,0,0,1] if accidental else [255,255,255,1]
            textcolor = [1,1,1,1] if accidental else [0,0,0,1]
            label = notenames[note % 12]
            key = Key(note=note, row=rownum, text=label,
                      background_color=keycolor, color=textcolor,
                      background_normal='', highlight=[.75,.75,.75,.75])
            self.add_widget(key)

class Janko(BoxLayout):
    def __init__(self, **kwargs):
        super(Janko, self).__init__(**kwargs)
        keys = app.config.getint('Grid', 'Keys')
        rows = app.config.getint('Grid', 'JankoRows')
        octaves = app.config.getint('Grid', 'JankoOctaves')
        start = app.config.getint('Grid', 'Octave')

        for octave in range(octaves):
            for rownum in range(rows):
                space = 1 / keys / 2 if not rownum % 2 else 0
                note = start + (octave * 12)
                row = JankoRow(rownum=rownum, start=note,
                               pos_hint={'x':space}, orientation='horizontal')
                self.add_widget(row, len(row.children))

class Sizer(BoxLayout):
    section = StringProperty()
    label = StringProperty()
    low = NumericProperty()
    high = NumericProperty()
    inputbox = ObjectProperty(None)
    toolbar = BooleanProperty()

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
        return app.config.get(self.section, self.label)

    def set(self, value):
        self.inputbox.text = str(value)
        app.config.set(self.section, self.label, value)

    def plus(self, instance):
        value = app.config.getint(self.section, self.label)
        if self.low <= value < self.high:
            self.set(value + 1)
            if self.toolbar:
                app.resize_grid()

    def minus(self, instance):
        value = app.config.getint(self.section, self.label)
        if self.low < value <= self.high:
            self.set(value - 1)
            if self.toolbar:
                app.resize_grid()

class Controls(BoxLayout):
    def __init__(self, **kwargs):
        super(Controls, self).__init__(**kwargs)

        info = BoxLayout(orientation='vertical')
        logo = Label(text="MasterGrid")
        info.add_widget(logo)
        layout = Button(text=self.get_layout())
        layout.bind(on_release=self.switch_layout)
        info.add_widget(layout)
        self.add_widget(info)

        menu = Button(text="Settings")
        menu.bind(on_press=app.open_settings)
        self.add_widget(menu)

        pitchbend = ToggleButton(text="Pitchbend", state=self.get('Pitchbend'))
        pitchbend.bind(on_release=partial(self.set, 'Pitchbend'))
        self.add_widget(pitchbend)

        aftertouch = ToggleButton(text="Aftertouch", state=self.get('Aftertouch'))
        aftertouch.bind(on_release=partial(self.set, 'Aftertouch'))
        self.add_widget(aftertouch)

        octave = Sizer(toolbar=True, section='Grid', label='Octave', orientation='vertical', low=0, high=8)
        self.add_widget(octave)
        rows = Sizer(toolbar=True, section='Grid', label='Rows', orientation='vertical', low=8, high=36)
        self.add_widget(rows)
        keys = Sizer(toolbar=True, section='Grid', label='Keys', orientation='vertical', low=8, high=36)
        self.add_widget(keys)

        prog = BoxLayout(orientation='vertical')
        prog_label = Label(text="Instrument")
        prog_input = TextInput(on_text_validate=self.set_prog, multiline=False, input_filter='int', input_type='number')
        prog.add_widget(prog_label)
        prog.add_widget(prog_input)
        self.add_widget(prog)

        mod = BoxLayout(orientation='vertical')
        mod_label = Label(text="Modulation")
        mod_slider = Slider(min=0, max=127)
        mod_slider.bind(value=self.set_mod)
        mod.add_widget(mod_label)
        mod.add_widget(mod_slider)
        self.add_widget(mod)

        reverb = BoxLayout(orientation='vertical')
        reverb_label = Label(text="Reverb")
        reverb_slider = Slider(min=0, max=127)
        reverb_slider.bind(value=self.set_reverb)
        reverb.add_widget(reverb_label)
        reverb.add_widget(reverb_slider)
        self.add_widget(reverb)

        panic = Button(text="Panic", on_press=self.panic)
        self.add_widget(panic)

    def get_layout(self):
        return app.config.get('Grid', 'Layout')

    def set_layout(self, layout):
        return app.config.set('Grid', 'Layout', layout)

    def switch_layout(self, instance):
        layout = self.get_layout()
        if layout == 'Sonome':
            new_layout = 'Janko'
        elif layout == 'Janko':
            new_layout = 'Sonome'
        instance.text = new_layout
        self.set_layout(new_layout)
        app.resize_grid()

    def get(self, label):
        enabled = app.config.getboolean('Expression', label)
        return 'down' if enabled else 'normal'

    def set(self, label, value):
        enabled = app.config.getboolean('Expression', label)
        app.config.set('Expression', label, not enabled)
        if enabled and label is 'Pitchbend':
            midi.set_pitchbend_range(app.config.getint('Expression', 'PitchbendRange'))

    def set_prog(self, instance):
        if isinstance(instance, int):
            instrument = instance
        else:
            if int(instance.text) > 127:
                instrument = 0
            else:
                instrument = int(instance.text)
        if app.config.getboolean('Expression', 'Pitchbend'):
            for channel in range(16):
                midi.set_instrument(instrument, channel)
        else:
            midi.set_instrument(instrument, app.config.getint('MIDI', 'Channel'))

    def set_reverb(self, instance, value):
        for channel in range(16):
            midi.reverb(channel, int(value))

    def set_mod(self, instance, value):
        if app.config.getboolean('Expression', 'Pitchbend'):
            for channel in range(16):
                midi.mod(channel, int(value))
        else:
            midi.mod(app.config.getint('MIDI', 'Channel'), int(value))

    def panic(self, button):
        if platform == 'android':
            midi.sendMIDI(-1, 0xB0, 123, 0)
        else:
            midi.panic()

class SettingMIDI(SettingItem):
    popup = ObjectProperty(None, allownone=True)

    def on_panel(self, instance, value):
        if value is None:
            return
        self.bind(on_release=self._create_popup)

    def _set_option(self, instance):
        self.value = instance
        self.popup.dismiss()

    def _create_popup(self, instance):
        global midi
        content = BoxLayout(orientation='vertical', spacing=10)
        self.popup = popup = Popup(content=content,
            title=self.title, size_hint=(None, None), size=(400, 400))

        if platform == 'android':
            devices = midi.getDevices(midi.MIDIServer)
            device_count = len(devices)
        else:
            device_count = pygame.midi.get_count()
        popup.height = device_count * 50 + 150

        content.add_widget(Widget(size_hint_y=None, height=50))
        uid = str(self.uid)

        if platform == 'android':
            for i in xrange(device_count):
                for port in devices[i].getPorts(): 
                    if midi.getName(devices[i]) != 'MasterGrid' and (port.getType() == 2 or midi.getName(devices[i]) == self.value):
                        state = 'down' if midi.getName(devices[i]) == self.value else 'normal'
                        btn = ToggleButton(text=str(midi.getName(devices[i])), state=state, group=uid)
                        btn.bind(on_release=self._set_option)
                        content.add_widget(btn)
        else:
            for i in range(device_count):
                if pygame.midi.get_device_info(i)[3] == 1 and (pygame.midi.get_device_info(i)[4] == 0 or pygame.midi.get_device_info(i)[1] == self.value):
                    state = 'down' if pygame.midi.get_device_info(i)[1] == self.value else 'normal'
                    btn = ToggleButton(text=str(pygame.midi.get_device_info(i)[1]), state=state, group=uid)
                    btn.bind(on_release=self._set_option)
                    content.add_widget(btn)

        btn = Button(text='Cancel', size_hint_y=None, height=50)
        btn.bind(on_release=popup.dismiss)
        content.add_widget(btn)

        popup.open()

class SettingRange(SettingItem):
    popup = ObjectProperty(None, allownone=True)

    def on_panel(self, instance, value):
        if value is None:
            return
        self.bind(on_release=self._create_popup)

    def _set_option(self, instance):
        self.popup.dismiss()

    def _create_popup(self, instance):
        content = BoxLayout(orientation='vertical', spacing=10)
        self.popup = popup = Popup(content=content,
            title=self.title, size_hint=(.5, .5))

        if self.key == 'Channel':
            smin = 0; smax = 15
        elif self.key == 'Volume':
            smin = 0; smax = 127
        elif self.key == 'PitchbendRange':
            smin = 0; smax = 64
        elif self.key == 'Sensitivity':
            smin = 1; smax = 5
        elif self.key == 'JankoRows':
            smin = 2; smax = 5
        elif self.key == 'JankoOctaves':
            smin = 2; smax = 7
        elif self.key == 'Octave':
            smin = 0; smax = 8
        elif self.key == 'Rows':
            smin = 1; smax = 36
        elif self.key == 'Keys':
            smin = 1; smax = 36

        label = Label(text=self.desc)
        content.add_widget(label)

        self.manualentry = Sizer(toolbar=False, section=self.section, label=self.key, orientation='vertical', low=smin, high=smax)
        content.add_widget(self.manualentry)

        content.add_widget(Widget(size_hint_y=None, height=10))

        okbtn = Button(text='Close', size_hint_y=None, height=50)
        okbtn.bind(on_release=self._set_option)
        content.add_widget(okbtn)

        cancelbtn = Button(text='Cancel', size_hint_y=None, height=50)
        cancelbtn.bind(on_release=popup.dismiss)
        content.add_widget(cancelbtn)

        popup.open()

class SetLayout(SettingItem):
    popup = ObjectProperty(None)

    def on_panel(self, instance, value):
        if value is None:
            return
        self.bind(on_release=self.toggle)

    def toggle(self, instance):
        if self.value == 'Sonome':
            self.value = 'Janko'
        elif self.value == 'Janko':
            self.value = 'Sonome'

class SetColor(SettingItem):
    popup = ObjectProperty(None, allownone=True)

    def on_panel(self, instance, value):
        if value is None:
            return
        self.bind(on_release=self._create_popup)

    def _set_option(self, instance):
        self.value = self.colorpicker.hex_color
        self.popup.dismiss()

    def _create_popup(self, instance):
        content = BoxLayout(orientation='vertical')
        buttons = BoxLayout(orientation='horizontal')

        self.popup = popup = Popup(content=content, title=self.title,
            size_hint=(1, 1))

        self.colorpicker = colorpicker = ColorPicker(hex_color=self.value)
        content.add_widget(colorpicker)

        btn = Button(text='Select', size_hint=(.5, .1))
        btn.bind(on_release=self._set_option)
        buttons.add_widget(btn)

        btn = Button(text='Cancel', size_hint=(.5, .1))
        btn.bind(on_release=popup.dismiss)
        buttons.add_widget(btn)

        content.add_widget(buttons)

        popup.open()

class MasterGrid(App):
    title = 'MasterGrid'
    root = ObjectProperty(None)
    controls = ObjectProperty(None)
    grid = ObjectProperty(None)
    channels = [[c, None] for c in range(16)]
    lastchannel = 0
    grid_disabled = False

    def get_channel(self, touch):
        if not self.config.getboolean('Expression', 'Pitchbend'):
            return self.config.getint('MIDI', 'Channel')
        else:
            if 'channel' in touch.ud:
                return touch.ud['channel']
            else:
                return self.new_channel(touch)

    def new_channel(self, touch):
        for span in range(10):
            candidate = self.lastchannel + span
            channel = candidate % 10
            if channel == 9:
                channel += 1 
            if self.channels[channel][1] == None:
                self.channels[channel][1] = touch.uid
                touch.ud['channel'] = self.channels[channel][0]
                self.lastchannel = touch.ud['channel']
                return touch.ud['channel']

    def free_channel(self, channel):
        self.channels[channel][1] = None

    def build_controls(self):
        self.controls = Controls(orientation='horizontal', size_hint=(1, .064))

    def build_grid(self):
        rows = self.config.getint('Grid', 'Rows')
        cols = self.config.getint('Grid', 'Keys')
        if self.config.get('Grid', 'Layout') == 'Sonome':
            self.grid = Sonome(rows=rows, cols=cols)
        elif self.config.get('Grid', 'Layout') == 'Janko':
            self.grid = Janko(orientation='vertical')

    def build(self):
        global midi
        if platform == 'android':
            VirtualMIDI = autoclass('org.mastergrid.VirtualMIDI')
            midi = VirtualMIDI()
            if not midi.started:
                self.server = midi.setUpMIDIServer()
            else:
                self.server = midi.MIDIServer
        else:
            pygame.midi.init()
            midi = PyGameMIDI()

        self.build_controls()
        self.build_grid()
        self.root = BoxLayout(orientation='vertical')
        self.root.add_widget(self.controls)
        self.root.add_widget(self.grid)
        return self.root

    def resize(self):
        self.resize_controls()
        self.resize_grid()

    def resize_controls(self):
        self.root.remove_widget(self.controls)
        self.build_controls()
        self.root.add_widget(self.controls)

    def resize_grid(self):
        self.root.remove_widget(self.grid)
        self.build_grid()
        self.root.add_widget(self.grid)

    def build_config(self, config):
        config.adddefaultsection('MIDI')
        config.setdefault('MIDI', 'Device', 'Fluidsynth')
        config.setdefault('MIDI', 'Channel', '0')
        config.setdefault('MIDI', 'Volume', '127')
        config.adddefaultsection('Expression')
        config.setdefault('Expression', 'Pitchbend', True)
        config.setdefault('Expression', 'PitchbendRange', '64')
        config.setdefault('Expression', 'Aftertouch', True)
        config.setdefault('Expression', 'Vertical', True)
        config.setdefault('Expression', 'Pressure', False)
        config.setdefault('Expression', 'PolyAftertouch', True)
        config.setdefault('Expression', 'Sensitivity', '2')
        config.adddefaultsection('Grid')
        config.setdefault('Grid', 'Layout', 'Sonome')
        config.setdefault('Grid', 'JankoOctaves', '6')
        config.setdefault('Grid', 'JankoRows', '3')
        config.setdefault('Grid', 'Octave', '0')
        config.setdefault('Grid', 'Rows', '10')
        config.setdefault('Grid', 'Keys', '36')
        config.setdefault('Grid', 'Highlight', '#8080ffff')

    def build_settings(self, settings):
        settings.register_type('midi', SettingMIDI)
        settings.register_type('range', SettingRange)
        settings.register_type('layout', SetLayout)
        settings.register_type('color', SetColor)
        settings.add_json_panel('MasterGrid Settings', self.config, data='''[
            { "type": "midi", "title": "MIDI output device", "desc": "Device or app to receive MIDI from MasterGrid", "section": "MIDI", "key": "Device"},
            { "type": "range", "title": "Default channel", "desc": "Default MIDI channel", "section": "MIDI", "key": "Channel"},
            { "type": "range", "title": "Volume", "desc": "Default MIDI note velocity (0-127)", "section": "MIDI", "key": "Volume"},
            { "type": "bool", "title": "Pitchbend", "desc": "Continuous pitchbend", "section": "Expression", "key": "Pitchbend"},
            { "type": "range", "title": "Pitchbend Range", "desc": "Pitchbend range in semitones", "section": "Expression", "key": "PitchbendRange"},
            { "type": "bool", "title": "Aftertouch", "desc": "Aftertouch expression", "section": "Expression", "key": "Aftertouch"},
            { "type": "bool", "title": "Vertical Expression", "desc": "Vertical expression", "section": "Expression", "key": "Vertical"},
            { "type": "bool", "title": "Pressure Sensitivity", "desc": "Expression based on touch pressure", "section": "Expression", "key": "Pressure"},
            { "type": "bool", "title": "Polyphonic Aftertouch", "desc": "Sends polyphonic MIDI aftertouch messages", "section": "Expression", "key": "PolyAftertouch"},
            { "type": "range", "title": "Sensitivity", "desc": "Aftertouch sensitivity", "section": "Expression", "key": "Sensitivity"},
            { "type": "layout", "title": "Layout", "desc": "Select a note layout", "section": "Grid", "key": "Layout"},
            { "type": "range", "title": "Octaves", "desc": "Number of octaves (Janko layout only)", "section": "Grid", "key": "JankoOctaves"},
            { "type": "range", "title": "Rows per octave group", "desc": "Number of rows (Janko layout only)", "section": "Grid", "key": "JankoRows"},
            { "type": "range", "title": "Starting octave", "desc": "Octave of bottom left note", "section": "Grid", "key": "Octave"},
            { "type": "range", "title": "Rows", "desc": "Number of rows", "section": "Grid", "key": "Rows"},
            { "type": "range", "title": "Keys", "desc": "Semitones per row", "section": "Grid", "key": "Keys"},
            { "type": "color", "title": "Highlight color", "desc": "Key highlight color", "section": "Grid", "key": "Highlight"}
        ]''')

    def display_settings(self, settings):
        self.grid_disabled = True
        App.display_settings(self, settings)

    def close_settings(self, *largs):
        self.grid_disabled = False
        App.close_settings(self, largs)

    def on_config_change(self, config, section, key, value):
        if key == 'Device':
            midi.select_device()
        elif key == 'Layout':
            self.resize()
        elif key == 'Rows':
            self.resize()
        elif key == 'Keys':
            self.resize()
        elif key == 'Octaves':
            self.resize()
        elif key == 'JankoRows':
            self.resize()
        elif key == 'JankoKeys':
            self.resize()
        elif key == 'JankoOctaves':
            self.resize()
        else:
            pass

if __name__ in ('__main__', '__android__'):
    try:
        app = MasterGrid()
        app.run()
    finally:
        if platform == 'android':
            midi.tearDownMIDIServer(app.server)
        else:
            midi.midi.close()
        app.config.write()
