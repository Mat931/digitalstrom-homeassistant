# Debug-Log abrufen

Klicken Sie auf die "MY"-Schaltfläche unten, um die Übersichtsseite der digitalSTROM-Integration zu öffnen, öffnen Sie das Dreipunktmenü oben rechts und wählen Sie "Debug-Protokoll aktivieren".

Solange das Debug-Protokoll aktiv ist, werden die Debug-Meldungen dieser Integration gesammelt.

Verwenden Sie das Dreipunktmenü rechts neben dem Eintrag der Integration, um die Integration neu zu laden und warten Sie, bis der Fehler, den Sie melden, ausgelöst wurde.

Klicken Sie dann auf "Deaktivieren" um das Debug-Protokoll zu deaktivieren, dies lädt eine Datei mit den gesammelten Log-Meldungen herunter. Senden Sie diese Datei an die Entwickler der Integration.

[![Open your Home Assistant instance and show an integration.](https://my.home-assistant.io/badges/integration.svg)](https://my.home-assistant.io/redirect/integration/?domain=digitalstrom)


# Installieren der neuesten Entwicklungsversion

[![Open your Home Assistant instance and show your action developer tools.](https://my.home-assistant.io/badges/developer_services.svg)](https://my.home-assistant.io/redirect/developer_services/)

Um die neueste Entwicklungsversion der digitalSTROM-Integration zu installieren, verwenden Sie die "MY"-Schaltfläche oben, um die Entwicklerwerkzeuge -> Aktionen zu öffnen.

Klicken Sie dann auf "Zum YAML-Modus", fügen Sie den folgenden Code ein und führen Sie die Aktion aus. 

```yaml
action: update.install
target:
  entity_id: update.digitalstrom_update
data:
  version: main
```

Wenn die Installation abgeschlossen ist, sehen Sie eine neue Reparaturmeldung in den [Home Assistant-Einstellungen](https://my.home-assistant.io/redirect/config/), die auffordert, Home Assistant neu zu starten. Starten Sie neu, um zur neuen Version zu wechseln.

Nach der erfolgreichen Installation der Entwicklungsversion wird in den Home Assistant Einstellungen ein neues Update für die digitalSTROM-Integration angezeigt.

Klicken Sie noch nicht auf Installieren bis Sie mit dem Testen der Entwicklungsversion fertig sind, weil damit wieder die ältere stabile Version installiert wird.

