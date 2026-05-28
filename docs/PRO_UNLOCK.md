# Comment ça marche ? — PhotoOrganizer Lifetime Unlock

> Page utilisateur. Ouvre depuis le bouton "Comment ça marche ?" du modal d'activation.
> Tu cherches les détails techniques ou business ? Va voir [`MONETIZATION.md`](MONETIZATION.md).

---

## En 30 secondes

PhotoOrganizer est **gratuit pour essayer** — 10 tris de photos sans payer
un centime, pour vérifier que l'outil te convient sur **tes** vraies
photos.

Au-delà, **10 € à vie** débloque l'usage illimité sur un seul PC. Pas
d'abonnement, pas de renouvellement, toutes les futures mises à jour
incluses.

C'est le même modèle que **Sublime Text**, **WinRAR** ou **Beyond Compare** :
tu essaies, tu décides, tu paies une fois, c'est fini.

---

## Ce qui est gratuit

- L'application complète (4 onglets : Organisation, Doublons, Historique, Paramètres)
- **10 organisations** réussies (chaque tri compte comme 1, peu importe
  le nombre de photos ou les options choisies)
- Toutes les fonctionnalités sans aucune limite cachée
- Le code source sous Apache-2.0 sur GitHub si tu veux compiler ta
  propre version

## Ce qui débloque l'achat à 10 €

- Usage **illimité** sur ton PC pour toujours
- **Toutes les futures versions gratuites**, à vie (v2.4, v3.0, etc.)
- Le sentiment chaleureux d'avoir soutenu un dev solo 🙂

---

## Politique 1 PC — à lire avant d'acheter

La licence est **liée au premier ordinateur** sur lequel tu l'actives.
Techniquement, on combine deux identifiants Windows (le `MachineGuid` et
le numéro de série du disque C:) pour reconnaître ta machine. Cette
empreinte est calculée et stockée **uniquement chez toi** — on ne la
voit jamais.

**Tu auras besoin d'une nouvelle clé dans ces cas-là** :

- Changement d'ordinateur (nouveau PC, portable de remplacement)
- Réinstallation complète de Windows (le `MachineGuid` change)
- Remplacement du disque dur système

**Tu N'auras PAS besoin de nouvelle clé dans ces cas-là** :

- Mise à jour de l'app (toutes les versions futures sont incluses)
- Clonage du disque vers un disque plus gros (l'empreinte est
  généralement préservée par les outils de clonage)
- Réveil du PC après mise en veille, redémarrage, déménagement

**Pourquoi cette règle stricte ?**
Pour rester à 10 € sans serveur de licence et sans modèle d'abonnement.
Un éditeur seul ne peut pas gérer manuellement les transferts de
licence pour chaque client à ce prix.

**Geste commercial ponctuel ?**
Si tu rencontres un cas réellement injuste (panne matérielle dans les
premiers mois, par exemple), écris-nous à
[manugrolleau48@gmail.com](mailto:manugrolleau48@gmail.com). Pas de
promesse, mais on est humains.

---

## Trouve ton ID machine

L'**ID machine** apparaît partout où c'est utile :

- Dans le bandeau d'en-tête de l'app, format `Activée · MAC-7A3F-9C2E`
- Dans le modal d'activation que tu vois en ce moment
- Tu peux le copier-coller dans un email de support si besoin

C'est juste un hash — ton vrai numéro de série et ton MachineGuid
restent en local.

---

## Comment activer une clé

1. **Achète une clé** sur [photoorganizer.lemonsqueezy.com](https://photoorganizer.lemonsqueezy.com)
2. **Tu reçois un email** avec ta clé (manuel pour les 10 premiers
   acheteurs — sous 24h ; automatique ensuite — en quelques secondes)
3. **Colle la clé** dans le champ ci-dessus
4. **Clique sur "Activer"** — c'est fait. Plus jamais besoin d'y penser.

Si l'activation échoue :

- **"Clé invalide"** → vérifie qu'aucun caractère ne manque (un espace
  à la fin suffit à tout casser)
- **"Liée à un autre ordinateur"** → cette clé a déjà été activée sur un
  autre PC. Écris-nous si c'est une erreur.
- **"Clé expirée"** → improbable avec une licence lifetime, mais
  contacte-nous

---

## Tes données restent chez toi

- L'app fonctionne **100% en local**. Aucune photo ne quitte ton disque dur.
- Le compteur de tris (`usage.dat`) et la licence (`license.dat`) sont
  signés HMAC et stockés dans `%LOCALAPPDATA%\PhotoOrganizer\`. Toi
  seul y as accès.
- Aucun téléchargement de catalogue, aucun cloud forcé, aucune
  télémétrie.
- Le serveur de licence ? Il n'y en a pas. Tout est validé hors-ligne.

Détails complets sur la collecte de données : [`PRIVACY.md`](PRIVACY.md).

---

## Quelques questions fréquentes

**Et si je supprime `usage.dat` pour réinitialiser le compteur ?**
Ça marche. C'est un trade-off assumé : à 10 € le DRM agressif ne vaut
pas le coup. On compte sur ta bonne foi pour un essai honnête de 10
tris.

**Je peux installer sur mon PC ET mon portable ?**
Non, une clé = un PC. Si tu utilises deux machines, il te faut deux
clés.

**Si je revends mon PC à un proche, il hérite de ma licence ?**
Techniquement oui (la licence est sur le disque). Mais on te recommande
de désinstaller proprement avant la cession et qu'il achète sa propre
clé pour rester correct.

**Et si je veux contribuer au code ?**
Le code source est Apache-2.0, donc tu peux forker, modifier, distribuer
ta propre version. Si tu veux contribuer à l'upstream, lis
[`CONTRIBUTING.md`](../CONTRIBUTING.md).

**Le prix va augmenter ?**
Probablement pas en dessous de 15 €. Si tu hésites entre maintenant et
plus tard, achète maintenant — la promo de lancement à 30% (code
`EARLY30`) est limitée aux 30 premiers jours.

---

## Contact

Question, bug, doute, idée d'amélioration :
[manugrolleau48@gmail.com](mailto:manugrolleau48@gmail.com)

Réponse sous 5 jours ouvrés en général. Aucune télémétrie, aucun envoi
automatique — c'est juste toi et moi.

Merci d'utiliser PhotoOrganizer.
