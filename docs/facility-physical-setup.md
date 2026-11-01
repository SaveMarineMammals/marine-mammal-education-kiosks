# Facility physical setup — NovoTouch LK7530i

Physical install for education kiosks on **Vivitek NovoTouch LK7530i** collaborative
flat panels. Goals:

1. Support **dynamic Xibo content** today (Glance & Match and other layouts).
2. Stay ready for **interactive touch** later without remounting compute.
3. Require the **least new hardware** beyond the panel and a Raspberry Pi kit.
4. Keep a **flush wall mount**: only the included TV bracket attaches to the wall
   (no separate wall shelves, Pi boxes, or mini-PC plates).

Software bootstrap for the Pi lives in [`ops/players/README.md`](../ops/players/README.md).
Networking and hostnames: [`ops/networking/README.md`](../ops/networking/README.md).
Canvas size: [`framework/standards/resolution.md`](../framework/standards/resolution.md)
(**1920×1080** landscape).

## Display

| Spec | Value |
| --- | --- |
| Model | Vivitek NovoTouch **LK7530i** |
| Size / native resolution | 75", 4K UHD (3840×2160), 60 Hz |
| Orientation | **Landscape only** (no portrait) |
| Touch | Infrared; up to 20 touch / 10 writing points; HID over USB |
| Depth / weight (approx.) | ~100 mm / ~60 kg |
| Included wall mount | **WIB9060A** (150 kg rating) |
| Included Android OPS | VKA05 (Slot 1) — panel features only; **not** the Xibo host |
| Optional Windows OPS | VKW21 (Slot 2) — deferred; not part of this primary path |

Manufacturer references:

- [NovoTouch product page](https://www.vivitekusa.com/productdetail/NovoTouch/)
- [User manual (LK6530i / LK7530i / LK8630i)](https://support.launchnovo.com/wp-content/uploads/2020/03/NovoTouch_LK6530i_LK7530i_LK8630i_UM_English_V5-1.pdf)

## Architecture

```text
  Wall (power + Ethernet drop)
        |
        +-- WIB9060A frame only (no other wall hardware)
        |
        v
  LK7530i panel  <---- HDMI ----  Raspberry Pi 5
        ^                         (aluminium VESA case
        |                          on display rear / mount brackets)
        +---- USB touch (USB-B) --+
                                  |
                                  +-- Ethernet --> Xibo CMS (XMDS / XMR)
```

- **Day-1 video:** Pi drives one HDMI input; panel source locked to that input;
  layouts stay **1920×1080**.
- **Future touch:** USB touch is wired at install. IR touch is Linux HID–compatible;
  interactive Xibo layouts can use it later without opening the wall.
- **Android OPS (VKA05):** May remain installed for NovoConnect / panel UI. Do **not**
  run Xibo on it — the module ships with **Android 6.0**, which cannot run current
  Xibo for Android v4 (requires Android 7+).
- **Windows OPS:** Not required for this path (would be extra hardware per panel).

### Player software note

Official **Xibo for Linux** is **x86-64 only** and is **not** supported on Raspberry Pi.
Fleet Pis use **Raspberry Pi OS (64-bit)** and the community **Arexibo** player
(aarch64). That combination is **community-supported**, not Xibo Signage helpdesk–
supported. Ephemeral QA in Docker continues to use the official Linux player on x86;
see [`ops/qa/`](../ops/qa/).

## Bill of materials (per kiosk)

| Item | Specification |
| --- | --- |
| Board | **Raspberry Pi 5, 8 GB** (4 GB OK for static Glance & Match; 8 GB preferred for future interactive HTML) |
| Storage | **128 GB** (or larger) microSD **A2** for OS + offline media cache |
| Cooling | **Official Raspberry Pi Active Cooler** |
| Enclosure | **Aluminium VESA Raspberry Pi 5 case** with **75 mm VESA wings**, ~**90 × 84 × 34 mm**, black; USB-C, Micro-HDMI, USB, Ethernet, and microSD accessible. Example SKU class: The Pi Hut [Aluminium VESA Raspberry Pi 5 Case](https://thepihut.com/products/aluminium-vesa-raspberry-pi-5-case) / Cool Kit Pack (case + Active Cooler + 75 mm wings) |
| Power | **Official 27 W USB-C PSU** (5 V / 5 A); right-angle USB-C cable if needed for cavity fit |
| Video cable | **0.3–0.5 m** Micro-HDMI (Pi) → HDMI (panel); use HDMI 2.0 or an HDMI 1.4 input on the LK7530i |
| Touch cable | **0.3–0.5 m** USB-A (Pi) → **Touch Port** USB-B on the panel (Touch Port 1 or 2) |
| Network | Short **Cat6** patch to facility LAN (Ethernet preferred over Wi-Fi) |
| Fasteners | **M4** screws/nuts to share display or mount-bracket holes with the 75 mm wings; cable ties and adhesive clips for strain relief |

**Optional:** USB-C power extension; HDMI ferrite if interference appears; USB keyboard
for commissioning only (remove afterward).

Facility infrastructure (shared, not per-Pi SKUs): in-wall or recessed **AC duplex**
and **Ethernet** behind the panel footprint so bricks and cables stay in the cavity.

## Mounting (clean wall rule)

Only the **WIB9060A** wall frame gets anchors in the wall. The Pi attaches to the
**display rear** or **display-side mount brackets**.

1. Have a **certified installer** mount the WIB9060A frame (landscape only; respect
   load rating and local code). Place a protective cloth under the panel when laying
   it face-down to fit brackets.
2. Install the two WIB9060A brackets on the LK7530i rear with the supplied bracket
   screws (Vivitek manual, “Installing the Wall Mount”).
3. Mount the Pi aluminium case with its **75 mm VESA wings**:
   - Prefer sharing two existing M4 fasteners or bracket holes **75 mm apart**, or
     bolting the wings to a WIB9060A **display bracket** rail.
   - Large-panel VESA is often **600×400**. If there is no native 75 mm pair, use a
     small adapter that clamps or bolts to the **display brackets** — **never** add
     a second wall plate for the Pi.
4. Hang the panel on the wall frame and secure with the WIB9060A frame screws.
5. Confirm the stack seats fully and the panel sits flush. Case depth (~34 mm) plus
   short cables must fit the mount standoff cavity.

## Cabling

Route everything in the cavity behind the panel.

| From | To | Notes |
| --- | --- | --- |
| Wall AC | Panel power inlet + Pi 27 W PSU | Prefer a duplex recessed behind the panel |
| Wall Ethernet | **Pi RJ45** | Prefer DHCP reservation by Pi MAC ([`ops/networking`](../ops/networking/README.md)). Do not rely on the panel’s disabled bottom LAN jack for the player. |
| Pi Micro-HDMI | Panel **HDMI** in | Lock panel input to this source |
| Pi USB-A | Panel **Touch Port 1 or 2** (USB-B) | Wire at day-1 even if content is non-interactive |

Leave the VKA05 antenna clear if that OPS module stays installed; keep Pi and cable
bundles from blocking OPS slot access for service.

## Software image and per-kiosk config

Fleet Pis use the **golden image** and **Kiosk config** pipelines — see
[`ops/players/image/`](../ops/players/image/).

1. Flash an approved `player-image-v*` Release (or soak artifact) `.img.xz`.
2. Generate config (Actions → **Kiosk config**, or
   `python3 ops/players/image/generate_kiosk_config.py …`).
3. Copy `kiosk.conf` to `/boot/firmware/kiosk.conf` on the SD boot partition.
4. Power on; first-boot applies hostname and Arexibo CMS settings.
5. Authorize the display in CMS into the location display group.

Player auth uses the shared **CMS Key** in `kiosk.conf` (not client certificates).

## Display and OS configuration

**Panel**

- Input: fixed to the Pi’s HDMI; disable auto source switching and NovoConnect
  auto-launch for kiosk duty.
- Orientation: landscape only.
- Brightness: avoid maximum for long periods (panel lifetime).

**Pi (golden image defaults)**

- OS/player: baked by [`ops/players/image/`](../ops/players/image/) (Lite + Arexibo).
- HDMI forced toward **1920×1080@60** — do not drive full 4K for current layouts.
- Hostname from `kiosk.conf`: `kiosk-<location>-<nn>`; CMS display name matches.
- Assign a **location/role display group** (`lobby`, not exhibit names).
- Touch: after USB connect, confirm the HID device appears (`libinput` / `evdev`);
  leave the cable connected for future interactive layouts.

## Commissioning checklist

- [ ] WIB9060A installed; panel landscape and flush; no extra wall boxes
- [ ] Pi in aluminium VESA case attached to display rear or mount brackets only
- [ ] HDMI, USB touch, Ethernet, and power dressed in the rear cavity
- [ ] Approved golden image flashed; generated `kiosk.conf` on `/boot/firmware/`
- [ ] Hostname + DHCP reservation set; CMS reachable
- [ ] Arexibo registered and authorized
- [ ] Display group assigned; test layout plays at 1920×1080
- [ ] Touch HID visible to the OS (even if layouts are non-interactive)
- [ ] `ops/scripts/bootstrap-check.sh` passes (optional)
- [ ] Reboot persistence confirmed; offline cache spot-check
  ([`ops/runbooks/offline-cache.md`](../ops/runbooks/offline-cache.md))
- [ ] Private inventory updated (MAC, hostname, location, display group)

## Future interactivity

No hardware remount is required to enable touch content:

1. Keep the USB touch cable connected to the Pi.
2. Author interactive layouts / actions in Xibo (large hit targets; idle return to
   attract — see [`framework/standards/accessibility.md`](../framework/standards/accessibility.md)).
3. Validate on one physical kiosk before rolling out to a display group.

## Non-goals

- Using the **Android VKA05** as the Xibo player
- Buying **Windows OPS** modules for the primary fleet (deferred alternate)
- Separate wall-mounted Pi enclosures, shelves, or mini-PC plates
- Portrait mounts (unsupported on LK7530i; would need a different panel and template)
- Driving **4K** layouts while the design canvas remains 1080p
