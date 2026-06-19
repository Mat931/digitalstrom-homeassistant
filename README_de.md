# digitalSTROM-Integration für Home Assistant
Mit dieser Integration können Sie Ihren digitalSTROM-Server (dSS) mit Home Assistant verbinden.

## Installation über HACS
1. Installieren Sie [HACS](https://hacs.xyz/).
2. Mit dem folgenden MY-Button können Sie `digitalstrom-homeassistant` als "Custom Repository" hinzufügen:

    [![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Mat931&repository=digitalstrom-homeassistant&category=integration)

   Alternativ können Sie dieses Repository (`https://github.com/Mat931/digitalstrom-homeassistant`) manuell als "Custom Repository" zu HACS hinzufügen und den Typ `Integration` auswählen.
4. Laden Sie die digitalSTROM-Integration mit Hilfe von HACS herunter.
5. Starten Sie Home Assistant neu.

## Manuelle Installation
1. Kopieren Sie den `custom_components`-Ordner aus diesem Repository in Ihre Home Assistant-Installation.
2. Starten Sie Home Assistant neu.

## Einrichtung
1. Mit dem folgenden MY-Button können Sie die Einrichtung der digitalSTROM-Integration starten:
   
   [![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=digitalstrom)

   Alternativ können Sie `Einstellungen`, `Geräte & Dienste` aufrufen. Diese Integration unterstützt "Auto Discovery" und sollte Ihre dSS-Instanz automatisch entdecken.
2. Geben Sie Nutzername und Passwort des digitalSTROM-Servers ein.
3. Wenn Sie ein selbst-signiertes Zertifikat auf dem dSS nutzen müssen Sie dessen [SHA-256 Fingerabdruck herausfinden](https://github.com/Mat931/digitalstrom-homeassistant/blob/main/certificate_fingerprint_de.md). Dieser Fingerabdruck wird genutzt, um die Identität des Servers zu bestätigen.
4. Im folgenden Schritt können Sie prüfen, ob Ihren digitalSTROM-Geräten die richtigen Zonen zugeordnet wurden.

## Verwendung von digitalSTROM Szenen-Events

Diese Integration stellt Szenenwechsel aus digitalSTROM als Home Assistant Events zur Verfügung.

Immer wenn eine Szene in digitalSTROM ausgelöst wird (z. B. über einen physischen Taster oder eine Automation), wird ein entsprechendes Event im Home Assistant Event-Bus erzeugt.

Events sind die Grundlage von Home Assistant: Immer wenn etwas passiert, wird ein Event erzeugt, das wiederum Automationen auslösen kann. :contentReference[oaicite:0]{index=0}

### Event-Typ

```yaml
digitalstrom_scene
```

### Event-Daten

```yaml
scene: <Szenen-ID>
zone: <Zonen-ID>
group: <Gruppen-ID>
```

### Beispiel-Event

```yaml
event_type: digitalstrom_scene
data:
  scene: 17
  zone: 61667
  group: 1
origin: LOCAL
```

### Events anzeigen (Debugging)

1. Öffne **Entwicklerwerkzeuge → Ereignisse** in Home Assistant  
2. Trage ein:

```yaml
digitalstrom_scene
```

3. Klicke auf **„Zuhören starten“**  
4. Löse eine Szene über digitalSTROM aus  
5. Beobachte das eingehende Event  

### Szenen-, Zonen- und Gruppen-IDs herausfinden

Die IDs stammen direkt aus digitalSTROM und entsprechen nicht zwingend den Anzeigenamen wie „Stimmung 1“ oder „Stimmung 2“.

So findest du die richtigen Werte:

- Szene in digitalSTROM auslösen  
- Event in den Entwicklerwerkzeugen beobachten  
- Werte für `scene`, `zone` und `group` notieren  

### Beispiel: Automation für eine bestimmte Szene

```yaml
alias: Beispiel - Reagiere auf eine bestimmte digitalSTROM Szene
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

### Beispiel: Unterschiedliches Verhalten je nach Szene

```yaml
alias: Beispiel - Szenenabhängige Steuerung
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

### Hinweise

- Für jede Szenenänderung in digitalSTROM wird ein Event erzeugt  
- Verwende `scene`, `zone` und `group`, um Events zuverlässig zu filtern  
- Mehrere Trigger können in einer Automation kombiniert werden  
- Diese Funktion ermöglicht es, physische digitalSTROM Eingaben direkt in Home Assistant Automationen zu nutzen