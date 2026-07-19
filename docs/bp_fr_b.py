"""Édition française — chapitres 4 à 9 (produit, avantage, tarification, finance)."""
from __future__ import annotations

from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, Spacer

import finance_model as FM
from build_business_plan import (M, UE, BE, SENS, MK, SVC, SS, bullets, callout,
                                 heading, kpibox, money, num, para, pc, rule,
                                 srcbox, table)


def ch4():
    s = [heading("4 &nbsp; Le produit, et la preuve qu'il existe", 0),
         para("Un plan d'affaires qui décrit un logiciel non écrit est une promesse. Ce "
              "chapitre décrit du code qui tourne, et chaque affirmation est reproductible par "
              "une commande listée en annexe B."),

         heading("4.1 &nbsp; Ce qu'est BatchTwin", 1),
         para("Une couche numérique posée sur l'ERP Odoo existant du client, qui exécute le lot "
              "tel qu'il se déroule réellement &mdash; chaque gramme, chaque contrôle, chaque "
              "signature, chaque kilowattheure &mdash; et produit un dossier de lot conforme et "
              "sans papier."),
         Spacer(1, 3),
         table(["Couche", "Fonction", "État"],
               [["Moteur de dossiers", "Analyse les modèles `.docx` du client et les convertit "
                 "en formulaires saisissables ; la spécification produit recouvre le bloc "
                 "d'identification, si bien que l'identité n'est jamais ressaisie.",
                 "Réalisé, 1 205 champs [MESURÉ]"],
                ["Cycle de vie et barrières", "Cinq étapes (DFA, DCOI, DCOII, DCT, libération) "
                 "avec barrières de signature par rôle. La libération est bloquée tant que "
                 "chaque étape n'est pas signée et chaque contrôle satisfait.", "Réalisé"],
                ["Identité et signatures", "PBKDF2-HMAC-SHA256, 240 000 itérations, sel par "
                 "utilisateur, comparaison à temps constant. Mot de passe ressaisi à chaque "
                 "signature, conformément au 21 CFR 11.200 [SOURCÉ] réf. [20].", "Réalisé"],
                ["Piste d'audit", "Enregistrements chaînés par empreintes, plus un fichier "
                 "d'ancrage externe en ajout seul : une réécriture complète de la base reste "
                 "détectable.", "Réalisé"],
                ["Coût et bilan matière", "Quantité réellement consommée face à la "
                 "nomenclature théorique ; rendement, perte et coût réel par unité.",
                 "Réalisé ; l'ordre de grandeur exige une pesée réelle"],
                ["MSP", "Carte de contrôle X&#772;/R, règles Western Electric, prévision de "
                 "dérive par moindres carrés face aux limites de spécification.",
                 "Réalisé et validé sur un exemple de référence"],
                ["VÉRA", "Prévision de matières premières, FEFO avec projection de péremption, "
                 "point de commande avec stock de sécurité.", "Réalisé sur jeu de données simulé"],
                ["Conseiller de reprise", "Recommandation par cas à partir des déviations "
                 "clôturées du site, classant les actions qui ont tenu au-dessus de celles qui "
                 "ont récidivé.", "Réalisé"],
                ["Intégration Odoo", "XML-RPC `execute_kw` ; **en lecture seule par "
                 "construction**.", "Adaptateurs simulé et réel ; le réel n'a jamais été "
                 "éprouvé sur un Odoo de production"]],
               [34 * mm, 90 * mm, 46 * mm]),

         Spacer(1, 6),
         heading("4.2 &nbsp; Preuves mesurées", 1),
         para("Chiffres produits en exécutant le code, non en le décrivant :"),
         Spacer(1, 3),
         table(["Indicateur", "Valeur", "Mode d'obtention"],
               [["Champs de dossier numérisés", "1 205", "`docx_forms.load_all('dossier')` sur quatre modèles réels"],
                ["Contrôles de conformité tactiles", "135", "cellules S/NS et C/NC adjacentes fusionnées en un contrôle"],
                ["Lignes papier vierges supprimées", "570", "séries de &ge; 3 lignes vides identiques repliées en bloc extensible"],
                ["Blocs répétables", "27", "tableaux extensibles à la demande au lieu d'être pré-imprimés"],
                ["Modèles de dossier &rarr; formulaire adaptatif", "4 &rarr; 1", "la spécification produit recouvre le bloc d'identification"],
                ["Ressaisie manuelle de l'identité produit", "4 &rarr; 0", "l'identité provient de la spécification versionnée"],
                ["Routes d'API", "84", "`backend/main.py`"],
                ["Lignes de code backend", "6 609", "`find backend -name '*.py' | xargs wc -l`"],
                ["Tests automatisés au vert", "143 (8 ignorés)", "`python -m pytest -q`"],
                ["Profils métier pris en charge", "4", "BPF pharma, cosmétique, agroalimentaire HACCP, dispositif médical"]],
               [58 * mm, 26 * mm, 86 * mm], align_right=(1,)),

         Spacer(1, 6),
         heading("4.3 &nbsp; Économie unitaire d'un lot réel", 1),
         para(f"Calculée à partir de la nomenclature réelle de Medicka pour le produit de "
              f"démonstration &mdash; sirop oral citrate de magnésium et vitamine B6, 200 mL, "
              f"lot de {UE['units']} unités :"),
         Spacer(1, 3),
         table(["Grandeur", "Valeur (TND)", "Valeur (EUR)", "Remarque"],
               [["Coût matière théorique par lot", num(UE["bom_tnd"], 2),
                 f"{UE['bom_eur']:,.2f}", "ce que croit Odoo [MESURÉ]"],
                ["Coût matière par unité", num(UE["cost_per_unit_tnd"], 4),
                 f"{UE['cost_per_unit_eur']:.4f}", "11 lignes de nomenclature, coûts fournisseurs réels"],
                ["Réellement consommé", "inconnu", "inconnu", "aucun site ne le mesure aujourd'hui"],
                ["Perte matière", "inconnue", "inconnue", "**le chiffre que BatchTwin crée**"]],
               [58 * mm, 28 * mm, 26 * mm, 58 * mm], align_right=(1, 2)),
         Spacer(1, 5),
         para("La nomenclature complète, à 11 lignes, est reproduite en annexe C. Nous la "
              "montrons parce qu'elle fait la différence entre un plan qui *affirme* que la "
              "perte matière existe et un plan qui *démontre le mécanisme* qui va la mesurer."),

         heading("4.4 &nbsp; Ce qui n'est délibérément pas affirmé", 1)]
    s += bullets([
        "**Aucune connexion Odoo réelle n'a été éprouvée** sur l'instance de production d'un "
        "client. Le contrat XML-RPC dispose d'un adaptateur simulé, d'un adaptateur réel et "
        "d'un test de contrat, mais le chemin réel n'est pas démontré. C'est le premier "
        "risque technique et il figure au registre du chapitre 12.",
        "**L'ordre de grandeur de la perte matière n'est pas mesuré.** Le mécanisme est du "
        "code réel sur une nomenclature réelle ; le chiffre obtenu en démonstration provient "
        "d'une pesée simulée.",
        "**Les chiffres de VÉRA sont synthétiques.** Écart de vérité de stock, exposition à "
        "la péremption et stock dormant sont calculés de façon déterministe sur un jeu de "
        "données amorcé, non sur l'entrepôt de Medicka.",
        "**La lecture OCR d'étiquette est inexploitable avec le modèle installé.** La chaîne "
        "de traitement est correcte, y compris l'échelle de résolution adaptative ; le modèle "
        "de vision à 2 milliards de paramètres présent sur la machine de développement est "
        "trop faible pour lire une étiquette nutritionnelle. La saisie manuelle est le chemin "
        "principal et fonctionne toujours.",
        "**Les livrables de validation ne sont pas encore modélisés.** CDC, QI, QO et QP sont "
        "vendus comme prestation au tarif indiqué, mais existent aujourd'hui comme périmètre, "
        "non comme documents.",
    ])
    s += [Spacer(1, 5),
          kpibox("Chapitre 4 &mdash; indicateurs produit", [
              ("Champs de dossier", "1 205", "MESURÉ", "analyseur docx_forms"),
              ("Contrôles de conformité", "135", "MESURÉ", "fusion S/NS + C/NC"),
              ("Lignes vierges supprimées", "570", "MESURÉ", "repli des blocs répétables"),
              ("Routes d'API", "84", "MESURÉ", "backend/main.py"),
              ("Tests au vert", "143", "MESURÉ", "pytest"),
              ("Lignes de code backend", "6 609", "MESURÉ", "wc -l"),
              ("Coût matière par lot", money(UE["bom_tnd"]), "MESURÉ", "analytics.mass_balance()"),
              ("Connexion Odoo réelle", "non démontrée", "&mdash;", "risque R1, ch. 12"),
          ]),
          PageBreak()]
    return s


def ch5():
    s = [heading("5 &nbsp; Avantage concurrentiel", 0),
         para("Quatre avantages sont structurels &mdash; ils découlent d'une décision de "
              "conception qu'un concurrent devrait renverser pour les copier. Le reste relève "
              "de l'exécution, et l'exécution se copie."),

         heading("5.1 &nbsp; Paysage concurrentiel", 1),
         table(["Alternative", "Ce qu'elle coûte", "Pourquoi le client ne la choisit pas"],
               [["Rester sur papier", "Rien de visible", "Le calcul de coût est une "
                 "approximation, la libération est lente, et une non-conformité en inspection "
                 "est existentielle. Le véritable concurrent en place."],
                ["MasterControl", "À partir de 1 000 $/mois par fonction, davantage par site [SOURCÉ]",
                 "Tarifé pour les multinationales ; les limites de licence et le coût par site "
                 "supplémentaire sont les griefs précis des avis clients."],
                ["Werum PAS-X (Körber)", "18 à 24 mois, conseil à six chiffres [SOURCÉ]",
                 "Le seul calendrier de déploiement disqualifie une PME ; couplage étroit à "
                 "l'écosystème de l'éditeur."],
                ["Module Qualité d'Odoo", "Inclus dans Odoo", "Enregistre des contrôles. Ne "
                 "produit pas de dossier de lot conforme et n'a pas de signature Part 11."],
                ["Développement interne", "18 mois d'ingénierie", "Aucune expérience de "
                 "validation, et la charge de maintenance ne s'arrête jamais."]],
               [34 * mm, 44 * mm, 92 * mm]),

         Spacer(1, 6),
         heading("5.2 &nbsp; Les quatre avantages structurels", 1),

         heading("5.2.1 &nbsp; Nous lisons les documents du client", 2),
         para("Tout eBR concurrent exige que le client ré-implémente ses dossiers dans le "
              "modèle de données de l'éditeur. Ce travail &mdash; et non la licence &mdash; "
              "concentre l'essentiel du coût d'un projet eBR et la quasi-totalité de son "
              "risque de calendrier ; l'intégration cause plus de retard que toute autre "
              "partie de ces projets [SOURCÉ]."),
         para("BatchTwin analyse les fichiers `.docx` que le client possède déjà. Quatre "
              "dossiers réels de Medicka sont devenus **1 205 champs saisissables sans aucune "
              "retranscription** [MESURÉ]. Commercialement, c'est la démonstration qui emporte "
              "la vente : un prospect envoie un dossier par courriel et le voit tourner comme "
              "formulaire tablette dans la même réunion. Aucun concurrent ne peut répondre à "
              "cela en réunion."),

         heading("5.2.2 &nbsp; Déploiement sur site par défaut", 2),
         para("L'IA s'exécute sur un modèle Ollama local et la base de données appartient au "
              "client. Les données de lot et les formules ne quittent jamais le site. Un "
              "directeur qualité qui entend « vos formules restent sur votre serveur » se "
              "détend ; celui qui entend « notre cloud » ouvre une discussion d'audit "
              "fournisseur Annexe 11 qui peut coûter des mois."),
         para("Il existe un second bénéfice, plus discret, qui apparaît au chapitre 7 : **nous "
              "ne supportons aucun coût cloud par client.** Le premier poste de coût variable "
              "d'un concurrent SaaS est absent de notre compte de résultat par construction, "
              "et c'est la raison pour laquelle la marge brute sur les licences est proche de "
              "la totalité."),

         heading("5.2.3 &nbsp; L'intégration Odoo ne peut pas corrompre l'ERP", 2),
         para("BatchTwin lit dans Odoo via XML-RPC et n'y écrit jamais. Cela a commencé comme "
              "une précaution et s'est révélé la phrase la plus forte de l'entretien "
              "commercial : le client ne peut pas être lésé par l'intégration, si bien que "
              "l'objection informatique &mdash; habituellement la plus lente à lever &mdash; ne "
              "se forme jamais. Cela signifie aussi qu'à la question « qu'advient-il quand vos "
              "données capteurs encombrent notre ERP ? », la réponse est dans l'architecture "
              "plutôt que dans une politique."),

         heading("5.2.4 &nbsp; Une intelligence adaptative qui cite ses preuves", 2),
         para("Chaque déviation clôturée par l'AQ porte une cause racine, une CAPA et une "
              "décision de disposition. C'est une base de cas que l'usine écrit elle-même. "
              "Lorsqu'un nouveau problème apparaît &mdash; ou lorsque la MSP prévoit un "
              "franchissement alors que rien n'a encore échoué &mdash; le conseiller retrouve "
              "les cas clôturés correspondants et rapporte ce qui a été fait et **si cela a "
              "tenu**. Une CAPA suivie d'une récidive se classe sous une CAPA qui a tenu."),
         para("Ce n'est délibérément pas un modèle entraîné. Chaque recommandation nomme le "
              "lot, la date et la personne qui a signé, de sorte qu'un opérateur peut aller "
              "lire ce dossier. Un score de probabilité ne lui donne rien sur quoi agir, et un "
              "opérateur BPF ne peut pas signer contre 0,83. Le dispositif fonctionne en outre "
              "dès le premier lot, sans jeu de données à constituer."),

         Spacer(1, 4),
         callout("La limite honnête de la barrière à l'entrée",
                 "L'analyseur `.docx` est l'actif défendable, et il l'est peut-être deux ans "
                 "plutôt que pour toujours &mdash; un concurrent bien doté saurait en écrire "
                 "un. La barrière durable n'est pas l'analyseur ; ce sont les modèles de "
                 "dossiers accumulés, les profils métier et les bases de cas de déviations "
                 "clôturées des clients installés, qui gagnent en valeur à chaque client et "
                 "dont rien ne se transfère à un concurrent. C'est pourquoi le plan privilégie "
                 "les clients de référence sur la marge en année 1.", "info"),

         Spacer(1, 5),
         heading("5.3 &nbsp; Positionnement face aux allégations d'IA", 1),
         para("Un mot sur la discipline, car c'est un avantage concurrentiel en marché "
              "réglementé. Deux composants seulement de BatchTwin relèvent de l'apprentissage "
              "automatique : le copilote de recherche documentaire et le lecteur d'étiquettes "
              "par vision. La prévision MSP est une régression par moindres carrés ; les "
              "coefficients saisonniers de VÉRA sont écrits à la main. Nous le disons dans la "
              "documentation comme dans la présentation."),
         para("La raison est réglementaire plutôt que modeste. Un inspecteur peut valider une "
              "carte de contrôle &mdash; les constantes viennent de l'ASTM STP-15D / "
              "ISO 7870-2 et l'arithmétique tient sur une page. Valider un modèle entraîné "
              "suppose de qualifier ses données d'entraînement, de versionner les poids et de "
              "reprouver le comportement après chaque réentraînement. **Aucun modèle appris ne "
              "se trouve sur un chemin critique de libération**, et un test vérifie que le "
              "module assistant ne contient aucun chemin d'écriture."),

         Spacer(1, 4),
         kpibox("Chapitre 5 &mdash; indicateurs d'avantage", [
             ("Retranscription pour intégrer un dossier", "aucune", "MESURÉ", "l'analyseur lit le .docx client"),
             ("Champs intégrés depuis 4 dossiers réels", "1 205", "MESURÉ", "docx_forms"),
             ("Coût cloud par client", "0 TND", "CALCULÉ", "déploiement sur site, ch. 7"),
             ("Écritures dans l'Odoo du client", "0", "MESURÉ", "adaptateur lecture seule + test de contrat"),
             ("Composants ML sur chemin critique", "0", "MESURÉ", "AssistantReadOnlyTests"),
             ("Démarrage à froid du conseiller", "aucun", "MESURÉ", "base de cas dès le premier lot"),
         ]),
         Spacer(1, 4),
         srcbox(["[1] Capterra &mdash; MasterControl", "[12] BatchLine &mdash; PAS-X",
                 "[13] A3P &mdash; opportunités et écueils de l'eBR",
                 "[14] Vimachem &mdash; l'eBR dans le MES"]),
         PageBreak()]
    return s


def ch6():
    p = FM.PLANS
    s = [heading("6 &nbsp; Modèle économique et tarification", 0),
         callout("Aucun prix de ce chapitre n'a été éprouvé auprès d'un client",
                 "Ce qui suit expose le raisonnement d'abord et le chiffre ensuite, afin que "
                 "le montant puisse être discuté plutôt que simplement cité. Chaque prix est "
                 "une **position d'ouverture dérivée d'ancrages publics**, non un tarif "
                 "validé. Ce qui le ferait bouger : trois entretiens clients.", "warn"),

         Spacer(1, 5),
         heading("6.1 &nbsp; Qui achète réellement", 1),
         para("**Ni** l'opérateur qui s'en sert, **ni** la direction informatique. L'acheteur "
              "est le **pharmacien responsable ou le directeur qualité** &mdash; la personne "
              "qui signe personnellement la libération et porte personnellement le risque "
              "réglementaire. Le responsable de production est le champion, parce que le "
              "produit lui retire de la paperasse ; la direction financière approuve, parce "
              "qu'il expose le coût réel par lot ; et l'informatique n'a qu'à ne pas s'y "
              "opposer &mdash; d'où l'importance commerciale de l'intégration en lecture "
              "seule."),
         para("Cela façonne le discours : **risque et traçabilité d'abord, efficacité "
              "ensuite**. Un directeur qualité n'achète pas du temps gagné. Il achète la "
              "capacité de répondre à un inspecteur."),

         heading("6.2 &nbsp; Les deux ancrages publics", 1),
         table(["Ancrage", "Montant", "Source"],
               [["eBR d'entreprise", "MasterControl à partir de **1 000 $/mois par fonction**, "
                 "coût additionnel par site", "[SOURCÉ] réf. [1]"],
                ["Ce que le client paie déjà en logiciel", "Odoo Enterprise "
                 "**8,95 à 76,20 $ par utilisateur et par mois**, le Moyen-Orient en bas de "
                 "fourchette", "[SOURCÉ] réf. [2]"]],
               [42 * mm, 78 * mm, 50 * mm]),
         Spacer(1, 5),
         para("**La règle que ces ancrages produisent :** tarifer *au-dessus* de ce que le "
              "client paie déjà pour son ERP &mdash; BatchTwin porte davantage de risque "
              "réglementaire qu'Odoo &mdash; et *un ordre de grandeur en dessous* d'un MES "
              "d'entreprise, parce qu'être abordable pour un site de cent personnes est la "
              "raison d'être même du produit."),

         heading("6.3 &nbsp; Par site, et ce point n'est pas négociable", 1),
         para("Les opérateurs travaillent en équipes sur des tablettes partagées. Une "
              "tarification par utilisateur pénalise exactement le comportement dont le "
              "produit dépend &mdash; chacun enregistrant ses propres actions sous sa propre "
              "identité &mdash; et pousse les clients vers des comptes partagés, ce qui détruit "
              "le modèle d'identité Part 11 sur lequel repose toute la conformité. **Un modèle "
              "tarifaire qui sape l'argument central du produit est le mauvais modèle, à "
              "n'importe quel prix.**"),

         heading("6.4 &nbsp; La grille tarifaire d'ouverture", 1),
         table(["Offre", "Périmètre", "Annuel par site"],
               [["Essential", "1 ligne de production, jusqu'à 5 produits",
                 f"**{money(p['Essential']['annual_tnd'])}**"],
                ["Standard", "1 site, lignes illimitées, MSP + VÉRA + déviations + indicateurs",
                 f"**{money(p['Standard']['annual_tnd'])}**"],
                ["Enterprise", "Multi-sites, tableau de bord hybride, SSO, SLA prioritaire",
                 f"**{money(p['Enterprise']['annual_tnd'])}** + "
                 f"{money(p['Enterprise']['group_fee_tnd'])} groupe"]],
               [26 * mm, 92 * mm, 52 * mm], align_right=(2,)),
         Spacer(1, 5),
         para("**Comment le tarif Standard a été construit, pour qu'il puisse être contesté :**"),
         ] + bullets([
        f"Un site d'une centaine de personnes paie environ **34 000 à 84 000 TND par an** "
        f"pour Odoo Enterprise aux tarifs Maghreb [CALCULÉ d'après la réf. [2] pour "
        f"40 utilisateurs]. {money(p['Standard']['annual_tnd'])} se situe dans cette "
        f"fourchette &mdash; défendable, puisque BatchTwin porte le dossier réglementaire et "
        f"pas Odoo.",
        f"MasterControl ouvre à 1 000 $ par mois pour une seule fonction puis refacture par "
        f"site ; un déploiement eBR comparable atteint six chiffres en dollars. "
        f"{money(p['Standard']['annual_tnd'])} en représente environ un dixième, ce qui est "
        f"toute la raison pour laquelle ce produit peut exister sur ce segment.",
        f"À environ {money(p['Standard']['annual_tnd'] / 12)} par mois, c'est une ligne "
        f"budgétaire qu'un directeur qualité approuve sans note au comité. Au-delà d'environ "
        f"65 000 TND, cela devient une décision d'investissement avec comité, et le cycle de "
        f"vente double.",
    ]) + [
        Spacer(1, 5),
        heading("6.5 &nbsp; Prestations &mdash; d'où vient réellement le revenu initial", 1),
        para(f"Tarifées à partir d'un taux journalier calculé plutôt qu'inventé. Un ingénieur "
             f"senior chargé coûte environ **{money(FM.ENG_MONTHLY_TND)} par mois** à Tunis "
             f"[SOURCÉ, fourchette 3 500 à 7 000+]. Sur {FM.WORKING_DAYS_PER_MONTH} jours "
             f"ouvrés, avec un coefficient de {FM.BILL_MULTIPLIER:.0f} appliqué aux "
             f"prestations, cela donne **{money(FM.DAY_RATE_TND)} par jour** [CALCULÉ]."),
        Spacer(1, 3),
        table(["Prestation", "Jours", "Prix", "Contenu"],
              [["Déploiement et intégration des dossiers", "20", money(SVC[0]["price_tnd"]),
                "analyse et validation des modèles `.docx` du client"],
               ["Pack de validation (CDC/QI/QO/QP)", "16", money(SVC[1]["price_tnd"]),
                "les documents que le client présente à l'inspecteur"],
               ["Accompagnement marche parallèle et formation", "11", money(SVC[2]["price_tnd"]),
                "8 semaines à temps partiel, les deux systèmes en service"],
               ["**Total première année**", f"**{sum(r['days'] for r in SVC)}**",
                f"**{money(FM.services_total())}**", "non récurrent"]],
              [56 * mm, 14 * mm, 28 * mm, 72 * mm], align_right=(1, 2), bold_rows=(3,)),
        Spacer(1, 5),
        callout("À étalonner avant toute proposition chiffrée",
                "Le comparable mental du client n'est pas MasterControl &mdash; c'est le tarif "
                "journalier d'un intégrateur Odoo local en Tunisie. C'est un chiffre "
                "obtenable en une semaine, et il devrait l'être avant la première proposition. "
                "Notre taux journalier est dérivé de données salariales, ce qui est une "
                "approximation raisonnable et non la même chose qu'un prix de marché.", "warn"),

        Spacer(1, 5),
        heading("6.6 &nbsp; Licence et support", 1),
        para("**Licence commerciale, code source remis au client.** Chaque client reçoit le "
             "code source de son déploiement sous licence de non-redistribution. C'est "
             "inhabituel et délibéré : un client BPF doit pouvoir répondre à un inspecteur sur "
             "ce que fait le système, et « faites-nous confiance, c'est une boîte noire » est "
             "une réponse faible au regard de l'Annexe 11. Un séquestre est proposé pour "
             "l'offre Enterprise."),
        para("Pas d'open source &mdash; l'analyseur `.docx` est l'actif défendable et le donner "
             "supprimerait la barrière à l'entrée. [HYPOTHÈSE] À reconsidérer si l'adoption "
             "stagne ; un noyau ouvert avec modules de conformité commerciaux est un repli "
             "crédible."),
        para("**Le support est inclus dans l'abonnement, non facturé à part, et les mises à "
             "jour réglementaires sont comprises.** Un client ne doit jamais recevoir de "
             "facture pour rester conforme, et le dire supprime la principale objection à "
             "l'abonnement dans une industrie réglementée."),

        Spacer(1, 4),
        kpibox("Chapitre 6 &mdash; indicateurs tarifaires", [
            ("Essential", money(p["Essential"]["annual_tnd"]), "CALCULÉ", "fourchette d'ancrage, réf. [1][2]"),
            ("Standard", money(p["Standard"]["annual_tnd"]), "CALCULÉ", "juste au-dessus de la facture Odoo"),
            ("Enterprise par site", money(p["Enterprise"]["annual_tnd"]), "CALCULÉ", "+ forfait groupe"),
            ("Taux journalier prestations", money(FM.DAY_RATE_TND), "CALCULÉ",
             f"{money(FM.ENG_MONTHLY_TND)}/{FM.WORKING_DAYS_PER_MONTH} j &times; {FM.BILL_MULTIPLIER:.0f}"),
            ("Prestations première année", money(FM.services_total()), "CALCULÉ", "47 jours au total"),
            ("Valeur moyenne du contrat initial", money(MK["avg_first_year_contract_tnd"]),
             "CALCULÉ", "Standard + prestations"),
            ("Prix validés auprès de clients", "0", "&mdash;", "question ouverte n° 3"),
        ]),
        Spacer(1, 4),
        srcbox(["[1] Capterra &mdash; tarifs MasterControl", "[2] OEC.sh &mdash; tarifs Odoo par pays",
                "[3] Tarifs officiels Odoo", "[15] Glassdoor / levels.fyi &mdash; salaire ingénieur Tunis"]),
        PageBreak()]
    return s


def ch7():
    y1, y2, y3 = M[1], M[2], M[3]
    s = [heading("7 &nbsp; Structure de coûts et économie unitaire", 0),
         para("Ce que coûte l'exploitation de cette entreprise, et ce que vaut un client."),

         heading("7.1 &nbsp; Base de coûts", 1),
         para("La masse salariale domine, comme il se doit dans une société de logiciel. Trois "
              "fondateurs la première année, avec revalorisation à mesure que le revenu le "
              "permet, et renforcement de la capacité de livraison plutôt que de l'effectif "
              "commercial &mdash; sur un marché à cycle de vente de 6 à 12 mois, la qualité de "
              "livraison engendre la référence suivante, et la référence engendre la vente "
              "suivante."),
         Spacer(1, 3),
         table(["Poste", "Année 1", "Année 2", "Année 3", "Base"],
               [["Effectif", str(FM.HEADCOUNT[1]), str(FM.HEADCOUNT[2]), str(FM.HEADCOUNT[3]),
                 "[HYPOTHÈSE] +1 support A2, +2 livraison A3"],
                ["Rémunération mensuelle par tête", money(FM.FOUNDER_MONTHLY_TND[1]),
                 money(FM.FOUNDER_MONTHLY_TND[2]), money(FM.FOUNDER_MONTHLY_TND[3]),
                 "[HYPOTHÈSE] sous le marché en A1, au marché en A3"],
                ["Masse salariale", money(y1["payroll_tnd"]), money(y2["payroll_tnd"]),
                 money(y3["payroll_tnd"]), "effectif &times; rémunération &times; 12"],
                ["Autres charges d'exploitation", money(y1["opex_tnd"]), money(y2["opex_tnd"]),
                 money(y3["opex_tnd"]), "infrastructure, juridique, déplacements, marketing"],
                ["**Charges totales**", f"**{money(y1['cost_tnd'])}**",
                 f"**{money(y2['cost_tnd'])}**", f"**{money(y3['cost_tnd'])}**", ""]],
               [40 * mm, 27 * mm, 27 * mm, 27 * mm, 49 * mm],
               align_right=(1, 2, 3), bold_rows=(4,)),

         Spacer(1, 6),
         heading("7.2 &nbsp; Détail des charges d'exploitation", 1),
         table(["Poste", "Année 1", "Année 2", "Année 3", "Remarque"],
               [[fr, money(FM.OPEX_TND[1][k]), money(FM.OPEX_TND[2][k]), money(FM.OPEX_TND[3][k]),
                 note] for k, fr, note in [
                    ("Infrastructure & tooling", "Infrastructure et outillage",
                     "développement et intégration continue seulement &mdash; aucun hébergement client"),
                    ("Legal, accounting, company", "Juridique, comptabilité, société",
                     "constitution, dépôts annuels"),
                    ("Travel & GMP events", "Déplacements et salons BPF",
                     "l'acheteur fréquente les congrès qualité pharmaceutique, pas les salons logiciels"),
                    ("Marketing & collateral", "Marketing et supports",
                     "études de cas et documentation de validation, non de la publicité")]],
               [42 * mm, 25 * mm, 25 * mm, 25 * mm, 53 * mm], align_right=(1, 2, 3)),

         Spacer(1, 6),
         callout("L'avantage structurel de marge : aucune facture cloud par client",
                 "BatchTwin se déploie sur le serveur du client. La dépense d'infrastructure "
                 "reste plate à mesure que les clients s'ajoutent, puisqu'elle ne couvre que "
                 "notre développement et notre intégration continue. Le premier poste de coût "
                 "variable d'un concurrent SaaS &mdash; l'hébergement par locataire &mdash; est "
                 "absent de ce compte de résultat par construction. C'est pourquoi la marge "
                 "brute sur les licences est quasi totale, et pourquoi le coût marginal du "
                 "client suivant est du temps de support et non de l'infrastructure.", "good"),

         Spacer(1, 6),
         heading("7.3 &nbsp; Ce que vaut un client", 1),
         table(["Grandeur", "Valeur", "Mode d'obtention"],
               [["Valeur du contrat de première année", money(MK["avg_first_year_contract_tnd"]),
                 "offre Standard + prestations initiales [CALCULÉ]"],
                ["Valeur récurrente annuelle ensuite", money(FM.PLANS["Standard"]["annual_tnd"]),
                 "licence seule [CALCULÉ]"],
                ["Revenu moyen par compte, année 3", money(y3["arpa_tnd"]),
                 "revenu licences &divide; sites actifs [CALCULÉ]"],
                ["Attrition annuelle supposée", "1 à 2 sites par an",
                 "[HYPOTHÈSE] aucune preuve ; les clients réglementés sont fidèles une fois validés"],
                ["Coût marginal d'un site supplémentaire", "temps de support uniquement",
                 "aucun coût d'hébergement ; voir &sect; 7.2 [CALCULÉ]"]],
               [58 * mm, 38 * mm, 74 * mm], align_right=(1,)),

         Spacer(1, 6),
         heading("7.4 &nbsp; Le problème de la dépendance aux prestations", 1),
         para(f"En année 1, **{pc(y1['services_tnd'] / y1['revenue_tnd'] * 100, 0)}** du chiffre "
              f"d'affaires provient de prestations non récurrentes. En année 3, cette part "
              f"tombe à **{pc(y3['services_tnd'] / y3['revenue_tnd'] * 100, 0)}** [CALCULÉ]. La "
              f"direction est la bonne, mais le chiffre de la première année signifie que "
              f"BatchTwin commence sa vie comme un cabinet de conseil qui possède un logiciel."),
         para("C'est habituel pour un logiciel d'entreprise à ses débuts, et cela reste un "
              "risque, parce que le revenu de prestations ne se capitalise pas et ne survit "
              "pas à la saturation du temps des fondateurs. L'atténuation est explicite : "
              "**chaque heure de déploiement doit réduire les heures nécessaires au "
              "déploiement suivant.** L'analyseur `.docx` incarne déjà ce principe &mdash; "
              "c'est la raison pour laquelle l'intégration prend 20 jours et non des mois "
              "&mdash; et l'objectif suivant est de modéliser le pack de validation, plus gros "
              "livrable manuel restant."),

         Spacer(1, 4),
         kpibox("Chapitre 7 &mdash; indicateurs économiques", [
             ("Charges totales année 1", money(y1["cost_tnd"]), "CALCULÉ", "masse salariale + charges"),
             ("Charges totales année 3", money(y3["cost_tnd"]), "CALCULÉ", "6 personnes"),
             ("Valeur du contrat initial", money(MK["avg_first_year_contract_tnd"]), "CALCULÉ",
              "Standard + prestations"),
             ("Revenu moyen par compte, A3", money(y3["arpa_tnd"]), "CALCULÉ", "licences &divide; sites"),
             ("Coût d'infrastructure par client", "0 TND", "CALCULÉ", "déploiement sur site"),
             ("Part des prestations, A1 &rarr; A3",
              f"{pc(y1['services_tnd'] / y1['revenue_tnd'] * 100, 0)} &rarr; "
              f"{pc(y3['services_tnd'] / y3['revenue_tnd'] * 100, 0)}", "CALCULÉ",
              "décroissante, par conception"),
         ]),
         Spacer(1, 4),
         srcbox(["[15] Glassdoor / levels.fyi / worldsalaries &mdash; salaire ingénieur Tunisie"]),
         PageBreak()]
    return s


def ch8():
    y1, y2, y3 = M[1], M[2], M[3]
    notes_fr = {
        1: "Medicka (référence, remise de 50 % la première année) + 2 clients payants, tous en Tunisie",
        2: "Ouverture du canal des intégrateurs Odoo, Tunisie uniquement",
        3: "Premiers sites maghrébins et premier groupe multi-sites",
    }
    s = [heading("8 &nbsp; Projection financière à trois ans", 0),
         para("Tout ce chapitre est [CALCULÉ] à partir des hypothèses de l'annexe D, via "
              "`docs/finance_model.py`. Modifiez une hypothèse, relancez le modèle, et tous "
              "les chiffres bougent ensemble &mdash; y compris ceux qui dégradent le plan."),

         heading("8.1 &nbsp; Montée en charge clients", 1),
         para("Volontairement lente. Le cycle de vente en fabrication réglementée est de 6 à "
              "12 mois et exige la validation de l'assurance qualité ; tout plan supposant une "
              "adoption rapide par la base en environnement BPF est erroné."),
         Spacer(1, 3),
         table(["Année", "Nouveaux", "Attrition", "Actifs", "Tunisie / Maghreb", "Ce qui se passe"],
               [[str(y), str(FM.RAMP[y]["new"]), str(FM.RAMP[y]["churn"]),
                 str(M[y]["active_sites"]), f"{FM.RAMP[y]['tn']} / {FM.RAMP[y]['mg']}",
                 notes_fr[y]] for y in (1, 2, 3)],
               [16 * mm, 19 * mm, 19 * mm, 16 * mm, 28 * mm, 72 * mm],
               align_right=(1, 2, 3)),

         Spacer(1, 6),
         heading("8.2 &nbsp; Répartition des offres", 1),
         table(["Année", "Essential", "Standard", "Enterprise", "Total sites"],
               [[str(y), str(FM.MIX[y]["Essential"]), str(FM.MIX[y]["Standard"]),
                 str(FM.MIX[y]["Enterprise"]), str(M[y]["active_sites"])] for y in (1, 2, 3)],
               [26 * mm, 34 * mm, 34 * mm, 34 * mm, 42 * mm], align_right=(1, 2, 3, 4)),
         Spacer(1, 4),
         para("Le modèle vérifie par assertion que la répartition des offres égale le nombre "
              "de sites actifs pour chaque année, et échoue bruyamment sinon. Un plan dont la "
              "répartition clients contredit son propre décompte de clients est un plan qu'il "
              "ne faut pas lire plus loin."),

         Spacer(1, 5),
         heading("8.3 &nbsp; Compte de résultat", 1),
         table(["", "Année 1", "Année 2", "Année 3"],
               [["Sites actifs", y1["active_sites"], y2["active_sites"], y3["active_sites"]],
                ["Revenu licences", money(y1["licence_tnd"]), money(y2["licence_tnd"]),
                 money(y3["licence_tnd"])],
                ["Revenu prestations", money(y1["services_tnd"]), money(y2["services_tnd"]),
                 money(y3["services_tnd"])],
                ["**Chiffre d'affaires total**", f"**{money(y1['revenue_tnd'])}**",
                 f"**{money(y2['revenue_tnd'])}**", f"**{money(y3['revenue_tnd'])}**"],
                ["Masse salariale", money(y1["payroll_tnd"]), money(y2["payroll_tnd"]),
                 money(y3["payroll_tnd"])],
                ["Autres charges", money(y1["opex_tnd"]), money(y2["opex_tnd"]), money(y3["opex_tnd"])],
                ["**Charges totales**", f"**{money(y1['cost_tnd'])}**",
                 f"**{money(y2['cost_tnd'])}**", f"**{money(y3['cost_tnd'])}**"],
                ["**Résultat**", f"**{money(y1['profit_tnd'])}**", f"**{money(y2['profit_tnd'])}**",
                 f"**{money(y3['profit_tnd'])}**"],
                ["Marge nette", pc(y1['margin_pct']), pc(y2['margin_pct']),
                 pc(y3['margin_pct'])],
                ["Trésorerie cumulée", money(y1["cumulative_cash_tnd"]),
                 money(y2["cumulative_cash_tnd"]), money(y3["cumulative_cash_tnd"])],
                ["Revenu récurrent annuel de sortie", money(y1["arr_exit_tnd"]),
                 money(y2["arr_exit_tnd"]), money(y3["arr_exit_tnd"])]],
               [50 * mm, 40 * mm, 40 * mm, 40 * mm], align_right=(1, 2, 3),
               bold_rows=(3, 6, 7)),

         Spacer(1, 6),
         callout("Trois points à relever avant de croire ce tableau",
                 f"**Un.** La rentabilité en année 1 dépend de fondateurs acceptant "
                 f"{money(FM.FOUNDER_MONTHLY_TND[1])} par mois. Avec des salaires de marché "
                 f"dès le premier jour, l'année 1 est déficitaire. **Deux.** Le revenu "
                 f"récurrent de sortie de {money(y3['arr_exit_tnd'])} est le chiffre qui "
                 f"compte pour une société de logiciel, pas le total de "
                 f"{money(y3['revenue_tnd'])} &mdash; le revenu de prestations ne se "
                 f"capitalise pas. **Trois.** Chaque nombre de clients de ce tableau est une "
                 f"[HYPOTHÈSE]. L'arithmétique du revenu est solide ; le décompte de clients "
                 f"est une prévision, et le chapitre 9 montre ce qui arrive lorsqu'elle est "
                 f"fausse.", "warn"),

         Spacer(1, 5),
         heading("8.4 &nbsp; Qualité du revenu dans le temps", 1),
         table(["Année", "Licences (récurrent)", "Prestations (ponctuel)", "Part récurrente"],
               [[str(y), money(M[y]["licence_tnd"]), money(M[y]["services_tnd"]),
                 f"{pc(M[y]['licence_tnd'] / M[y]['revenue_tnd'] * 100, 0)}"] for y in (1, 2, 3)],
               [26 * mm, 48 * mm, 48 * mm, 48 * mm], align_right=(1, 2, 3)),
         Spacer(1, 4),
         para(f"La part récurrente passant de "
              f"{pc(y1['licence_tnd'] / y1['revenue_tnd'] * 100, 0)} à "
              f"{pc(y3['licence_tnd'] / y3['revenue_tnd'] * 100, 0)} est la tendance la plus "
              f"importante de ce chapitre. C'est la différence entre construire une société de "
              f"logiciel et exploiter un cabinet de conseil."),

         Spacer(1, 4),
         kpibox("Chapitre 8 &mdash; indicateurs de projection", [
             ("CA année 1", money(y1["revenue_tnd"]), "CALCULÉ", "3 sites + prestations"),
             ("CA année 2", money(y2["revenue_tnd"]), "CALCULÉ", "7 sites"),
             ("CA année 3", money(y3["revenue_tnd"]), "CALCULÉ", "15 sites"),
             ("Revenu récurrent de sortie, A3", money(y3["arr_exit_tnd"]), "CALCULÉ", "licences seules"),
             ("Marge nette année 3", pc(y3['margin_pct']), "CALCULÉ", "résultat &divide; CA"),
             ("Trésorerie cumulée sur 3 ans", money(y3["cumulative_cash_tnd"]), "CALCULÉ",
              "sans financement externe"),
             ("Part de revenu récurrent, A3",
              f"{pc(y3['licence_tnd'] / y3['revenue_tnd'] * 100, 0)}", "CALCULÉ", "licences &divide; total"),
         ]),
         PageBreak()]
    return s


def ch9():
    y3 = M[3]
    sc_fr = {"Price 25% lower": "Prix inférieur de 25 %", "Base case": "Scénario central",
             "Price 25% higher": "Prix supérieur de 25 %",
             "Half the customers": "Moitié moins de clients",
             "Double the customers": "Deux fois plus de clients"}
    s = [heading("9 &nbsp; Seuil de rentabilité et sensibilité", 0),
         para("Une projection ne vaut d'être lue qu'accompagnée des conditions qui la brisent. "
              "Ce chapitre est celui où le plan tente de se réfuter lui-même."),

         heading("9.1 &nbsp; Seuil de rentabilité sur le revenu récurrent", 1),
         para("Le revenu de prestations peut porter l'entreprise au début, mais il ne se "
              "reproduit pas. La question qui compte est le nombre de sites nécessaires pour "
              "que **les licences seules** couvrent la base de coûts."),
         Spacer(1, 3),
         table(["Donnée", "Valeur", "Source"],
               [["Base de coûts annuelle (année 2)", money(BE["annual_cost_tnd"]),
                 "[CALCULÉ] masse salariale + charges"],
                ["Licence moyenne par site", money(BE["avg_licence_tnd"]),
                 "[CALCULÉ] répartition des offres en année 2"],
                ["**Sites nécessaires à l'équilibre**",
                 f"**{num(BE['sites_for_breakeven_on_licence_alone'], 1)}**",
                 "charges &divide; licence moyenne"]],
               [58 * mm, 40 * mm, 72 * mm], align_right=(1,), bold_rows=(2,)),
         Spacer(1, 5),
         para(f"Le plan atteint {num(BE['sites_for_breakeven_on_licence_alone'], 1)} sites au cours de "
              f"l'**année 3**. Avant ce point, l'entreprise est solvable grâce aux prestations "
              f"et à une rémunération de fondateurs sous le marché, non parce que le modèle "
              f"produit fonctionne déjà. Le formuler ainsi est ce qui distingue un plan d'une "
              f"présentation commerciale."),

         Spacer(1, 5),
         heading("9.2 &nbsp; Sensibilité", 1),
         para("Chaque ligne fait varier un seul facteur, tout le reste étant constant, sur "
              "l'année 3 :"),
         Spacer(1, 3),
         table(["Scénario", "CA année 3", "Résultat année 3", "vs central"],
               [[sc_fr.get(r["scenario"], r["scenario"]), money(r["y3_revenue_tnd"]),
                 money(r["y3_profit_tnd"]), pc(r['delta_vs_base_pct'], sign=True)] for r in SENS],
               [54 * mm, 38 * mm, 40 * mm, 38 * mm], align_right=(1, 2, 3), bold_rows=(1,)),

         Spacer(1, 6),
         callout("Le constat qui compte",
                 f"Le prix n'est pas la variable sensible &mdash; une baisse de 25 % coûte "
                 f"{pc(abs(SENS[0]['delta_vs_base_pct']), 0)} du chiffre d'affaires et "
                 f"l'entreprise reste bénéficiaire. **La variable sensible est le nombre de "
                 f"clients.** Le diviser par deux transforme un résultat de "
                 f"{money(y3['profit_tnd'])} en une perte de "
                 f"{money(abs(SENS[3]['y3_profit_tnd']))}. Tout dépend donc de la montée en "
                 f"charge clients, qui est la partie la moins étayée du plan &mdash; ce qui "
                 f"est précisément la raison pour laquelle le chapitre 3 refuse d'énoncer une "
                 f"part de marché qu'il ne peut pas soutenir, et pour laquelle la stratégie "
                 f"commerciale du chapitre 10 s'articule autour d'un client de référence "
                 f"plutôt que d'un budget marketing.", "bad"),

         Spacer(1, 6),
         heading("9.3 &nbsp; Ce qui devrait être vrai", 1),
         para("Pour que ce plan fonctionne, tout ce qui suit doit tenir. La défaillance d'un "
              "seul élément est significative :"),
         ] + bullets([
        "**Medicka devient un client de référence en production.** Sans un site BPF nommé en "
        "exploitation, la montée en charge de l'année 2 n'a pas de moteur.",
        "**Environ un nouveau site par trimestre est signé à partir de l'année 2.** Sur un "
        "cycle de 6 à 12 mois, cela suppose un portefeuille de 8 à 12 prospects qualifiés "
        "maintenu en permanence &mdash; ce qui exige le décompte de marché dont le chapitre 3 "
        "dit que nous ne disposons pas.",
        "**Le déploiement reste proche de 20 jours.** Si l'intégration réelle prend 40 jours, "
        "les prestations cessent d'être rentables et consomment la capacité de livraison dont "
        "dépend la croissance de l'année 3.",
        "**L'intégration Odoo réelle fonctionne sur un site client.** Non démontré à ce jour ; "
        "risque R1.",
        "**L'attrition reste à 1 ou 2 sites par an.** Plausible pour des systèmes validés, "
        "mais totalement non étayé &mdash; nous n'avons jamais eu de client susceptible de "
        "partir.",
    ]) + [
        Spacer(1, 5),
        heading("9.4 &nbsp; Le scénario défavorable, énoncé", 1),
        para(f"Si la montée en charge est divisée par deux &mdash; trois sites en année 2 au "
             f"lieu de cinq, et cinq en année 3 au lieu de dix &mdash; le chiffre d'affaires "
             f"de l'année 3 s'établit vers **{money(SENS[3]['y3_revenue_tnd'])}** face à une "
             f"base de coûts de **{money(y3['cost_tnd'])}**, soit une perte d'environ "
             f"**{money(abs(SENS[3]['y3_profit_tnd']))}** [CALCULÉ]. L'entreprise ne disparaît "
             f"pas à ce stade, la base de coûts étant essentiellement composée de salaires de "
             f"fondateurs qui peuvent être réduits de nouveau, mais elle cesse d'être une "
             f"entreprise de croissance pour devenir un cabinet de conseil à deux clients."),
        para("Le signal honnête à surveiller n'est pas le chiffre d'affaires. C'est **le fait "
             "que le deuxième client se signe sans qu'un fondateur soit dans la pièce.** Tant "
             "que cela ne s'est pas produit, la stratégie commerciale n'est pas démontrée, "
             "quoi qu'affiche la ligne de revenus."),

        Spacer(1, 4),
        kpibox("Chapitre 9 &mdash; indicateurs de risque", [
            ("Sites à l'équilibre, licences seules",
             f"{num(BE['sites_for_breakeven_on_licence_alone'], 1)}", "CALCULÉ", "charges &divide; licence moyenne"),
            ("Année d'atteinte", "Année 3", "CALCULÉ", "montée en charge clients"),
            ("Effet d'une baisse de prix de 25 %", pc(SENS[0]['delta_vs_base_pct'], sign=True),
             "CALCULÉ", "reste bénéficiaire"),
            ("Effet de moitié moins de clients", pc(SENS[3]['delta_vs_base_pct'], sign=True),
             "CALCULÉ", f"perte de {money(abs(SENS[3]['y3_profit_tnd']))}"),
            ("Facteur le plus sensible", "nombre de clients", "CALCULÉ", "et non le prix"),
            ("Portefeuille requis dès A2", "8 à 12 qualifiés", "CALCULÉ",
             "1 signature/trimestre sur cycle de 6-12 mois"),
        ]),
        PageBreak()]
    return s
