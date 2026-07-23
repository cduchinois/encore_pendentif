# ENCORE

**Le pendentif qui capte la setlist pendant que tu profites pleinement de ta soirée, et te fait revivre l'émotion, one more time, le lendemain.**

*Gemma 4 Hackathon Paris, 25 juillet 2026. Tracks visées: Edge/On-Device (principale), Context Engineering for SLMs (Alien Intelligence), NVIDIA GPU Challenge (optionnelle).*

**Équipe**: Jade (iOS + pipeline), Mathieu (data + catalogue).

---

## 1. Le problème

Sortir son téléphone pour shazamer en plein moment d'émotion, c'est inhumain: ça casse la vibe, la tienne et celle des autres. Et le pire, c'est que ça ne marche même pas: Shazam sèche sur les transitions DJ, les tracks pitchés, les bootlegs et les morceaux non sortis, et sans réseau il ne répond que le lendemain. Au final il te reste, au mieux, une liste de titres à plat. La soirée, elle, est perdue.

## 2. La solution

**Encore** capte la setlist à ta place pendant que tu vis ta soirée. Tu ne sors plus jamais ton iPhone pour shazamer: le pendentif écoute, identifie en temps réel, et le lendemain il te rend la mémoire complète de ta nuit: setlist horodatée, transitions, moments forts, et la playlist prête dans Apple Music ou Spotify.

Un seul geste: tu adores ce qui joue, tu tapes le pendentif, le morceau est épinglé.

Le cerveau, c'est ton téléphone: **Gemma 4 en local + un catalogue de reconnaissance intégré**. Tout se passe sur l'appareil, rien ne part dans le cloud. Pour ce hackathon, nous avons préparé et scanné un catalogue de 3000 morceaux (la collection de Mathieu, raretés comprises) qui tient en quelques dizaines de Mo sur l'iPhone: la preuve qu'une base locale sérieuse est possible sans un seul appel serveur.

**Roadmap**: à ce ratio (~15 Ko par morceau), un catalogue d'un million de titres tiendrait en 10 à 20 Go; la vraie réponse produit, ce sont des packs catalogue par scène (techno, house, hip-hop...) de quelques centaines de Mo, téléchargés une fois, à jour, et à toi.

Positionnement: **Shazam identifie des morceaux, Encore capture des soirées, en temps réel, sans cloud.**

## 3. Comment ça marche

### Le matériel

- **Pendentif**: Seeed XIAO ESP32-S3 Sense (micro PDM intégré), coque translucide imprimée en 3D (fichiers STL prêts: `encore_body.stl` + `encore_lid.stl`, Ø42 x 23 mm, languette lanière intégrée, trous micro, encoche USB-C).
- **LED d'ambiance**: une WS2812B (NeoPixel, ~2 euros, 3 fils) derrière la coque dépolie: le pendentif change de couleur avec l'ambiance de la salle (bleu calme → rose/rouge chaud, pulse au drop), flash blanc au pin. Piloté en local (niveau sonore + basses) ou par l'iPhone via l'état de soirée. Mode privé = tout éteint, sans ambiguïté.
- **Alimentation**: LiPo 3,7V 500-600 mAh (taille boîte d'allumettes, ~10 g) soudée aux pastilles BAT; circuit de charge intégré au XIAO, recharge USB-C. Sans soudure: une mini power bank USB-C dans la coque.
- **Interaction, une seule zone tactile** (touch capacitif de l'ESP32-S3, pastille de cuivre sur la face avant): **double tap = pin le morceau** (flash LED), **appui long = mode privé** (écoute coupée, LED éteinte). Les moments forts, eux, sont détectés automatiquement par le volume de la foule, pas besoin de geste.
- **iPhone (app iOS privée, installée via Xcode, sans App Store)**: tout le cerveau tourne ici, en local. L'app continue en arrière-plan écran éteint (background modes iOS, liaison BLE avec le pendentif); pour la démo, l'écran reste allumé puisque c'est le dashboard.

**Roadmap matériel**: gestion d'écoute autonome (deep sleep, réveil quand la musique démarre, détection RMS + régularité spectrale), boîtier final, autonomie multi-soirées.

### Gemma 4, le cerveau permanent

Gemma 4 E2B tourne en local sur l'iPhone (llama.cpp ou Google AI Edge) et c'est lui qui comprend la soirée. Le fingerprinting n'est qu'un capteur spécialisé à son service: il donne des noms exacts, Gemma donne le sens. En continu, Gemma:

- **détecte et qualifie les transitions** (blend long, cut sec, montée de BPM) à partir de l'état de soirée compilé;
- **tague les moments forts** en croisant volume de foule, pins et enchaînements;
- **écoute ce que personne ne reconnaît** (entrée audio native, ce que ni le fingerprinting ni les modèles Apple ne savent faire) et produit une fiche ID structurée: genre, description, voix, extrait de paroles transcrit, avec BPM et tonalité calculés par DSP (librosa);
- **arbitre les candidats** lors de la résolution différée, avec sortie JSON structurée native;
- **rédige le récap** de fin de soirée.

### La reconnaissance, du plus précis au plus robuste

1. **Fingerprint local, instantané et offline**: ShazamKit custom catalog (matching 100% on-device) sur le catalogue embarqué; alternative Olaf compilé pour iOS. Identification en 3 à 5 secondes, lookup en millisecondes, zéro réseau.
2. **Similarité par embeddings**: rattrape les morceaux filtrés, superposés ou trop dégradés pour le match exact.
3. **Catalogue mondial Shazam (si réseau)**: filet gratuit pour le mainstream hors catalogue local.
4. **Fiche ID Gemma**: quand tout échoue, le modèle écoute et décrit (voir ci-dessus).
5. **Rien n'est jamais perdu**: pour chaque inconnu, on sauvegarde le clip audio, l'empreinte, l'embedding et la fiche. La fiche sert à l'humain; le clip et l'empreinte servent aux machines pour la résolution différée.

### Le catalogue (préparé la veille)

- Les 3000 morceaux sont fingerprintés en batch sur Mac (quelques heures, une nuit suffit).
- Chaque morceau est **enrichi à l'avance**: liens Spotify et Apple Music (iTunes Search API, Spotify Web API), pochette, BPM. Au match, la fiche complète sort instantanément, offline, liens compris. Priorité aux ~50 morceaux du set de démo.
- **Audit anti-Shazam**: trouver quelques morceaux confirmés introuvables par Shazam, car la démo comparera Encore et Shazam en direct.

### La résolution différée (SerpAPI au cœur)

Quand le réseau revient, un job de fond résout les inconnus:

- **SerpAPI**: recherche Google des paroles transcrites entre guillemets, recherche par description, résultats YouTube pour vérifier les candidats, croisement avec les tracklists publiées (type 1001Tracklists). En bonus pour le récap: pochettes (Google Images) et prochaines dates de l'artiste (Google Events).
- **Reconnaissance exacte sur clip**: AudD ou ACRCloud sur l'extrait sauvegardé.
- **Enrichissement écoutable**: iTunes Search API et Spotify Web API transforment "titre + artiste" en liens jouables.

### La couche context engineering (track Alien Intelligence)

Un petit modèle à l'edge n'a ni la RAM ni les tokens pour du contexte brut. Encore embarque un **compilateur de contexte** à deux étages:

1. **L'état de soirée compressé**: setlist, courbe BPM, volume de la foule et pins maintenus en une représentation structurée ultra-compacte. C'est ce contexte compilé qui permet à E2B de détecter les transitions, taguer les moments forts et rédiger le récap.
2. **La compilation des résultats SerpAPI**: une réponse SERP brute fait ~50 Ko de JSON; le compilateur la réduit en moins de 1000 tokens de preuves structurées (candidats, concordances de paroles, sources), et E2B tranche avec un score de confiance.

Mini-benchmark présenté au jury: taux de résolution correcte par token de contexte, petit modèle + contexte compilé contre gros modèle + JSON brut.

### Le produit final

Fin de soirée, un bouton: **"Tu veux vivre Encore cette soirée?"** Gemma génère le récap (setlist complète, courbe d'énergie, les moments où la salle a explosé, tes pins en tête), et l'app crée la playlist directement dans Apple Music (MusicKit) ou Spotify (Web API). On n'écoute pas dans notre app: on livre la soirée dans l'app de musique que les gens utilisent déjà.

### Qu'est-ce qui est "edge"?

Tout le chemin critique: capture sur le pendentif; fingerprint, embeddings, inférence Gemma, timeline et récap sur l'iPhone. Aucun serveur à nous. L'audio d'une soirée privée est traité et jeté sur place: privacy par construction. Le cloud (SerpAPI, liens, playlist) n'est que de l'enrichissement différé et optionnel. **Le cloud améliore Encore, mais Encore n'a pas besoin du cloud.**

## 4. Technologies sponsors utilisées

| Sponsor | Utilisation |
|---|---|
| **Gemma 4 (Google DeepMind)** | E2B en local sur iPhone, cerveau permanent: fiches ID des inconnus (entrée audio native), détection des transitions, moments forts, récap, arbitrage des candidats SerpAPI. Function calling et sortie JSON structurée natifs. |
| **SerpAPI** | Résolution différée des IDs (paroles, YouTube, tracklists) et enrichissement culturel du récap (pochettes, concerts à venir). Consomme les crédits offerts au cœur du produit. |
| **Alien Intelligence** | Track Context Engineering: le compilateur de contexte à deux étages + benchmark accuracy/token. À affiner avec leurs mentors le matin même selon leur API. |
| **NVIDIA (optionnel)** | Variante serveur: le même pipeline servi par Gemma 4 sur vLLM pour le cas "club entier" multi-flux, si le temps le permet. |

## 5. La démo (5 minutes)

Le set de démo est mixé entièrement dans le catalogue embarqué: reconnaissance rapide garantie, pièges anti-Shazam pré-vérifiés.

1. **Décor (30 s)**: enceinte Bluetooth, mini DJ set, pendentif au cou, dashboard iPhone projeté.
2. **Reconnaissance passive (1 min)**: les morceaux tombent en 3-4 secondes sur la timeline. Personne n'a touché un téléphone.
3. **Le duel (le moment fort)**: un bootleg/edit rare, puis une transition avec deux morceaux superposés. Un juge Shazame en même temps, connexion activée. Shazam sèche; Encore affiche, hors ligne.
4. **Mode avion (30 s)**: on coupe tout réseau, tout continue. "Aucune donnée ne quitte la pièce."
5. **Le pin (30 s)**: double tap sur le pendentif au drop, flash LED, morceau épinglé. Appui long: LED éteinte, mode privé, réponse à la question privacy avant qu'elle soit posée.
6. **Le morceau introuvable (1 min)**: un beat produit par l'équipe la veille, inconnu de l'univers entier. Fiche ID Gemma (genre, BPM, description, paroles). On réactive le WiFi: la résolution différée SerpAPI se lance en live.
7. **Le final (30 s)**: "Tu veux vivre Encore cette soirée?", récap généré par Gemma, playlist créée dans Apple Music sous les yeux du jury. *"Shazam vous donne un titre. Encore vous rend votre soirée."*

## 6. Périmètre du jour J

**Doit marcher**: streaming pendentif → iPhone, fingerprint local, timeline, pin, fiche Gemma, récap, playlist.
**Bonus si le temps**: résolution SerpAPI en live pendant la démo, benchmark contexte chiffré, embeddings, étage catalogue mondial Shazam.
**Coupé sans regret / roadmap**: gestion d'écoute autonome (deep sleep), multi-utilisateurs, comptes, App Store, boîtier final, packs catalogue par scène.

## 7. Préparation avant le 25 (checklist)

*À valider avec le règlement: libs open source, données et matériel préparés sont généralement autorisés, le code produit le jour même.*

- [ ] **Mathieu**: exporter la base proprement (fichiers audio + tags titre/artiste fiables); lancer le script de fingerprinting sur les 3000 morceaux (une nuit); enrichissement Spotify/Apple des ~50 morceaux du set de démo.
- [ ] **Audit anti-Shazam**: tester les raretés candidates contre Shazam, ne garder que les échecs confirmés.
- [ ] **Jade**: flasher et tester le XIAO dès réception (streaming audio = le plus gros risque); alimentation (LiPo soudée ou power bank); installer Gemma E2B sur Mac et iPhone (tester llama.cpp ET Google AI Edge, garder le meilleur).
- [ ] **Impression 3D de la coque au fablab de 42**: apporter `encore_body.stl` et `encore_lid.stl` (clé USB ou mail), filament transparent ou translucide (PETG ou PLA), 0,2 mm, 2-3 périmètres, pas de supports, ~1h30 d'impression. Demander de l'aide au staff du lab pour le slicer. Poncer l'intérieur pour l'effet lueur diffuse.
- [ ] Acheter la LED WS2812B (breakout 1 pixel ou mini anneau 8 LED) + lanière/cordon.
- [ ] Produire le faux morceau inédit (30 s de beat suffisent).
- [ ] Répéter le duel Shazam 10 fois, chronométrer la démo.
