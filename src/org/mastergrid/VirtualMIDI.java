package org.mastergrid;

import org.kivy.android.PythonActivity;
import android.content.Context;
import android.content.pm.PackageManager;
import android.media.midi.MidiManager;
import android.media.midi.MidiOutputPort;
import android.media.midi.MidiDevice;
import android.media.midi.MidiDevice.MidiConnection;
import android.media.midi.MidiDeviceInfo;
import android.media.midi.MidiDeviceInfo.PortInfo;
import android.media.midi.MidiDeviceStatus;
import android.media.midi.MidiInputPort;
import android.media.midi.MidiReceiver;
import android.media.midi.MidiSender;
import android.os.Bundle;

import java.io.IOException;

public class VirtualMIDI {
    Context mContext = (Context) PythonActivity.mActivity;

    static class MidiContext {
        MidiDeviceInfo midiInfo;
        MidiDevice midiDevice;
        MidiInputPort midiInputPort;
        MidiOutputPort midiOutputPort;
    }

    public MidiContext MIDIServer;
    public boolean started = false;

    class MidiOpenCallback implements MidiManager.OnDeviceOpenedListener {
        MidiDevice mDevice;
        @Override
        public synchronized void onDeviceOpened(MidiDevice device) {
            mDevice = device;
            notifyAll();
        }
        public synchronized MidiDevice waitForOpen(int msec)
                throws InterruptedException {
            long deadline = System.currentTimeMillis() + msec;
            long timeRemaining = msec;
            while (mDevice == null && timeRemaining > 0) {
                wait(timeRemaining);
                timeRemaining = deadline - System.currentTimeMillis();
            }
            return mDevice;
        }
    }

    public MidiDeviceInfo findMIDIDevice(String name) {
        MidiManager midiManager = (MidiManager) mContext.getSystemService(
                Context.MIDI_SERVICE);
        MidiDeviceInfo[] infos = midiManager.getDevices();
        MidiDeviceInfo midiInfo = null;
        for (MidiDeviceInfo info : infos) {
            Bundle properties = info.getProperties();
            String Name = (String) properties.get(
                    MidiDeviceInfo.PROPERTY_NAME);
            if (name.equals(Name)) {
                midiInfo = info;
                break;
            }
        }
        return midiInfo;
    }

    public MidiDeviceInfo[] getDevices(MidiContext mc) {
        MidiManager midiManager = (MidiManager) mContext.getSystemService(
                Context.MIDI_SERVICE);
        return midiManager.getDevices();
    }

    public String getName(MidiDeviceInfo info) {
        Bundle properties = info.getProperties();
        String name = (String) properties.get(
                    MidiDeviceInfo.PROPERTY_NAME);
        return name;
    }

    public MidiInputPort getMIDIInputPort(MidiContext mc) {
        return mc.midiInputPort;
    }

    public void connectUsbMidi(MidiManager midiManager,
            MidiDevice midiDevice, MidiDeviceInfo usbInfo)
            throws Exception {
        MidiOpenCallback callback = new MidiOpenCallback();
        midiManager.openDevice(usbInfo, callback, null);
        MidiDevice usbDevice = callback.waitForOpen(1000);
        MidiInputPort usbInputPort = usbDevice.openInputPort(0);
        midiDevice.connectPorts(usbInputPort, 0);
    }

    public MidiContext setUpMIDIServer() throws Exception {
        MidiManager midiManager = (MidiManager) mContext.getSystemService(
                Context.MIDI_SERVICE);
        MidiDeviceInfo midiInfo = findMIDIDevice("MasterGrid");
        MidiDeviceInfo usbInfo = findMIDIDevice("Android USB Peripheral Port");
        MidiOpenCallback callback = new MidiOpenCallback();
        midiManager.openDevice(midiInfo, callback, null);
        MidiDevice midiDevice = callback.waitForOpen(1000);
        VirtualMIDIService midiService = VirtualMIDIService.getInstance();
        MidiInputPort midiInputPort = midiDevice.openInputPort(0);
        MidiOutputPort midiOutputPort = midiDevice.openOutputPort(0);
        if (usbInfo != null) {
            connectUsbMidi(midiManager, midiDevice, usbInfo);
        }
        MidiContext mc = new MidiContext();
        mc.midiInfo = midiInfo;
        mc.midiDevice = midiDevice;
        mc.midiInputPort = midiInputPort;
        mc.midiOutputPort = midiOutputPort;
        started = true;
        MIDIServer = mc;
        return mc;
    }

    public void tearDownMIDIServer(MidiContext mc) throws IOException {
        VirtualMIDIService midiService = VirtualMIDIService.getInstance();
        mc.midiOutputPort.close();
        mc.midiOutputPort.close();
        mc.midiInputPort.close();
        mc.midiInputPort.close();
        mc.midiDevice.close();
        mc.midiDevice.close();
        started = false;
    }

    public void sendMIDI(int channel, int cmd, int param1, int param2)
            throws IOException {
        byte[] buffer = new byte[32];
        int numBytes = 0;
        if (channel == -1) {
            buffer[numBytes++] = (byte)(cmd);
        } else {
            buffer[numBytes++] = (byte)(cmd + channel);
        }
        buffer[numBytes++] = (byte)param1;
        if (param1 != -1) buffer[numBytes++] = (byte)param2;
        int offset = 0;
        MIDIServer.midiInputPort.send(buffer, offset, numBytes);
    }

    public void note_on(int note, int velocity, int channel)
            throws IOException {
        sendMIDI(channel, 0x90, note, velocity);
    }

    public void note_off(int note, int channel)
            throws IOException {
        sendMIDI(channel, 0x80, note, 0);
    }

    public void set_instrument(int instrument, int channel)
            throws IOException {
        sendMIDI(channel, 0xC0, instrument, -1);
    }

    public void set_pitchbend_range(int range)
            throws IOException {
        for (int channel = 0; channel < 16; channel++) {
            sendMIDI(channel, 0xB0, 100, 0);
            sendMIDI(channel, 0xB0, 101, 0);
            sendMIDI(channel, 0xB0, 6, range);
        }
    }

    public void pitchbend(int channel, int pitch)
            throws IOException {
        sendMIDI(channel, 0xE0, pitch & 0x7f, (pitch >> 7) & 0x7f);
    }

    public void aftertouch(int channel, int note, int velocity)
            throws IOException {
        sendMIDI(channel, 0xA0, note, velocity);
    }

    public void mod(int channel, int value)
            throws IOException {
        sendMIDI(channel, 0xB0, 1, value);
    }

    public void reverb(int channel, int value)
            throws IOException {
        sendMIDI(channel, 0xB0, 91, value);
    }
}
