# MasterGrid
## Multitouch MIDI Grid powered by Python and Kivy

### Usage
MasterGrid runs on Windows and Linux, but it should also work on a Mac with a touchscreen.
This uses PyGame and PortMIDI, which have not yet been fully ported to Android or iOS.

MasterGrid does not generate sounds on its own, it relies on external hardware or software
to play sampled or synthesized sounds - e.g. FluidSynth, Linux Multimedia Studio or ZynAddSubFX.
To select an output device or program, open the settings menu by pressing Tab.

### Keyboard bindings
* Tab: opens settings.
* Space: toggles fullscreen.
* Escape: closes the app.

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
