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
- **Layouts:** Standard, Joystick, Dual stick and a free **Board** (sliders, hold buttons, sticks, double sticks, sequence buttons, lights and mixers; vertical sliders; tilt steering).
- **Lights:** set a channel to *Light* for on/off, brightness (gamma-corrected so dimming looks even) and slow/fast/pulse blinking. Blinking is slow on purpose because the hub only catches an update every 100 to 200 ms.
- **Mixer:** one Board slider that drives up to four channels, each with its own ratio and direction.
- **Toggles and Turbo:** Board toggles (LED button, latch switch, forward/stop/reverse) and a hold-to-boost Turbo button that lifts a channel to full power while pressed (it still respects Player mode limits).
- **Power profiles:** Kid, Normal and Full presets (power limit and smoothing) switch with one tap; save the current limit into any of them.
- **Stick range:** cap how much output a stick can give (25 to 100%).
- **Hub names:** give each hub a short name, shown in the channel list.
- **Test hub and Calibration:** move each active channel at the **Test power** set in the Calibration card (default 60%, per model). It ignores Limit and Speed, so raise it until the motor just moves.
- **Dashboard (landscape, 3D joystick and slider, Back puts the last removed widget back; layout templates: Car / Truck, Excavator, Dual stick):** in Board layout, tick "Dashboard when the phone is sideways". The board becomes a full-screen canvas. Tap Edit to drag and resize widgets (snapped to a fine 48x24 grid, no overlaps), change each widget colour, and Add widget. An E-Stop widget can be added or removed (the header E-Stop button is always there). The layout is saved per model.
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

## Notes

- The signing key (`app/release.keystore`) is committed on purpose so updates install over older builds.
  It only protects this personal app. Keep the repo private if you do not want others signing look-alike builds.
- The screen is a web page in `app/src/main/assets/index.html`; the Bluetooth part is in `Mk6Advertiser.java` and `Mk6Crypt.java`.
- Protocol credit: J0EK3R (MIT), see `NOTICE`.
