# Anti-Shazam audit — before the 25th

Le duel : un juré Shazame en live (service online) et **échoue** ; Encore le reconnaît **offline** via le custom catalog signé. Donc chaque morceau ici doit être (1) **signé** dans `data/catalog` (recognizable par Encore) et (2) **inconnu de Shazam online**. On ne garde que les échecs Shazam confirmés.

Test live Shazam — **2026-07-25** (Mathieu, au casque).

| track | signé (Encore) | Shazam online | duel ? |
|---|---|---|---|
| The Drum Club — Follow The Sun | ✅ | **échoue** (confirmé — surprenant) | ✅ **duel recommandé** (échec inattendu = plus spectaculaire) |
| Psychick Warriors Ov Gaia — Exit 23 (Drum Club Remix 1) | ✅ | **échoue** (confirmé) | ✅ backup duel |
| Spiral Tribe Sound System — Forward The Revolution | ✅ | **TROUVÉ** par Shazam ❌ | ✗ hors duel — reste au set comme titre reconnu |
| The Justified Ancients Of Mu Mu — It's Grim Up North | ✅ | non testé | candidat de secours |
| Paperclip People — Throw (Slam's RTM Remix) | ✅ | non testé | candidat de secours |

**Bonus — Blue Monday** : Shazam trouve le morceau mais **se trompe de version**. Encore matche la signature exacte (1983) → affiche la bonne. Angle « précision maison » à exploiter si le timing démo le permet.

## Slot « inconnu » (carte Gemma) — distinct du duel

Le duel (ci-dessus) : Shazam échoue, **Encore gagne offline** (morceau signé). Le slot Gemma, lui, c'est un morceau que **rien** ne reconnaît — pas même le catalogue Encore — donc l'échelle rate entièrement et **Gemma le décrit** (genre, description, voix, BPM injecté par DSP).

- **Morceau** : un inédit de Mathieu, jamais publié (`Dub techno 1.m4a`, AAC 44,1 kHz, 5:11, sans métadonnées propres — normal, c'est le mystère).
- **NON signé, hors des dossiers indexés** — c'est indispensable pour que la reconnaissance rate :
  - clé : `encore_demo/unreleased/Dub techno 1.m4a` (à l'écart de `MUSIC/`)
  - projet : `data/samples/unreleased/` (gitignoré)
- **BPM (DSP, librosa) : ~129** — la ground-truth à injecter dans la carte Gemma (le contrat `id_card.schema.json` interdit à Gemma de le deviner). L'app le recalcule en direct sur le clip ; ~129 sert à vérifier que l'ID card est juste. Durée : 311 s.
