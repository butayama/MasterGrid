package org.mastergrid;

import android.media.midi.MidiDeviceService;
import android.media.midi.MidiDeviceStatus;
import android.media.midi.MidiReceiver;

import java.io.IOException;

public class VirtualMIDIService extends MidiDeviceService {
    private MidiReceiver mInputReceiver = new MasterGridReceiver();
    private MidiReceiver mOutputReceiver;
    private static VirtualMIDIService mInstance;
    public int statusChangeCount;
    public boolean inputOpened;
    public int outputOpenCount;

    @Override
    public void onCreate() {
        super.onCreate();
        mInstance = this;
    }

    @Override
    public void onDestroy() {
        super.onDestroy();
    }

    public static VirtualMIDIService getInstance() {
        return mInstance;
    }

    @Override
    public MidiReceiver[] onGetInputPortReceivers() {
        return new MidiReceiver[] { mInputReceiver };
    }

    class MasterGridReceiver extends MidiReceiver {
        @Override
        public void onSend(byte[] data, int offset, int count, long timestamp)
                throws IOException {
            if (mOutputReceiver == null) {
                mOutputReceiver = getOutputPortReceivers()[0];
            }
            mOutputReceiver.send(data, offset, count, timestamp);
        }
    }

    @Override
    public void onDeviceStatusChanged(MidiDeviceStatus status) {
        statusChangeCount++;
        inputOpened = status.isInputPortOpen(0);
        outputOpenCount = status.getOutputPortOpenCount(0);
    }
}
