# digitalSTROM integration for Home Assistant
This integration allows you to connect your digitalSTROM server (dSS) to Home Assistant.

[🇩🇪 Deutsche Übersetzung](https://github.com/Mat931/digitalstrom-homeassistant/blob/main/README_de.md)

## Installation using HACS
1. Download and install [HACS](https://hacs.xyz/).
2. Click this MY button to add `digitalstrom-homeassistant` as a custom repository:

    [![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Mat931&repository=digitalstrom-homeassistant&category=integration)

   Alternatively you can manually add this repository (`https://github.com/Mat931/digitalstrom-homeassistant`) as a custom repository in HACS and select the type `Integration`.
4. Download the digitalSTROM integration using HACS.
5. Restart Home Assistant.

## Manual Installation
1. Copy the `custom_components` folder from this repository into your Home Assistant installation.
2. Restart Home Assistant.

## Setup
1. Click the MY button below to setup the digitalSTROM integration.
   
   [![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=digitalstrom)

   Alternatively you can navigate to `Settings`, `Devices & services`. This integration supports auto discovery and should automatically find your dSS instance.
2. Enter your username and password of your dSS.
3. If you are using a self-signed certificate on the dSS you need to [find out its SHA-256 fingerprint](https://github.com/Mat931/digitalstrom-homeassistant/blob/main/certificate_fingerprint.md). This fingerprint is used to verify the identity of the server.
4. In the next step you can check if the correct areas got assigned to your digitalSTROM devices.
