# Getting a debug log

Click the MY button below to open the overview page of the digitalSTROM integration, then click 'Enable debug logging'. While debug logging is active, the debug messages from this integration are collected. Use the three-dot menu on the right to reload the integration and wait until the error you're reporting was triggered. Then click 'Disable debug logging', this will download a file with the collected log messages. Send this file to the integration's maintainers.

[![Open your Home Assistant instance and show an integration.](https://my.home-assistant.io/badges/integration.svg)](https://my.home-assistant.io/redirect/integration/?domain=digitalstrom)


# Installing the latest development version

If your HACS integration updates appear in the Home Assistant settings next to the other updates then you have the new version of HACS. Otherwise you need to follow the steps for the old HACS version.

## With the new HACS

[![Open your Home Assistant instance and show your service developer tools.](https://my.home-assistant.io/badges/developer_services.svg)](https://my.home-assistant.io/redirect/developer_services/)

To install the latest development version of the digitalSTROM integration use the MY button above to open the developer tools -> services. Then click 'Go to YAML mode', paste the code below and call the service. When the installation is completed you will see a new repair message in the [Home Assistant settings](https://my.home-assistant.io/redirect/config/) telling to restart Home Assistant. Restart to switch to the new version. When you are done with testing the development version you can install the latest stable version in the Home Assistant settings.

```yaml
service: update.install
target:
  entity_id: update.digitalstrom_update
data:
  version: main
```

## With the old HACS

Click the MY button below to open the integration page in HACS, then use the three dot menu on the top right to 'Redownload' the integration. Select 'main' as the version and click 'Download'. Restart Home Assistant to switch to the new version. When you are done with testing the development version you can use the same method to install the latest stable version again.

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Mat931&repository=digitalstrom-homeassistant&category=integration)

