# MK6 Console

Android app that controls a **Mould King Module 6.0** (6 channels) from your phone.
The hub is driven by encrypted Bluetooth LE advertisements, so no pairing is needed.

## Get the APK

1. Open the **Releases** page of this repo on your phone.
2. Download `MK6-Console.apk` from the newest build.
3. Open the file and allow "Install unknown apps" for your browser when Android asks.

Every push to `main` builds a new signed APK (GitHub Actions, `.github/workflows/build.yml`).
You can also start a build by hand from the **Actions** tab (Run workflow).

## Use it

1. Switch the hub to Bluetooth (app) mode and power it on.
2. Open MK6 Console and allow the Bluetooth permission.
3. Tap **Sambung hab** and wait about 3 seconds until it says **Hab aktif**.
4. Move the sliders or joystick. **E-Stop** sets every channel to 0.

The app stops broadcasting when it leaves the screen, so motors do not keep running in the background.

## Notes

- The signing key (`app/release.keystore`) is committed on purpose so updates install over older builds.
  It only protects this personal app. Keep the repo private if you do not want others signing look-alike builds.
- The screen is a web page in `app/src/main/assets/index.html`; the Bluetooth part is in `Mk6Advertiser.java` and `Mk6Crypt.java`.
- Protocol credit: J0EK3R (MIT), see `NOTICE`.
