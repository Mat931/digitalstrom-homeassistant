# Debug-Log abrufen

Klicken Sie auf die "MY"-Schaltfläche unten, um die Übersichtsseite der digitalSTROM-Integration zu öffnen, und dann auf "Debug-Protokoll aktivieren". Solange das Debug-Protokoll aktiv ist, werden die Debug-Meldungen dieser Integration gesammelt. Verwenden Sie das Dreipunktmenü rechts, um die Integration neu zu laden und warten Sie, bis der Fehler, den Sie melden, ausgelöst wurde. Klicken Sie dann auf "Debug-Protokoll deaktivieren", dies lädt eine Datei mit den gesammelten Log-Meldungen herunter. Senden Sie diese Datei an die Entwickler der Integration.

[![Open your Home Assistant instance and show an integration.](https://my.home-assistant.io/badges/integration.svg)](https://my.home-assistant.io/redirect/integration/?domain=digitalstrom)


# Installieren der neuesten Entwicklungsversion

Wenn Ihre HACS-Integration-Updates in den Home Assistant-Einstellungen neben den anderen Updates angezeigt werden, haben Sie die neue Version von HACS. Andernfalls müssen Sie den Schritten für die alte HACS-Version folgen.

## Mit dem neuen HACS

[![Open your Home Assistant instance and show your service developer tools.](https://my.home-assistant.io/badges/developer_services.svg)](https://my.home-assistant.io/redirect/developer_services/)

Um die neueste Entwicklungsversion der digitalSTROM-Integration zu installieren, verwenden Sie die "MY"-Schaltfläche oben, um die Entwicklerwerkzeuge -> Aktionen zu öffnen. Klicken Sie dann auf "Zum YAML-Modus", fügen Sie den folgenden Code ein und führen Sie die Aktion aus. Wenn die Installation abgeschlossen ist, sehen Sie eine neue Reparaturmeldung in den [Home Assistant-Einstellungen](https://my.home-assistant.io/redirect/config/), die auffordert, Home Assistant neu zu starten. Starten Sie neu, um zur neuen Version zu wechseln. Wenn Sie mit dem Testen der Entwicklungsversion fertig sind, können Sie die letzte stabile Version in den Home Assistant-Einstellungen installieren.

```yaml
action: update.install
target:
  entity_id: update.digitalstrom_update
data:
  version: main
```
## Mit dem alten HACS

Klicken Sie auf die "MY"-Schaltfläche unten, um die Integrationsseite in HACS zu öffnen, und verwenden Sie dann das Dreipunktmenü oben rechts, um die Integration erneut herunterzuladen. Wählen Sie "main" als Version aus und klicken Sie auf "Herunterladen". Starten Sie Home Assistant neu, um zur neuen Version zu wechseln. Wenn Sie mit dem Testen der Entwicklungsversion fertig sind, können Sie dieselbe Methode verwenden, um die letzte stabile Version wieder zu installieren.


[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Mat931&repository=digitalstrom-homeassistant&category=integration)
