# MasterGrid
## Multitouch MIDI Grid powered by Python and Kivy

### Usage
MasterGrid works on Windows and Linux, and could also be coerced to run on Apple devices.
This was designed for use with a capacitive touchscreen.
This requires an Python installation with Kivy, and except on Android, where FluidSynth has been integrated,
you will also need PyGame and a platform that supports PortMIDI.

MasterGrid does not generate sounds on its own, it relies on external MIDI hardware or software
to play sampled or synthesized sounds, such as FluidSynth, Linux Multimedia Studio or ZynAddSubFX.
You will need to select an output device or program in MasterGrid's settings menu before this will make any sound.

### Credits
MasterGrid draws inspiration from various apps by [Rob Fielding](https://github.com/rfielding),
including Mugician and Cantor for iOS, CSharpAttempt for Windows 8,
as well as some similar Android apps such as IsoKeys/Hexiano.

No code was used from the above projects, but the implementation of continuous pitchbend
in MasterGrid does approximately the same thing as Rob Fielding's fretless library,
using one MIDI channel for each touch point.

MasterGrid uses code snippets from [IcarusTouch](http://github.com/stocyr/IcarusTouch),
which is licensed under the terms of the GNU General Public License, version 3 or later.
See LICENSE for the full text of the license.

Copyright (c) 2016 Robert Oscilowski.
Portions Copyright (c) 2011 Cyril Stoller.
