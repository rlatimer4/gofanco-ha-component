# Gofanco/WebUI HDMI Matrix Switcher for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/hacs/integration)
![Version](https://img.shields.io/github/v/release/rlatimer4/gofanco-ha-component)

A custom component to integrate and control Gofanco (and other generic) 4x4 HDMI Matrix Switchers with a web interface into Home Assistant.

This integration polls the device to get the current status of all inputs and outputs and creates `select` entities to allow for easy switching from your dashboard. It is designed to be robust and handle the non-standard, `HTTP/0.9`-style API responses that these devices often use.

![Lovelace Card Example](https://placehold.co/600x200/2d3748/ffffff?text=Entities+Card+Screenshot)

## Features

- **Local Polling:** All communication happens on your local network. No cloud required.
- **Auto-Discovery (via Config Flow):** Set up the integration entirely through the Home Assistant UI.
- **Four `select` Entities:** Creates a dropdown selector for each of the four outputs.
- **Dynamic Naming:** Uses the friendly names for inputs and outputs that you have configured in the device's web UI.
- **Robust Communication:** Specifically designed to handle the quirky API of these devices.

---

## Installation

### Method 1: HACS (Home Assistant Community Store) - Recommended

1.  Ensure you have [HACS](https://hacs.xyz/) installed.
2.  Go to HACS > Integrations > and click the three dots in the top right, then **Custom Repositories**.
3.  Add the URL to this repository (`https://github.com/rlatimer4/gofanco-ha-component`) and select the category **Integration**.
4.  The "HDMI Matrix Switcher" integration will now be shown. Click **Install**.
5.  Restart Home Assistant.

### Method 2: Manual Installation

1.  Download the latest release from the [Releases page](https://github.com/rlatimer4/gofanco-ha-component/releases).
2.  Unzip the file and copy the `hdmi_matrix_switcher` folder into your Home Assistant `custom_components` directory. Your final directory structure should look like this:
    ```
    └── ...
    └── custom_components/
        └── hdmi_matrix_switcher/
            ├── __init__.py
            ├── select.py
            ├── manifest.json
            ├── coordinator.py
            ├── config_flow.py
            └── const.py
    ```
3.  Restart Home Assistant.

---

## Configuration

Once installed, you can add the integration to Home Assistant through the UI.

1.  Go to **Settings** > **Devices & Services**.
2.  Click the **+ Add Integration** button in the bottom right.
3.  Search for "**HDMI Matrix Switcher**" and click on it.
4.  You will be prompted to enter the **Host** (IP Address) of your HDMI matrix.
    ![Config Flow Screenshot](https://placehold.co/400x200/2d3748/ffffff?text=Config+Flow+UI)
5.  Click **Submit**.

The integration will be added, and you will now have a new device with four `select` entities.

---

## Usage

The easiest way to control your matrix is by adding the `select` entities to your dashboard using an Entities card.

1.  Go to your dashboard and click the three dots > **Edit Dashboard**.
2.  Click **+ Add Card** and choose the **Entities** card.
3.  Add the four new entities to the card:
    - `select.den_tv` (or whatever you named Output 1)
    - `select.basement_tv` (or whatever you named Output 2)
    - `select.hdmi_output_3`
    - `select.hdmi_output_4`
4.  Click **Save**. You will now have dropdowns to control each output.

---

## Troubleshooting

This integration uses a `command_line` approach with `curl` to communicate with the device. This is intentional and necessary because these specific HDMI matrix devices use a non-standard, outdated `HTTP/0.9` protocol for their API.

Modern web libraries, including those used by Home Assistant's standard `rest` components, will reject these responses as invalid. Using `curl` with the `--http0.9` flag allows us to reliably communicate with the device. If you are having issues, it is likely a network problem between your Home Assistant instance and the matrix.

## Contributing

Contributions are welcome! If you have an idea for an improvement or have found a bug, please open an issue or submit a pull request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
