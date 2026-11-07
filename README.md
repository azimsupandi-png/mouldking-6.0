# MK6 Console

Android app that controls one to three **Mould King Module 6.0** hubs (6 channels each) from your phone.
The hubs are driven by encrypted Bluetooth LE advertisements, so no pairing is needed.

## Get the APK

1. Open the **Releases** page of this repo on your phone.
2. Download `MK6-Console.apk` from the newest build.
3. Open the file and allow "Install unknown apps" for your browser when Android asks.

Every push to `main` builds a new signed APK (GitHub Actions, `.github/workflows/build.yml`).
You can also start a build by hand from the **Actions** tab (Run workflow).

## Use it

1. Switch each hub to Bluetooth (app) mode and power it on.
2. Open MK6 Console and allow the Bluetooth permission.
3. Tap **Connect hub** and wait about 3 seconds until it says **Hub active**.
4. Move the sliders, hold buttons or sticks. **E-Stop** locks every channel at 0 until you tap **Release E-Stop**.

The app stops broadcasting when it leaves the screen, so motors do not keep running in the background.

## Setting the hub number

Each hub needs its own number (M1, M2 or M3) when you use more than one. Press the hub's power button briefly: the LED flashes 1, 2 or 3 times, which is its number. Pick the same numbers under **Limits & hubs** in the app.

## Features

- **Models:** every model stores channel names, reverse, limits, stick mapping, layout and recordings. Two examples are included.
- **Look:** one brick-style theme (dark panels, studs, hazard stripes, yellow accent), power rings on every channel and stick, and a status line under the title.
- **Header:** a Bluetooth button (green tick / red cross, follows the phone's Bluetooth and opens its settings), a hub button (play to connect, pause to disconnect, pulses while active) and a stop button for **E-Stop**.
- **Layouts:** Standard, Joystick, Dual stick and a free **Board** (sliders with an optional hold mode, sticks, double sticks, lights, mixers, toggles, turbo, ramps, gears, dials, meters and a session timer; vertical sliders; tilt steering).
- **Lights:** set a channel to *Light* for on/off, brightness (gamma-corrected so dimming looks even) and slow/fast/pulse blinking. Blinking is slow on purpose because the hub only catches an update every 100 to 200 ms.
- **Mixer:** one Board slider that drives up to four channels, each with its own ratio and direction.
- **Steering wheel, Gear lever, D-pad:** the Steering wheel turns by dragging (full lock 90, 180 or 270 degrees in total) and springs back to centre, or stays if you choose. The Gear lever is a vertical lever with click stops 3, 2, 1, N, R (set in Gear settings). The D-pad drives with four buttons: hold to move, or tap to toggle; tank mode uses two motors, car mode one drive and one steering channel; power and ramp time are set in its settings.
- **Gamepad and the Dial selector:** in Gamepad Button mapping you can pick previous position, next position and on/off for the Dial selector.
- **Tidy:** in Dashboard edit, Tidy packs the widgets in aligned rows without gaps (Back undoes it).
- **Arc and LED meter direction:** in the meter settings choose Both ways (-100 to +100, zero at the top) or Forward only (0 to 100, filling from the start; negative values show 0).
- **Dial and Dial selector:** the Dial sets a channel by touch and drag, with an LED ring around it (colour theme, optional forward-only 0 to 100). Press and hold until it vibrates to switch the output on or off; it ramps over a time you set (default 3 s) to avoid jerking. The Dial selector chooses one of 4 or 6 outputs per hub with six small marker dots; the chosen output stays off until you press and hold, and changing position switches the old output off.
- **Meters and Scope:** Arc meter, LED meter and a Scope (10, 30 or 60 s, record, pause, step back and forward, optional target line). A Ramp widget can show its own scope with the target and rise time.
- **Toggles and Turbo:** Board toggles (LED button, latch switch, forward/stop/reverse) and a hold-to-boost Turbo button that lifts a channel to full power while pressed (it still respects Player mode limits).
- **Power profiles:** Kid, Normal and Full presets (power limit and smoothing) switch with one tap; save the current limit into any of them.
- **Stick range:** cap how much output a stick can give (25 to 100%).
- **Hub names:** give each hub a short name, shown in the channel list.
- **Test hub and Calibration:** move each active channel at the **Test power** set in the Calibration card (default 60%, per model). It ignores Limit and Speed, so raise it until the motor just moves.
- **Dashboard (landscape, 3D joystick and slider, Back puts the last removed widget back; layout templates: Car / Truck, Excavator, Dual stick, Monitor, 4 motors + driver, plus up to 10 of your own saved layouts that work in every model and are kept in backups):** in Board layout, tick "Dashboard when the phone is sideways". The board becomes a full-screen canvas. Tap Edit to drag and resize widgets (snapped to a fine 48x24 grid, no overlaps), and Add widget. An E-Stop widget can be added or removed (the header E-Stop button is always there). The layout is saved per model.
- **Joystick tuning:** in Dashboard edit mode, the gear button on a joystick sets its deadzone, sensitivity, power limit and axis lock (free, left/right only or up/down only). Each joystick is tuned separately and the settings are saved with the layout.
- **Slider shortcut:** tap the number at the top right of a Board slider to send it back to 0.
- **Export / import layouts:** Template > Export layout gives a text you can copy; Import layout pastes one back (Back undoes it).
- **Hub safety and comfort:** the hub link is restored (motors at zero) when you come back to the app, can be switched off in Settings; Edit, Reset and the model picker are locked on the Dashboard while the hub is active, and Reset needs a second tap.
- **Effects:** Settings > Effects is Auto (the Dashboard drops glow, shadows and the knob image step by step on phones that cannot keep up), Full or Lightweight. A hidden performance readout opens by holding the title for a second.
- **Per channel:** maximum power, start power, fine control (expo curve with preview) and slider or hold-to-move control.
- **Record & replay:** record up to 90 seconds of control movements, then replay once or in a loop. Manual input is locked during replay and E-Stop cancels it.
- **Backup:** export all models to a file and import them again (in the app, through the system file picker).
- **Sequences & quick actions:** build timed step lists (channel, power, seconds, "together" with the previous step, optional loop, repeat 1 to 10 times, speed 0.5x to 2x, start delay). Every sequence gets a big button at the top of the page. A second tap or E-Stop stops it and every channel returns to 0.
- **Gamepad:** pair a Bluetooth controller in Android settings and press a button. Left stick = stick 1, right stick = stick 2 (Dual stick layout), RT/LT drive a trigger channel, Back = E-Stop, Start = release. Dead zone is adjustable, and unplugging the pad stops the motors.
- **Safety:** auto-stop after a set idle time, a warning after long full-power running, E-Stop on the gamepad (Back/Start), and motors stop when the app leaves the screen.
- **Gamepad buttons:** map A/B/X/Y, bumpers, sticks' clicks and the D-pad to hold a channel forward or reverse, run a sequence, or stop everything.
- **Sound and vibration** feedback (can be switched off) and **home-screen shortcuts**: long-press the app icon for your models, or add one model to the home screen from the App card.
- **Language:** English or Bahasa Melayu, plus a short first-run guide (reopen it from the App card).
- **Several hubs:** up to three hubs, each with its own module number (M1 to M3). The hubs are updated in turn, so response is slower than with one hub.

The hub only listens, so the app cannot show battery level or motor state.

### LED meter layout
- The LED bar fills the whole card. Its value is a small yellow number at the top right of the card (no big white value inside).
- In an LED meter's settings, "Bar layout" switches the LED bar between vertical and horizontal. Horizontal runs left to right (both ways: -100 on the left, +100 on the right).

### Slider and joystick extras
- **Quick values**: a row of chips (−100, −50, 0, +50, +100) under every slider channel.
- **Step size**: in a channel's settings, pick 1, 5 or 10 for the ◀ ▶ buttons (hold to repeat).
- **Joystick axis bars**: two bars under each pad show Drive/Steer (or Left/Right).

- **Swipe joystick pairs** (Board): in a joystick's settings turn on "Swipe to other pairs". Swipe the card sideways (not on the pad) to move between channel pairs (A+B, C+D, E+F). Dots show the pair (3 + 3 + 3 with three hubs), and the old pair is set to 0.

### Start / stop button (Board)
- A round push button with a 40-LED ring and START / STOP wording on the centre button (red ring, white START and red STOP when stopped; all yellow when started). It turns the hub link on and off, like the green button at the top. It has no title and no hint text, only a small ON / OFF word under the ring.
- Hold it (0.5 s by default; 0.3 / 0.5 / 0.8 / 1.2 s in the gear). When the time is up the phone vibrates, and only then do the LEDs change: red turns to glowing yellow one by one when starting, and back to red one by one when stopping. A short tap does nothing.
- The whole ring flashes yellow while E-Stop is on or the hub has a fault (Bluetooth off, link lost, permission denied).
- The button is not dimmed when the hub is off, so you can always start it again.

## Notes

- The signing key (`app/release.keystore`) is committed on purpose so updates install over older builds.
  It only protects this personal app. Keep the repo private if you do not want others signing look-alike builds.
- The screen is a web page in `app/src/main/assets/index.html`; the Bluetooth part is in `Mk6Advertiser.java` and `Mk6Crypt.java`.
- Protocol credit: J0EK3R (MIT), see `NOTICE`.

## Regression test

`python3 tests/widgets_test.py` loads the app in headless Chromium and checks every board
widget kind (render, settings popup, behaviour, reload) in landscape and portrait. It needs
Python with `playwright` and Chromium installed. Run it before each commit.

`python3 tests/dashboard_edit_test.py` checks Dashboard editing in landscape (drag, select, resize, templates).

`python3 tests/features_test.py` checks the dashboard polish features below.

### Dial

The dial turns relative to where it is: touching it never jumps to another value, and it stops at the ends instead of wrapping round. In the dial's settings, *Swipe to other channels* lets you swipe sideways on the card (outside the knob) to move the dial to the next channel, like the arc meter.

The dial selector also turns relative to where it is and steps through the positions in order (A to F), and the position you leave fades out over the on/off ramp time instead of cutting off.

### Steering wheel gyro

In the steering wheel's settings, *Gyro* (Off/On) lets you hold the wheel and tilt the phone to steer, like tilt steering. It uses the tilt sensitivity and reverse settings from the Tilt steering card, and works even if that card's master switch is off.

### Dashboard polish
- **Channel chip:** widget titles show a yellow chip with the channel letter plus the channel name (the full title is the tooltip).
- **Hub limit tick:** arc and LED meters mark the hub's real maximum (power limit, speed, channel max) with a white tick when it is below 100%.
- **Hub lost:** when the hub link drops, widgets dim and a red banner appears (tap to dismiss); both clear when the hub is back.
- **Selector dots:** the selected position is a bigger red dot, the others are small grey dots.
- **Gyro steering:** wheel settings have a dead zone (Off/3/5/8 degrees) and a per-wheel sensitivity (30/45/60 degrees for full lock, or the phone setting).
- **Second channel:** slider, dial and wheel settings can also drive another channel of the same hub with the same value or the opposite one (tank turn).
- **Edit mode:** the hub cannot be connected while editing the board.
- **Lock:** the Lock button in the dashboard bar makes the board untouchable (E-Stop still works). Hold the lock button for 1 s to unlock.
- **Board history:** the last 3 boards per model are kept every time editing finishes; restore them from Settings, Board history.
