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

## Features

- **Models:** every model stores channel names, reverse, limits, stick mapping, layout and recordings. Two examples are included.
- **Layouts:** Standard, Joystick (stick 1 first, its channels hidden from the list) and Dual stick (two sticks side by side, works well in landscape).
- **Per channel:** maximum power, start power, fine control (expo curve with preview) and slider or hold-to-move control.
- **Record & replay:** record up to 90 seconds of control movements, then replay once or in a loop. Manual input is locked during replay and E-Stop cancels it.
- **Backup:** export all models to a file and import them again (in the app, through the system file picker).
- **Several hubs:** up to three hubs, each with its own module number (M1 to M3). The hubs are updated in turn, so response is slower than with one hub.

The hub only listens, so the app cannot show battery level or motor state.

## Notes

- The signing key (`app/release.keystore`) is committed on purpose so updates install over older builds.
  It only protects this personal app. Keep the repo private if you do not want others signing look-alike builds.
- The screen is a web page in `app/src/main/assets/index.html`; the Bluetooth part is in `Mk6Advertiser.java` and `Mk6Crypt.java`.
- Protocol credit: J0EK3R (MIT), see `NOTICE`.
