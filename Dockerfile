# Hub-Bild mit diesem Plugin: der Hub der Distribution plus dieses Paket und seine Skills.
#
# Bauen (Basisbild aus der eigenen Registry, gebaut von der CI von fyos-os):
#   docker build --build-arg HUB_BILD=<registry>/fyos-os/hub:main -t mein-hub:main .
# Die Vorgabe zeigt auf eine Beispieladresse, die sich nie auflösen lässt.
#
# Installiert wird mit uv statt pip. Braucht das Paket weitere Pakete aus einem eigenen Paketindex, steht dessen
# Adresse als Bau-Argument FYOS_INDEX_URL VOR PyPI:
#   docker build --build-arg HUB_BILD=<registry>/fyos-os/hub:main \
#     --build-arg FYOS_INDEX_URL=https://registry.example.com/api/packages/org/pypi/simple -t mein-hub:main .
# uv fragt die Indizes der Reihe nach (--index-strategy first-index) und nimmt ein Paket nur aus dem ersten Index, der
# es führt. Ein Paket gleichen Namens auf PyPI kann das eigene so nicht verdrängen; pip mit --extra-index-url nähme
# die höchste Version aus allen Indizes (Dependency Confusion).
ARG HUB_BILD=registry.example.com/fyos/fyos-os/hub:main
FROM ${HUB_BILD}

ARG FYOS_INDEX_URL=""

USER root
# uv aus dem offiziellen Bild, in fester Version (dieselbe wie im Hub-Bild von fyos-os).
COPY --from=ghcr.io/astral-sh/uv:0.12.8 /uv /uvx /bin/
COPY . /tmp/plugin
# Werkzeuge, App, Katalogeintrag und Skills reisen im Paket; der Hub findet sie über die Entry-Points.
RUN uv pip install --system --no-cache --index-strategy first-index \
      ${FYOS_INDEX_URL:+--index "$FYOS_INDEX_URL"} /tmp/plugin && rm -rf /tmp/plugin

USER fyos
