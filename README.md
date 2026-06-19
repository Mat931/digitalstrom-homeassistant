# digitalSTROM integration for Home Assistant
This integration allows you to connect your digitalSTROM server (dSS) to Home Assistant.

[🇩🇪 Deutsche Übersetzung](https://github.com/Mat931/digitalstrom-homeassistant/blob/main/README_de.md)

[Join the discord server](https://discord.gg/uTDweuNnHq)

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

## Using digitalSTROM scene events

This integration exposes digitalSTROM scene changes as Home Assistant events.

Whenever a scene is triggered in digitalSTROM (for example via a physical switch or automation), a corresponding event is fired on the Home Assistant event bus.

Home Assistant is built around events — every action in the system produces an event, which can be used to trigger automations. :contentReference[oaicite:0]{index=0}

### Event type

```yaml
digitalstrom_scene
```

### Event data

```yaml
scene: <scene id>
zone: <zone id>
group: <group id>
```

### Example event

```yaml
event_type: digitalstrom_scene
data:
  scene: 17
  zone: 61667
  group: 1
origin: LOCAL
```

### How to inspect events

1. Open **Developer Tools → Events** in Home Assistant  
2. Enter:

```yaml
digitalstrom_scene
```

3. Click **Start listening**  
4. Trigger a scene via digitalSTROM  
5. Observe the incoming event  

Home Assistant allows automations to be triggered directly from events and optionally filtered by their data. :contentReference[oaicite:1]{index=1}

### Finding scene, zone and group IDs

The IDs used in the event data are provided by digitalSTROM and may not match the names shown in the UI.

To identify them:

- Trigger a scene in digitalSTROM
- Observe the event in Developer Tools
- Note the values of `scene`, `zone`, and `group`

### Example: Trigger automation on a specific scene

```yaml
alias: Example - react to a specific digitalSTROM scene
triggers:
  - trigger: event
    event_type: digitalstrom_scene
    event_data:
      scene: 17
      zone: 61667
      group: 1
actions:
  - action: switch.turn_on
    target:
      entity_id: switch.example
mode: single
```

### Example: React differently depending on the scene

```yaml
alias: Example - scene-dependent behavior
triggers:
  - trigger: event
    event_type: digitalstrom_scene
    event_data:
      zone: 61667
      group: 1

actions:
  - choose:
      - conditions:
          - condition: template
            value_template: "{{ trigger.event.data.scene | int == 17 }}"
        sequence:
          - action: switch.turn_on
            target:
              entity_id: switch.example
    default:
      - action: switch.turn_off
        target:
          entity_id: switch.example

mode: single
```

### Notes

- Events are emitted for every scene change in digitalSTROM
- Use `scene`, `zone`, and `group` to filter events reliably
- Multiple triggers can be combined in a single automation
- This feature enables seamless integration of digitalSTROM inputs into Home Assistant automations