# Charge Check (iPhone Shortcut)

Reminds you to charge your **Apple Watch and AirPods** on the wireless pad, only
when they're low, and reminds you again when it's time to take them off.

## What it does
1. Goes to your Home Screen, screenshots it, and reads the **Batteries widget**.
2. Ignores the first percentage (the iPhone) and checks the rest against **30%**.
3. If something is low, or the widget couldn't be read, it asks:
   **Charging now / Remind me in 30 min / Skip**.
   Otherwise it shows `All good 🔋 85%, 70%…`.
4. **Charging now** asks what you put on the pad, then creates a **Reminder** that
   alerts you after **60 min** (Watch) or **90 min** (if AirPods are included).
5. **Remind me in 30 min** creates a reminder whose note links back to this shortcut.

## Before you start
- Add the **Batteries widget, large size**, to the **first Home Screen page**.
- Check that the **iPhone is listed first** in the widget.

## Install
iOS only imports **signed** shortcut files, so the file is signed on your Mac first.

1. Download `Charge Check.shortcut` from this folder to your Mac.
2. In Terminal, in the folder you downloaded it to:
   ```bash
   shortcuts sign --mode anyone --input "Charge Check.shortcut" --output "Charge Check (signed).shortcut"
   ```
3. AirDrop `Charge Check (signed).shortcut` to your iPhone → tap **Add Shortcut**.
4. Run it once from the Shortcuts app and allow the permissions it asks for
   (Reminders, Notifications).

## Schedule it 3× a day
Automations can't be shipped in a file, so set these up once:

Shortcuts → **Automation** → **+** → **Time of Day** (do this 3 times, e.g. 8 AM, 2 PM, 9 PM)
- Repeat **Daily**
- **Run After Confirmation**
- Action: **Run Shortcut** → **Charge Check**

At each time, tap the notification. iOS can't screenshot a locked phone, so one tap is needed.

## Check after importing
This file was generated, not exported from an iPhone, so look over these steps once:
- **Add New Reminder** steps: the alert should be set to the *Adjusted Date*.
- **If … is less than 30**: change `30` to your own low level.
- **Number 90 / Number 60**: charge-time estimates, adjust to your devices.

To test the menu, temporarily set the low level to `100`.

## If the import fails
Build it by hand from the step list in `build_shortcut.py` (it reads top to
bottom in the same order as the actions), or change the settings at the top of
the script and rebuild:
```bash
python3 build_shortcut.py
```
