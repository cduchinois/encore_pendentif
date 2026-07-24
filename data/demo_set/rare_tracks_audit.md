# Anti-Shazam audit — before the 25th

Le duel : un juré Shazame en live (service online) et **échoue** ; Encore le reconnaît **offline** via le custom catalog signé. Donc chaque morceau ici doit être (1) **signé** dans `data/catalog` (recognizable par Encore) et (2) **inconnu de Shazam online**. On ne garde que les échecs Shazam confirmés.

Statut : `confirmé` = testé live et Shazam échoue · `à tester` = à Shazamer sur place le jour J.

| track | dans le catalogue (signé) | Shazam online | garder pour le duel ? |
|---|---|---|---|
| Spiral Tribe Sound System — Forward The Revolution | ✅ (id 16816, ajouté depuis le Synology) | inconnu (confirmé par Mathieu) — **à re-confirmer live** | **oui — finale du set** |
| Psychick Warriors Ov Gaia — Exit 23 (Drum Club Remix 1) | ✅ | à tester | candidat (rave/free-party obscur) |
| The Drum Club — Follow The Sun | ✅ | à tester | candidat |
| The Justified Ancients Of Mu Mu — It's Grim Up North | ✅ | à tester | candidat (KLF, souvent mal indexé) |
| Paperclip People — Throw (Slam's RTM Remix) | ✅ | à tester | candidat (remix rare) |

## Slot « inconnu » (carte Gemma) — distinct du duel

Le duel (ci-dessus) : Shazam échoue, **Encore gagne offline** (morceau signé). Le slot Gemma, lui, c'est un morceau que **rien** ne reconnaît — pas même le catalogue Encore — donc l'échelle rate entièrement et **Gemma le décrit** (genre, description, voix, BPM injecté par DSP).

- **Morceau** : un inédit de Mathieu, jamais publié (`Dub techno 1.m4a`, AAC 44,1 kHz, 5:11, sans métadonnées propres — normal, c'est le mystère).
- **NON signé, hors des dossiers indexés** — c'est indispensable pour que la reconnaissance rate :
  - clé : `encore_demo/unreleased/Dub techno 1.m4a` (à l'écart de `MUSIC/`)
  - projet : `data/samples/unreleased/` (gitignoré)
- **BPM (DSP, librosa) : ~129** — la ground-truth à injecter dans la carte Gemma (le contrat `id_card.schema.json` interdit à Gemma de le deviner). L'app le recalcule en direct sur le clip ; ~129 sert à vérifier que l'ID card est juste. Durée : 311 s.
