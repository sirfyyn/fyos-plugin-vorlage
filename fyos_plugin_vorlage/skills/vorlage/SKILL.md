---
name: vorlage
description: Laden, wenn der Besitzer eine Begrüßung oder eine kurze Notiz der Vorlage-App möchte. Wann welches Werkzeug, was ein Trockenlauf ist und was nie getan wird.
ausloeser: Notiz merken, Notiz setzen, Begrüßung, Vorlage-App
fuer: [agent]
---

# Vorlage: Begrüßung und Notiz

Dieser Skill gehört zum Plugin `fyos-plugin-vorlage` und zeigt, wie ein Plugin dem Agenten Wissen mitliefert.
Ein Skill sagt, **wann** und **in welcher Reihenfolge** man Werkzeuge nutzt und wo die Fallen liegen. Die
Werkzeuge selbst beschreibt der Hub.

## Wann

- Der Besitzer will begrüßt werden oder wissen, was in der Notiz steht: `vorlage.hallo`.
- Der Besitzer will sich etwas merken: `vorlage.notiz_setzen`.

## Ablauf

1. Suche das Werkzeug über den Hub (`hub__search_tools` mit »notiz«), lies bei Bedarf sein Schema.
2. Lies zuerst mit `vorlage.hallo`, was gerade in der Notiz steht. `notiz_setzen` **ersetzt** die Notiz.
3. Sage dem Besitzer vor dem Schreiben, was überschrieben wird, wenn schon eine Notiz da ist.
4. Rufe `vorlage.notiz_setzen` zuerst mit `__dry_run__: true` auf: Du bekommst den Plan, ohne dass etwas geändert wird.
5. Schreibe erst danach, mit `bestaetigt: true`. Das Werkzeug ändert ohne `bestaetigt` nichts und antwortet mit einem
   Fehler. Setze es nur, wenn der Besitzer die Notiz so gewollt hat: Sein Auftrag »merk dir …« genügt, solange nichts
   überschrieben wird; ersetzt du eine vorhandene Notiz, frage vorher.
6. Melde knapp: »Notiz gespeichert« und zeige auf Wunsch die App (`In FYOS öffnen`-Link aus dem Ergebnis).

## Regeln

- Höchstens so viele Zeichen, wie `notiz_max` im Ergebnis von `vorlage.hallo` nennt. Kürze nicht still, frage nach.
- Schreibe keine Zugangsdaten, Passwörter oder Schlüssel in die Notiz. Sie liegt unverschlüsselt im Speicher des Hubs.
- Diese Notiz ist kein Gedächtnis des Agenten. Für Merkenswertes über den Besitzer gilt das Gedächtnis des Agenten,
  nicht die Vorlage.
