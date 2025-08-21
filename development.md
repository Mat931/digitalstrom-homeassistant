# Getting a debug log

Click the MY button below to open the overview page of the digitalSTROM integration, then click the three-dot menu on the top right and select 'Enable debug logging'.

While debug logging is active, the debug messages from this integration are collected.

Use the three-dot menu to the right of the integration entry to reload the integration and wait until the error you're reporting was triggered.

Then click 'Disable' to disable debug logging, this will download a file with the collected log messages. Send this file to the integration's maintainer(s).

[![Open your Home Assistant instance and show an integration.](https://my.home-assistant.io/badges/integration.svg)](https://my.home-assistant.io/redirect/integration/?domain=digitalstrom)


# Installing the latest development version

[![Open your Home Assistant instance and show your action developer tools.](https://my.home-assistant.io/badges/developer_services.svg)](https://my.home-assistant.io/redirect/developer_services/)

To install the latest development version of the digitalSTROM integration use the MY button above to open the developer tools -> actions.

Then click 'Go to YAML mode', paste the code below and perform the action. 

```yaml
action: update.install
target:
  entity_id: update.digitalstrom_update
data:
  version: main
```

When the installation is completed you will see a new repair message in the [Home Assistant settings](https://my.home-assistant.io/redirect/config/) telling to restart Home Assistant. Restart to switch to the new version.

After the successful installation of the development version a new update for the digitalSTROM integration will appear in the Home Assistant settings.

Don't click install until you are done with testing the development version because that will install the older stable version again.

