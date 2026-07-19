"""Édition française — chapitres 10 à 14, annexes, références."""
from __future__ import annotations

from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, Spacer

import finance_model as FM
from build_business_plan import (M, UE, BE, SENS, MK, SVC, SS, bullets, callout,
                                 heading, kpibox, money, num, para, pc, rule,
                                 srcbox, table)


def ch10():
    s = [heading("10 &nbsp; Stratégie commerciale", 0),
         para("La contrainte qui structure tout : **le cycle de vente en fabrication "
              "réglementée est de 6 à 12 mois et passe par la validation de l'assurance "
              "qualité.** Ce n'est pas un produit en libre-service. Tout plan supposant une "
              "adoption rapide par la base est erroné, et aucun budget marketing ne comprime "
              "une décision de validation."),

         heading("10.1 &nbsp; Trois canaux, par ordre de priorité", 1),

         heading("10.1.1 &nbsp; Medicka comme client de référence", 2),
         para(f"Un site BPF nommé en production vaut plus que n'importe quelle action "
              f"marketing. L'échange est explicite : une tarification préférentielle la "
              f"première année &mdash; une remise de {FM.REFERENCE_DISCOUNT:.0%} est modélisée "
              f"[HYPOTHÈSE] &mdash; contre une étude de cas, une visite de site pour les "
              f"prospects qualifiés, et l'autorisation d'utiliser le nom."),
         para("Ce qui fait la valeur de la référence n'est pas le logo. C'est que le directeur "
              "qualité d'un prospect peut téléphoner au directeur qualité de Medicka et poser "
              "la seule question qui compte : *un inspecteur l'a-t-il accepté ?*"),

         heading("10.1.2 &nbsp; Le canal des intégrateurs Odoo", 2),
         para("Les intégrateurs vendent déjà à ce segment précis et cherchent une "
              "différenciation verticale. La forme habituelle est un partage de marge sur la "
              "licence, les prestations restant chez le partenaire. Le pourcentage relève de "
              "la négociation et non d'un chiffre à publier avant qu'elle n'ait eu lieu "
              "&mdash; **aucun intégrateur n'a encore été approché**, et c'est la question "
              "ouverte n° 5."),
         para("Stratégiquement, ce canal compte davantage que sa part de revenu ne le suggère : "
              "c'est la seule voie qui fait croître les ventes sans temps de fondateur, et le "
              "chapitre 9 identifie « le deuxième client signé sans fondateur dans la pièce » "
              "comme le véritable signal que l'entreprise fonctionne."),

         heading("10.1.3 &nbsp; Les congrès réglementaires", 2),
         para(f"L'acheteur fréquente les congrès BPF et qualité pharmaceutique, pas les salons "
              f"logiciels. Le budget de déplacement du chapitre 7 est dimensionné pour cela et "
              f"constitue le poste de charge à la croissance la plus rapide, passant de "
              f"{money(FM.OPEX_TND[1]['Travel & GMP events'])} à "
              f"{money(FM.OPEX_TND[3]['Travel & GMP events'])} [HYPOTHÈSE]."),

         Spacer(1, 5),
         heading("10.2 &nbsp; Le déroulé de vente", 1),
         table(["Étape", "Contenu", "Durée"],
               [["Qualification", "Confirmer le périmètre BPF, la présence d'un ERP, le "
                 "dossier de lot encore papier, 50 à 300 salariés. Écarter les sites dotés "
                 "d'un MES validé.", "1 à 2 semaines"],
                ["Analyse de leur dossier", "Le prospect envoie un dossier `.docx` réel. Nous "
                 "le renvoyons sous forme de formulaire tablette fonctionnel. **C'est le "
                 "différenciateur et cela doit se produire dès le premier rendez-vous.**",
                 "Séance même"],
                ["Évaluation technique", "L'AQ examine la piste d'audit, les signatures, les "
                 "barrières. L'informatique confirme l'accès Odoo en lecture seule.",
                 "4 à 8 semaines"],
                ["Revue de validation", "CDC convenu ; périmètre QI/QO/QP défini. L'étape la "
                 "plus lente, et celle que les concurrents ne compriment pas davantage.",
                 "8 à 16 semaines"],
                ["Marche parallèle", "Les deux systèmes en service ; les écarts sont "
                 "consignés. Voir le chapitre 11.", "4 à 8 semaines"],
                ["Bascule", "Le papier est retiré étape par étape.", "2 à 4 semaines"]],
               [34 * mm, 102 * mm, 34 * mm]),

         Spacer(1, 6),
         heading("10.3 &nbsp; La démonstration qui emporte la vente", 1),
         callout("Analyser le dossier du prospect, en direct",
                 "La démonstration de tout concurrent montre *ses* formulaires. La nôtre "
                 "montre celui du prospect. Un directeur qualité qui voit son propre modèle "
                 "DCT &mdash; celui qu'il a rédigé, avec son tableau de compression de "
                 "95 lignes &mdash; devenir un formulaire tablette devant lui n'évalue plus "
                 "une liste de fonctionnalités. Sur les quatre dossiers de Medicka, cela a "
                 "produit 1 205 champs sans aucune retranscription [MESURÉ]. C'est l'élément "
                 "le plus efficace de toute la stratégie commerciale, et il coûte un "
                 "rendez-vous.", "good"),

         Spacer(1, 6),
         heading("10.4 &nbsp; Traitement des objections", 1),
         table(["Objection", "Réponse", "Pourquoi elle tient"],
               [["« Est-ce validé ? »", "Non, et aucun éditeur ne peut valider votre procédé à "
                 "votre place. Nous fournissons CDC/QI/QO/QP et le code source pour que votre "
                 "équipe de validation le qualifie.",
                 "Honnête, et la remise du code source est assez inhabituelle pour marquer"],
                ["« Et si cela corrompt notre Odoo ? »", "C'est impossible. Nous n'écrivons "
                 "jamais dans Odoo.", "Architectural, et non une promesse contractuelle"],
                ["« Nos données ne peuvent pas quitter le pays. »", "Elles ne quittent jamais "
                 "votre serveur. L'IA s'exécute également en local.", "Déploiement sur site par défaut"],
                ["« Nous ne pouvons pas arrêter la production pour migrer. »", "Vous ne "
                 "l'arrêtez pas. Marche parallèle, puis bascule étape par étape, l'AQ gardant "
                 "la main sur le basculement.", "Imposé dans le code ; voir le chapitre 11"],
                ["« Que se passe-t-il si un capteur tombe en panne ? »", "Modes de défaillance "
                 "documentés, détection de péremption de la donnée, et saisie manuelle avec "
                 "marquage de provenance.", "Réalisé ; `resilience.py`"],
                ["« Vous êtes trois personnes. »", "Exact, et c'est le vrai risque. Séquestre "
                 "du code pour l'offre Enterprise ; le code source vous appartient de toute "
                 "façon.", "N'escamote pas le risque"]],
               [42 * mm, 66 * mm, 62 * mm]),

         Spacer(1, 5),
         kpibox("Chapitre 10 &mdash; indicateurs commerciaux", [
             ("Cycle de vente", "6 à 12 mois", "SOURCÉ", "norme en fabrication réglementée"),
             ("Délai d'analyse d'un dossier prospect", "séance même", "MESURÉ", "analyseur docx"),
             ("Remise client de référence", f"{FM.REFERENCE_DISCOUNT:.0%}", "HYPOTHÈSE", "année 1 uniquement"),
             ("Portefeuille requis dès A2", "8 à 12 qualifiés", "CALCULÉ", "1 signature par trimestre"),
             ("Intégrateurs approchés", "0", "&mdash;", "question ouverte n° 5"),
             ("Budget déplacements, A1 &rarr; A3",
              f"{money(FM.OPEX_TND[1]['Travel & GMP events'])} &rarr; "
              f"{money(FM.OPEX_TND[3]['Travel & GMP events'])}", "HYPOTHÈSE", "congrès BPF"),
         ]),
         PageBreak()]
    return s


def ch11():
    s = [heading("11 &nbsp; Migration et déploiement", 0),
         para("L'objection qui tue les affaires eBR n'est pas le prix. C'est **« nous ne "
              "pouvons pas arrêter de produire pendant que vous installez un logiciel ».** Les "
              "travaux d'intégration causent plus de retard que toute autre partie d'un projet "
              "eBR [SOURCÉ], et un site BPF qui interrompt sa production pour accommoder un "
              "projet informatique a commis une erreur commerciale irrattrapable."),

         heading("11.1 &nbsp; Marche parallèle, puis bascule par étapes", 1),
         para("BatchTwin n'exige jamais de bascule brutale. Chaque lot porte un **mode "
              "d'exécution** &mdash; papier, parallèle ou numérique &mdash; et seule l'AQ peut "
              "le modifier. Pendant la marche parallèle, les deux systèmes sont en service : le "
              "dossier papier demeure le dossier légal, et BatchTwin fonctionne à côté en "
              "capturant les mêmes données."),
         Spacer(1, 3),
         table(["Phase", "Dossier légal", "Ce qu'elle démontre", "Durée typique"],
               [["Papier", "Papier", "Situation de référence. Rien n'a encore changé.", "&mdash;"],
                ["Parallèle", "Papier", "Que le dossier numérique concorde avec le dossier "
                 "papier, lot par lot. Les écarts sont le livrable.", "4 à 8 semaines"],
                ["Numérique", "BatchTwin", "Bascule, étape par étape &mdash; fabrication en "
                 "premier, libération en dernier.", "2 à 4 semaines"]],
               [26 * mm, 28 * mm, 82 * mm, 34 * mm]),
         Spacer(1, 5),
         para("Le mode d'exécution est imposé dans le code plutôt que décrit dans un manuel, "
              "et seul un rôle AQ peut le faire avancer. Une politique de migration qui vit "
              "dans une présentation est une politique ; celle qu'un utilisateur non-AQ ne "
              "peut physiquement pas déclencher est un contrôle."),

         Spacer(1, 5),
         callout("La marche parallèle est aussi ce qui donne au dossier économique son chiffre manquant",
                 "Le produit le plus précieux de la marche parallèle n'est pas la confiance "
                 "dans le logiciel. C'est **la première mesure réelle de la perte matière** "
                 "&mdash; le chiffre qu'Odoo est structurellement incapable de produire, et la "
                 "seule donnée sans laquelle la feuille de calcul de retour sur investissement "
                 "du &sect; 11.3 ne peut pas être complétée. Toute marche parallèle doit être "
                 "cadrée pour le capturer délibérément et non incidemment.", "good"),

         Spacer(1, 5),
         heading("11.2 &nbsp; Fonctionner dans une usine réelle", 1),
         para("Un atelier BPF n'est pas un bureau. Le système est conçu pour les conditions "
              "qu'il rencontrera effectivement :"),
         ] + bullets([
        "**Hors ligne d'abord.** Formulaires, pesée, saisie de contrôle qualité, listes de "
        "vérification et conditionnement fonctionnent sans réseau et se synchronisent "
        "ensuite. **Les signatures, délibérément, non** &mdash; une signature Part 11 exige "
        "une vérification d'identité en direct, et mettre les signatures en file d'attente "
        "hors ligne détruirait le contrôle qu'elles existent pour assurer.",
        "**La panne de capteur est un état prévu, non une exception.** Huit modes de "
        "défaillance sont modélisés, avec des seuils de péremption (120 secondes pour une "
        "donnée périmée, 600 secondes pour une donnée morte) et un marquage de provenance : "
        "un lecteur peut toujours savoir si une valeur vient d'un instrument, d'un opérateur, "
        "ou d'un cache périmé.",
        "**Tablettes partagées, identité individuelle.** Les opérateurs signent avec leurs "
        "propres identifiants sur un appareil partagé ; la tarification est par site "
        "précisément pour que personne ne soit tenté de partager un compte.",
        "**Instruments existants, qualification existante.** En production, BatchTwin lit les "
        "instruments que l'usine possède déjà et qualifie déjà, via OPC UA, Modbus TCP, "
        "S7/PROFINET et EtherNet/IP. Le banc de démonstration utilisé pendant le "
        "développement est un banc d'essai, non une proposition de déploiement &mdash; un "
        "site BPF ne pose pas une platine d'essai sur une ligne validée.",
    ]) + [
        Spacer(1, 5),
        heading("11.3 &nbsp; La feuille de calcul du retour sur investissement", 1),
        para("Il n'y a pas de chiffre de retour sur investissement dans ce plan d'affaires, "
             "parce qu'en calculer un honnêtement exige quatre données que seul le client "
             "possède. Les inventer produirait un total péremptoire qui s'effondrerait à la "
             "première question sur son origine."),
        Spacer(1, 3),
        table(["Donnée", "Ce qu'il faut demander", "Qui la connaît"],
              [["L", "Lots produits par an", "Responsable de production &mdash; connu aujourd'hui"],
               ["H", "Heures passées par l'AQ à relire un dossier de lot papier",
                "AQ &mdash; connu aujourd'hui"],
               ["C", "Coût horaire chargé d'un relecteur AQ", "Finance &mdash; connu aujourd'hui"],
               ["M", "Coût matière d'un lot moyen", "Finance &mdash; connu aujourd'hui"],
               ["**perte %**", "**Perte matière réelle par lot**",
                "**Personne. Odoo ne peut pas la produire. La marche parallèle la crée.**"]],
              [20 * mm, 74 * mm, 76 * mm], bold_rows=(4,)),
        Spacer(1, 4),
        para("L'arithmétique devient alors triviale :"),
        Paragraph("Relecture AQ economisee = L &times; H &times; 0,40 &times; C &nbsp;&nbsp; "
                  "<i>(0,40 est le BAS de la fourchette publiee de 40-60 %)</i><br/>"
                  "Perte matiere revelee &nbsp;= L &times; M &times; perte %<br/>"
                  "Benefice annuel &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;= relecture + perte matiere + "
                  "deviations evitees<br/>"
                  "Retour sur investissement = (abonnement + deploiement) &divide; benefice annuel",
                  SS["Code"]),
        Spacer(1, 4),
        para("**Références publiées pour la catégorie** &mdash; pour cadrer la conversation, "
             "jamais pour être citées comme résultats mesurés de BatchTwin :"),
        Spacer(1, 3),
        table(["Référence", "Valeur", "Source"],
              [["Réduction du délai de libération des lots", "40 à 60 %", "[SOURCÉ] réf. [4]"],
               ["Effort de relecture AQ", "sensiblement réduit par la revue par exception",
                "[SOURCÉ] réf. [5]"],
               ["Réduction des erreurs, saisie directe vs manuelle",
                "jusqu'à 95 % (un établissement)", "[SOURCÉ] réf. [16]"],
               ["Délai typique de retour sur investissement", "12 à 18 mois", "[SOURCÉ] réf. [12]"]],
              [74 * mm, 44 * mm, 52 * mm]),

        Spacer(1, 6),
        heading("11.4 &nbsp; Pourquoi l'efficacité seule ne justifiera pas l'achat", 1),
        para("Appliquez la formule avec des données plausibles pour un site de la taille de "
             "Medicka : le temps de relecture AQ domine tous les autres termes ; la perte "
             "matière et la péremption sont des arrondis à côté. Le bénéfice croît "
             "linéairement avec le nombre de lots, l'abonnement non &mdash; en dessous de "
             "quelques centaines de lots par an, le calcul est marginal et la recommandation "
             "honnête est l'offre la plus petite."),
        para("**L'achat se justifie par le risque, non par l'efficacité.** Une non-conformité "
             "réglementaire sur les dossiers de lot est existentielle pour un site BPF : perte "
             "de certification, arrêt des exportations, coûts de remédiation sans commune "
             "mesure avec un abonnement. Un rappel de lot dû à une dérive de remplissage non "
             "détectée l'est tout autant. Un audit client raté coûte le compte. La réponse de "
             "BatchTwin à chacun de ces cas est concrète &mdash; la chaîne d'empreintes avec "
             "ancrage externe, les signatures Part 11, une barrière de libération "
             "infranchissable, et une prévision MSP qui alerte avant le franchissement de "
             "spécification."),
        para("C'est une tarification d'assurance plutôt que d'efficacité, ce qui explique "
             "précisément pourquoi l'acheteur est la personne qui signe personnellement la "
             "libération, et pourquoi le discours commence par la traçabilité."),

        Spacer(1, 4),
        kpibox("Chapitre 11 &mdash; indicateurs de déploiement", [
            ("Arrêt de production requis", "aucun", "MESURÉ", "machine à états du mode d'exécution"),
            ("Durée de marche parallèle", "4 à 8 semaines", "HYPOTHÈSE", "aucun client n'en a encore mené"),
            ("Changement de mode autorisé à", "rôle AQ uniquement", "MESURÉ", "store.set_run_mode()"),
            ("Actions disponibles hors ligne", "6 types sur 7", "MESURÉ", "signatures exclues par conception"),
            ("Modes de défaillance capteur modélisés", "8", "MESURÉ", "resilience.py"),
            ("Seuils péremption / mort", "120 s / 600 s", "MESURÉ", "resilience.py"),
            ("Réduction publiée du délai de libération", "40 à 60 %", "SOURCÉ",
             "réf. [4] &mdash; la catégorie, pas nous"),
            ("Chiffre de retour sur investissement propre", "non énoncé", "&mdash;",
             "exige les données du client"),
        ]),
        Spacer(1, 4),
        srcbox(["[4] iFactory &mdash; délai de libération eBR",
                "[5] MasterControl &mdash; revue par exception", "[12] BatchLine", "[13] A3P",
                "[16] Pharmaceutical Technology &mdash; réduction des erreurs"]),
        PageBreak()]
    return s


def ch12():
    risks = [
        ("R1", "L'intégration Odoo réelle échoue sur un site client", "Élevé", "Moyenne",
         "Les adaptateurs simulé et réel partagent un test de contrat. La lecture seule par "
         "construction limite le rayon d'impact. **Lacune : aucun Odoo de production n'a été "
         "éprouvé.** Première action de la mission Medicka."),
        ("R2", "Marché adressable plus petit que supposé", "Élevé", "Moyenne",
         "Reconnu ouvertement au chapitre 3. Recenser la population compléments et cosmétique "
         "est la question ouverte n° 1 et coûte des semaines, pas de l'argent."),
        ("R3", "La montée en charge clients n'est pas atteinte", "Élevé", "Moyenne",
         "La variable la plus sensible du modèle (&sect; 9.2). Atténué par des coûts fixes "
         "faibles &mdash; la rémunération des fondateurs peut être réduite de nouveau &mdash; "
         "et par le canal des intégrateurs."),
        ("R4", "Le déploiement dépasse largement 20 jours", "Moyen", "Moyenne",
         "La marge sur prestations s'évapore et la capacité de livraison est consommée. Atténué "
         "par l'analyseur et par la modélisation à venir du pack de validation."),
        ("R5", "Dépendance aux trois fondateurs", "Élevé", "Élevée",
         "Réel et non soluble à cette taille. La remise du code source et le séquestre "
         "Enterprise protègent le client même dans le pire scénario."),
        ("R6", "Un concurrent développe un analyseur `.docx`", "Moyen", "Faible-moyenne",
         "Deux ans d'avance au mieux. La barrière durable est l'accumulation de modèles, de "
         "profils et de bases de cas de déviations &mdash; d'où la priorité donnée aux clients "
         "de référence sur la marge en année 1."),
        ("R7", "La charge de validation dépasse notre capacité", "Élevé", "Moyenne",
         "Nous fournissons CDC/QI/QO/QP et le code source ; l'équipe de validation du client "
         "le qualifie. Les modèles n'existent pas encore &mdash; première lacune produit."),
        ("R8", "Une évolution réglementaire invalide une approche", "Moyen", "Faible",
         "Les mises à jour réglementaires sont incluses dans l'abonnement : le client ne reçoit "
         "jamais de facture de conformité. Le coût est porté par nous."),
        ("R9", "Exposition de change et macroéconomique", "Faible", "Moyenne",
         "Coûts et revenus sont tous deux en TND, d'où une couverture naturelle. L'expansion "
         "maghrébine en année 3 introduit une exposition."),
        ("R10", "Modèle de vision trop faible pour l'OCR d'étiquettes", "Faible", "Certaine",
         "Déjà avéré. La saisie manuelle est le chemin principal ; l'interface nomme le modèle "
         "et la limitation. Se résout par un modèle plus grand, non par du code."),
    ]
    s = [heading("12 &nbsp; Registre des risques", 0),
         para("Classés par le produit de l'impact et de la probabilité. Rien n'y est présenté "
              "comme résolu qui ne le soit pas."),
         Spacer(1, 3),
         table(["N°", "Risque", "Impact", "Probabilité", "Position"],
               [[a, b, c, d, e] for a, b, c, d, e in risks],
               [11 * mm, 42 * mm, 16 * mm, 20 * mm, 81 * mm]),

         Spacer(1, 6),
         heading("12.1 &nbsp; Questions ouvertes, par ordre de priorité", 1),
         para("Voici ce que nous chercherions à résoudre en premier, et aucune de ces questions "
              "n'exige de financement &mdash; seulement de l'accès et du temps :"),
         Spacer(1, 3),
         table(["N°", "Question", "Comment y répondre", "Coût"],
               [["1", "Combien de fabricants tunisiens de compléments, cosmétiques et "
                 "dispositifs entrent dans notre cible ?", "Agréger les enregistrements "
                 "ANCSEP, les listes de certificats ISO 22716 et les annuaires de fédérations "
                 "professionnelles.", "2 à 3 semaines de recherche documentaire"],
                ["2", "Quelle est la perte matière réelle par lot ?", "Un mois de pesée en "
                 "marche parallèle chez Medicka.", "Inclus dans le pilote"],
                ["3", "Que paieront réellement les clients ?", "Trois entretiens clients. "
                 "Remplace tout le chapitre 6 par des preuves.", "Trois rendez-vous"],
                ["4", "Quelles sont les quatre données de retour sur investissement chez "
                 "Medicka ?", "Les demander. Toutes les quatre leur sont connues aujourd'hui "
                 "(&sect; 11.3).", "Un rendez-vous"],
                ["5", "Quelle marge un intégrateur Odoo acceptera-t-il ?", "En approcher deux.",
                 "Deux rendez-vous"],
                ["6", "L'adaptateur Odoo réel fonctionne-t-il en production ?", "Se connecter à "
                 "l'instance de Medicka, en lecture seule.", "Une journée"],
                ["7", "Les acheteurs BPF de ce segment préfèrent-ils vraiment l'hébergement sur "
                 "site ?", "Affirmé par conservatisme, jamais mesuré. À poser dans les mêmes "
                 "trois entretiens.", "Gratuit"]],
               [10 * mm, 52 * mm, 66 * mm, 42 * mm]),

         Spacer(1, 6),
         callout("Ce que nous répondrions à un évaluateur demandant « combien ça coûte ? »",
                 "Nous n'avons pas encore fixé de prix. Voici la fourchette dans laquelle il "
                 "doit se situer et pourquoi &mdash; au-dessus de leur facture Odoo, un ordre "
                 "de grandeur en dessous d'un MES d'entreprise &mdash; voici la position "
                 "d'ouverture que cette fourchette produit, et voici les trois entretiens "
                 "clients qui la remplaceront par des preuves. Cette réponse est respectable "
                 "et vérifiable. Un chiffre d'apparence précise sans origine n'est ni l'un ni "
                 "l'autre, et il appelle exactement une question à laquelle il n'existe pas de "
                 "bonne réponse.", "info"),

         Spacer(1, 5),
         kpibox("Chapitre 12 &mdash; indicateurs de risque", [
             ("Risques à impact élevé", "5 sur 10", "CALCULÉ", "registre ci-dessus"),
             ("Risques avec lacune non couverte", "R1, R7", "&mdash;", "énoncés, non dissimulés"),
             ("Questions ouvertes exigeant un financement", "0 sur 7", "CALCULÉ",
              "toutes exigent de l'accès, pas de l'argent"),
             ("Question ouverte la plus longue", "2 à 3 semaines", "HYPOTHÈSE", "recensement du marché"),
             ("Hypothèses listées en annexe D", "20", "MESURÉ", "comptées depuis finance_model.py"),
         ]),
         PageBreak()]
    return s


def ch13():
    s = [heading("13 &nbsp; Cadre d'indicateurs", 0),
         para("Ce que nous mesurerions pour savoir si le plan fonctionne, séparé selon la "
              "question auquel chaque ensemble répond. Un indicateur sur lequel personne "
              "n'agirait est un ornement ; chaque métrique ci-dessous a un déclencheur énoncé."),

         heading("13.1 &nbsp; Indicateurs produit &mdash; est-il bon ?", 1),
         table(["Indicateur", "Aujourd'hui", "Cible", "Qui agit"],
               [["Champs de dossier numérisés par client", "1 205 [MESURÉ]", "&gt; 1 000",
                 "Livraison &mdash; en dessous, l'analyseur doit être retravaillé pour ce client"],
                ["Jours de déploiement par site", "20 [HYPOTHÈSE]", "&le; 20 et décroissant",
                 "Livraison &mdash; au-delà de 30, la marge sur prestations disparaît"],
                ["Tests automatisés au vert", "143 [MESURÉ]", "aucune régression", "Ingénierie"],
                ["Génération du dossier de lot", "un clic [MESURÉ]", "inchangé", "Produit"],
                ["Déviations clôturées citant le conseiller", "s. o.", "&gt; 50 %",
                 "Produit &mdash; mesure si l'intelligence adaptative est utilisée, pas "
                 "seulement construite"]],
               [56 * mm, 30 * mm, 32 * mm, 52 * mm]),

         Spacer(1, 5),
         heading("13.2 &nbsp; Indicateurs client &mdash; fonctionne-t-il en usine ?", 1),
         table(["Indicateur", "Mode de mesure", "Déclencheur"],
               [["Perte matière par lot", "bilan matière vs nomenclature, chaque lot",
                 "**Le chiffre qui n'existe pas aujourd'hui.** La première valeur réelle est un jalon."],
                ["Délai de libération des lots", "horodatages de signature, papier vs numérique",
                 "En dessous du bas de fourchette publié de 40 %, examiner le flux"],
                ["Heures de relecture AQ par lot", "déclaré par le client, avant et après",
                 "Le terme dominant du retour sur investissement (&sect; 11.4)"],
                ["Taux de récidive des déviations", "base de cas du conseiller",
                 "Une récidive croissante signifie que les CAPA ne tiennent pas"],
                ["Alertes MSP avant franchissement", "prévision vs réel",
                 "Une alerte qui arrive après le franchissement ne vaut rien"],
                ["Écarts en marche parallèle", "numérique vs papier, par lot",
                 "Doivent tendre vers zéro avant la bascule"]],
               [48 * mm, 52 * mm, 70 * mm]),

         Spacer(1, 5),
         heading("13.3 &nbsp; Indicateurs commerciaux &mdash; est-ce une entreprise ?", 1),
         table(["Indicateur", "Année 1", "Année 2", "Année 3", "Pourquoi il compte"],
               [["Sites actifs", str(M[1]["active_sites"]), str(M[2]["active_sites"]),
                 str(M[3]["active_sites"]), "la variable la plus sensible du modèle"],
                ["Revenu récurrent de sortie", money(M[1]["arr_exit_tnd"]),
                 money(M[2]["arr_exit_tnd"]), money(M[3]["arr_exit_tnd"]),
                 "la vraie mesure, pas le chiffre d'affaires total"],
                ["Part de revenu récurrent",
                 f"{pc(M[1]['licence_tnd'] / M[1]['revenue_tnd'] * 100, 0)}",
                 f"{pc(M[2]['licence_tnd'] / M[2]['revenue_tnd'] * 100, 0)}",
                 f"{pc(M[3]['licence_tnd'] / M[3]['revenue_tnd'] * 100, 0)}",
                 "société de logiciel ou cabinet de conseil"],
                ["Revenu moyen par compte", money(M[1]["arpa_tnd"]), money(M[2]["arpa_tnd"]),
                 money(M[3]["arpa_tnd"]), "santé de la répartition des offres"],
                ["Marge nette", pc(M[1]['margin_pct']), pc(M[2]['margin_pct']),
                 pc(M[3]['margin_pct']), "flattée par la rémunération des fondateurs jusqu'en A3"],
                ["Sites vs seuil de rentabilité",
                 f"{M[1]['active_sites']} / {num(BE['sites_for_breakeven_on_licence_alone'], 1)}",
                 f"{M[2]['active_sites']} / {num(BE['sites_for_breakeven_on_licence_alone'], 1)}",
                 f"{M[3]['active_sites']} / {num(BE['sites_for_breakeven_on_licence_alone'], 1)}",
                 "quand le modèle produit fonctionne réellement"]],
               [38 * mm, 25 * mm, 25 * mm, 25 * mm, 57 * mm], align_right=(1, 2, 3)),

         Spacer(1, 5),
         heading("13.4 &nbsp; Les trois indicateurs avancés", 1),
         para("Le chiffre d'affaires est un indicateur retardé sur un cycle de vente de 6 à "
              "12 mois &mdash; quand il bouge, la décision qui l'a causé remonte à deux "
              "trimestres. Ces trois-là bougent en premier :"),
         ] + bullets([
        "**Le deuxième client s'est-il signé sans fondateur dans la pièce ?** Tant que cela "
        "ne s'est pas produit, la stratégie commerciale n'est pas démontrée, quel que soit le "
        "chiffre d'affaires.",
        "**Le temps de déploiement décroît-il d'un client à l'autre ?** Un temps constant "
        "signifie que nous sommes un cabinet de conseil. Un temps décroissant signifie que le "
        "produit absorbe le travail.",
        "**Un directeur qualité client nous a-t-il recommandés spontanément à un pair ?** Sur "
        "un marché aussi restreint et aussi conservateur, la recommandation entre pairs est "
        "le seul canal marketing qui se capitalise.",
    ]) + [
        Spacer(1, 5),
        kpibox("Chapitre 13 &mdash; synthèse du cadre", [
            ("Indicateurs produit définis", "5", "MESURÉ", "&sect; 13.1"),
            ("Indicateurs client définis", "6", "MESURÉ", "&sect; 13.2"),
            ("Indicateurs commerciaux définis", "6", "MESURÉ", "&sect; 13.3"),
            ("Indicateurs avancés", "3", "MESURÉ", "&sect; 13.4"),
            ("Indicateurs mesurables aujourd'hui", "ensemble produit seulement", "&mdash;",
             "l'ensemble client exige un site en exploitation"),
        ]),
        PageBreak()]
    return s


def ch14():
    y3 = M[3]
    s = [heading("14 &nbsp; Feuille de route et conclusion", 0),

         heading("14.1 &nbsp; Feuille de route", 1),
         table(["Horizon", "Objectif", "Pourquoi cet ordre"],
               [["3 prochains mois", "Pilote Medicka : connexion Odoo réelle, marche "
                 "parallèle, première mesure réelle de perte matière.",
                 "Ferme R1 et les questions ouvertes 2, 4 et 6 d'un seul coup. Rien d'autre ne "
                 "devrait commencer avant."],
                ["3 à 6 mois", "Pack de validation modélisé (CDC/QI/QO/QP). Recensement du "
                 "marché achevé. Trois entretiens de tarification.",
                 "R7 est la première lacune produit ; les questions ouvertes 1 et 3 sont les "
                 "premières lacunes commerciales."],
                ["6 à 12 mois", "Deux clients payants au-delà de Medicka. Premier partenariat "
                 "intégrateur. Étude de cas publiée.",
                 "Démontre que la vente est reproductible sans fondateur dans la pièce."],
                ["Année 2", "Canal des intégrateurs Odoo alimentant le portefeuille. Tableau "
                 "de bord hybride multi-sites pour l'offre Enterprise.",
                 "La seule voie qui fait croître les ventes sans temps de fondateur."],
                ["Année 3", "Premiers sites maghrébins. Profils verticaux au-delà du "
                 "pharmaceutique démontrés en production.",
                 "Expansion géographique et sectorielle, une fois la mécanique démontrée à "
                 "domicile."]],
               [30 * mm, 68 * mm, 72 * mm]),

         Spacer(1, 6),
         heading("14.2 &nbsp; Ce qui nous ferait changer d'avis", 1),
         para("Un plan qui ne peut pas être réfuté n'est pas un plan. Signaux précis qui nous "
              "feraient changer de cap plutôt que forcer :"),
         ] + bullets([
        "**Le recensement du marché revient faible.** Si la population adressable tunisienne "
        "est réellement inférieure à une quarantaine de sites, le plan domestique seul ne "
        "porte pas une entreprise et l'expansion maghrébine passe de l'année 3 à l'année 1.",
        "**Trois directeurs qualité déclarent qu'ils n'achèteront pas en hébergement sur "
        "site.** L'hypothèse de déploiement est affirmée par conservatisme, non mesurée. Si "
        "elle est fausse, toute la structure de coûts change et l'avantage de marge du "
        "chapitre 7 disparaît.",
        "**Le déploiement prend plus de 40 jours chez le deuxième client.** Cela signifierait "
        "que l'analyseur se généralise moins bien que mesuré sur les quatre dossiers de "
        "Medicka, ce qui est le pari produit central.",
        "**Odoo publie un module eBR conforme.** Peu probable &mdash; ce n'est pas leur marché "
        "&mdash; mais cela supprimerait entièrement notre angle d'attaque, et la réponse "
        "serait de devenir le partenaire de validation et de services de ce module plutôt que "
        "de le concurrencer.",
    ]) + [
        Spacer(1, 6),
        heading("14.3 &nbsp; Conclusion", 1),
        para(f"BatchTwin traite un problème documenté plutôt que supposé : le dossier de lot "
             f"est la première source de non-conformités BPF [SOURCÉ], et l'outillage "
             f"abordable pour y remédier n'existe pas pour un fabricant de cent personnes. Le "
             f"produit est construit et mesurable &mdash; 1 205 champs issus des propres "
             f"documents d'un client, 143 tests au vert, 84 routes d'API [MESURÉ]. Le modèle "
             f"économique est dérivé d'ancrages publics plutôt qu'inventé, et atteint "
             f"{money(y3['revenue_tnd'])} de chiffre d'affaires et {money(y3['arr_exit_tnd'])} "
             f"de revenu récurrent en année 3 [CALCULÉ], sur une montée en charge clients que "
             f"nous avons qualifiée, à plusieurs reprises, de partie la moins étayée du plan."),
        para("Ce que nous n'affirmons pas importe autant que ce que nous affirmons. Nous ne "
             "nous sommes pas connectés à un Odoo de production. Nous n'avons pas mesuré la "
             "perte matière réelle. Nous n'avons pas éprouvé un prix auprès d'un client, "
             "approché un intégrateur, ni recensé notre propre marché adressable. Chacun de "
             "ces points figure au registre des risques avec l'action qui le referme, et aucun "
             "n'exige de financement &mdash; seulement de l'accès et un pilote."),
        Spacer(1, 4),
        callout("La phrase sur laquelle repose ce plan",
                "Odoo dit à un fabricant ce qui **aurait dû** se passer. BatchTwin capture ce "
                "qui **s'est réellement** passé &mdash; et l'écart entre les deux est là où se "
                "cachent le coût, la qualité, la conformité et le carbone. Combler cet écart "
                "vaut davantage pour un site BPF que n'importe quel gain d'efficacité, parce "
                "que c'est sur cet écart qu'un inspecteur pose ses questions.", "info"),
        PageBreak()]
    return s


# ================================================================== ANNEXES
def appendices():
    s = [heading("Annexe A &nbsp; Catalogue des indicateurs", 0),
         para("Tous les indicateurs cités dans ce document, consolidés. La colonne « preuve » "
              "est l'essentiel : un lecteur peut vérifier n'importe quelle ligne."),
         Spacer(1, 3)]

    rows = [
        ("Champs de dossier numérisés", "1 205", "MESURÉ", "ch. 1, 2, 4, 5"),
        ("Contrôles de conformité tactiles", "135", "MESURÉ", "ch. 2, 4"),
        ("Lignes papier vierges supprimées", "570", "MESURÉ", "ch. 2, 4"),
        ("Blocs répétables", "27", "MESURÉ", "ch. 4"),
        ("Modèles de dossier &rarr; formulaire adaptatif", "4 &rarr; 1", "MESURÉ", "ch. 4"),
        ("Routes d'API", "84", "MESURÉ", "ch. 4"),
        ("Lignes de code backend", "6 609", "MESURÉ", "ch. 4"),
        ("Tests automatisés au vert", "143 (8 ignorés)", "MESURÉ", "ch. 1, 4, 13"),
        ("Profils métier", "4", "MESURÉ", "ch. 4"),
        ("Modes de défaillance capteur modélisés", "8", "MESURÉ", "ch. 11"),
        ("Seuils péremption / mort", "120 s / 600 s", "MESURÉ", "ch. 11"),
        ("Écritures dans l'Odoo client", "0", "MESURÉ", "ch. 5, 10"),
        ("ML sur chemin critique de libération", "0", "MESURÉ", "ch. 5"),
        ("Coût matière du lot de démonstration", money(UE["bom_tnd"]), "MESURÉ", "ch. 2, 4"),
        ("Coût matière par unité", num(UE["cost_per_unit_tnd"], 4) + " TND", "MESURÉ", "ch. 4"),
        ("Inspections FDA citant le dossier de lot", "42 %", "SOURCÉ", "ch. 1, 2"),
        ("Lettres FDA médicaments, exercice 2025", "303 (+59 %)", "SOURCÉ", "ch. 2"),
        ("Lettres citant l'intégrité des données", "15 %", "SOURCÉ", "ch. 2"),
        ("Réduction du délai de libération (catégorie)", "40 à 60 %", "SOURCÉ", "ch. 11"),
        ("Réduction des erreurs, saisie directe", "jusqu'à 95 %", "SOURCÉ", "ch. 11"),
        ("Délai typique de retour sur investissement eBR", "12 à 18 mois", "SOURCÉ", "ch. 11"),
        ("Sites de fabrication pharma, Tunisie", "55", "SOURCÉ", "ch. 3"),
        ("Usines pharmaceutiques, Algérie", "218", "SOURCÉ", "ch. 3"),
        ("Marché pharma tunisien, 2025", "2,74 Md USD", "SOURCÉ", "ch. 3"),
        ("TCAC pharma tunisien jusqu'en 2032", "12,9 %", "SOURCÉ", "ch. 3"),
        ("Taux EUR/TND retenu", f"{FM.EUR_TND}", "SOURCÉ", "liminaires"),
        ("Fourchette salariale ingénieur Tunis", "3 500 à 7 000+ TND/mois", "SOURCÉ", "ch. 6, 7"),
        ("Taux journalier prestations", money(FM.DAY_RATE_TND), "CALCULÉ", "ch. 6"),
        ("Total prestations première année", money(FM.services_total()), "CALCULÉ", "ch. 6, 7"),
        ("Offre Essential", money(FM.PLANS["Essential"]["annual_tnd"]), "CALCULÉ", "ch. 6"),
        ("Offre Standard", money(FM.PLANS["Standard"]["annual_tnd"]), "CALCULÉ", "ch. 6"),
        ("Offre Enterprise", money(FM.PLANS["Enterprise"]["annual_tnd"]) + " + groupe",
         "CALCULÉ", "ch. 6"),
        ("Valeur du contrat de première année", money(MK["avg_first_year_contract_tnd"]),
         "CALCULÉ", "ch. 7"),
        ("CA année 1", money(M[1]["revenue_tnd"]), "CALCULÉ", "ch. 1, 8"),
        ("CA année 2", money(M[2]["revenue_tnd"]), "CALCULÉ", "ch. 8"),
        ("CA année 3", money(M[3]["revenue_tnd"]), "CALCULÉ", "ch. 1, 8"),
        ("Revenu récurrent de sortie, A3", money(M[3]["arr_exit_tnd"]), "CALCULÉ", "ch. 8, 13"),
        ("Marge nette année 3", pc(M[3]['margin_pct']), "CALCULÉ", "ch. 8"),
        ("Trésorerie cumulée sur 3 ans", money(M[3]["cumulative_cash_tnd"]), "CALCULÉ", "ch. 8"),
        ("Sites à l'équilibre, licences seules",
         f"{num(BE['sites_for_breakeven_on_licence_alone'], 1)}", "CALCULÉ", "ch. 1, 9, 13"),
        ("TAM Maghreb, plancher", f"{MK['tam_maghreb_pharma_floor_sites']} sites", "SOURCÉ", "ch. 3"),
        ("SAM Tunisie pharma", f"{MK['sam_tunisia_pharma_sites']} sites", "HYPOTHÈSE", "ch. 3"),
        ("Valeur annuelle du SAM", money(MK["sam_tunisia_value_tnd"]), "CALCULÉ", "ch. 3"),
        ("Perte matière réelle", "**inconnue**", "&mdash;", "ch. 2, 11 &mdash; le chiffre manquant"),
        ("Retour sur investissement BatchTwin", "**non énoncé**", "&mdash;",
         "ch. 11 &mdash; exige les données du client"),
        ("Nombre de sites compléments/cosmétique", "**inconnu**", "&mdash;",
         "ch. 3 &mdash; question ouverte n° 1"),
        ("Prix validés auprès de clients", "0", "&mdash;", "ch. 6, 12"),
        ("Intégrateurs approchés", "0", "&mdash;", "ch. 10, 12"),
    ]
    s += [table(["Indicateur", "Valeur", "Preuve", "Où dans ce document"],
                [[a, b, f"[{c}]" if c != "&mdash;" else c, d] for a, b, c, d in rows],
                [60 * mm, 34 * mm, 24 * mm, 52 * mm], align_right=(1,)),
          PageBreak()]

    # ---------------------------------------------------- Annexe B
    s += [heading("Annexe B &nbsp; Reproduire chaque affirmation mesurée", 0),
          para("Chaque commande ci-dessous s'exécute depuis la racine du dépôt et reproduit le "
               "chiffre correspondant. Cette annexe existe pour qu'aucun nombre mesuré de ce "
               "document n'ait à être cru sur parole."),
          Spacer(1, 3),
          table(["Affirmation", "Commande ou emplacement"],
                [["1 205 champs / 135 contrôles / 570 lignes / 27 blocs",
                  "`python -c \"from backend import docx_forms; "
                  "print(sum(f['field_count'] for f in docx_forms.load_all('dossier')))\"`"],
                 ["143 tests au vert, 8 ignorés", "`python -m pytest -q`"],
                 ["84 routes d'API", "`grep -cE '^@app\\.(get|post|put|delete)' backend/main.py`"],
                 ["6 609 lignes de code backend", "`find backend -name '*.py' | xargs wc -l`"],
                 ["Coût matière par lot et par unité",
                  "`backend/analytics.py::mass_balance()` sur le lot de démonstration"],
                 ["Intégration Odoo en lecture seule",
                  "`backend/odoo_adapter.py` ; `tests/test_odoo_contract.py`"],
                 ["Aucun ML sur chemin critique de libération",
                  "`tests/test_compliance.py::AssistantReadOnlyTests`"],
                 ["Limites de contrôle MSP validées",
                  "`tests/test_compliance.py::SPCValidationTests`"],
                 ["8 modes de défaillance, seuils 120 s / 600 s", "`backend/resilience.py`"],
                 ["Machine à états du mode d'exécution, AQ seule",
                  "`backend/store.py::set_run_mode()`"],
                 ["Base de cas et classement du conseiller",
                  "`backend/advisor.py` ; `tests/test_advisor.py`"],
                 ["Tout chiffre financier de ce document", "`python docs/finance_model.py`"]],
                [62 * mm, 108 * mm]),
          Spacer(1, 6)]

    # ---------------------------------------------------- Annexe C
    bom = [("Eau purifiée", "120,000", "kg", "0,05", "6,00"),
           ("Sirop de sorbitol 70 %", "40,000", "kg", "1,10", "44,00"),
           ("Citrate de magnésium", "4,800", "kg", "12,00", "57,60"),
           ("Chlorhydrate de pyridoxine (vit. B6)", "0,032", "kg", "180,00", "5,76"),
           ("Sorbate de potassium (conservateur)", "0,330", "kg", "6,50", "2,15"),
           ("Acide citrique (correcteur de pH)", "0,660", "kg", "1,80", "1,19"),
           ("Arôme orange", "1,600", "kg", "22,00", "35,20"),
           ("Flacon PET 200 mL + bouchon", "800", "unité", "0,14", "112,00"),
           ("Gobelet doseur", "800", "unité", "0,03", "24,00"),
           ("Étiquette + notice", "800", "unité", "0,05", "40,00"),
           ("Étui carton", "800", "unité", "0,09", "72,00")]
    s += [heading("Annexe C &nbsp; Nomenclature du lot de démonstration", 0),
          para(f"Formule réelle de Medicka &mdash; sirop oral citrate de magnésium et vitamine "
               f"B6, 200 mL, lot de {UE['units']} unités. Les coûts sont en EUR tels que "
               f"détenus dans les données source ; le total TND est converti à {FM.EUR_TND}."),
          Spacer(1, 3),
          table(["Matière", "Cible", "Unité", "Coût unitaire (EUR)", "Coût ligne (EUR)"],
                [[a, b, c, d, e] for a, b, c, d, e in bom]
                + [["**Total**", "", "", "", "**" + num(UE["bom_eur"], 2) + "**"],
                   ["**Total (TND)**", "", "", "",
                    "**" + num(UE["bom_tnd"], 2) + "**"],
                   ["**Par unité (TND)**", "", "", "", "**" + num(UE["cost_per_unit_tnd"], 4) + "**"]],
                [66 * mm, 22 * mm, 18 * mm, 32 * mm, 32 * mm], align_right=(1, 3, 4),
                bold_rows=(len(bom), len(bom) + 1, len(bom) + 2)),
          Spacer(1, 5),
          para("Il s'agit du coût théorique &mdash; ce qu'Odoo croit avoir été consommé. Ce qui "
               "a été *réellement* consommé est inconnu aujourd'hui sur tous les sites de ce "
               "segment, et produire ce chiffre pour la première fois constitue le cœur de la "
               "proposition de valeur (chapitres 2 et 11)."),
          PageBreak()]

    # ---------------------------------------------------- Annexe D
    assumptions = [
        ("Tarifs", "Prix des offres Essential / Standard / Enterprise", "ch. 6", "3 entretiens clients"),
        ("Tarifs", f"Coefficient de {FM.BILL_MULTIPLIER:.0f} sur le coût chargé", "ch. 6",
         "Étalonner sur le tarif journalier d'un intégrateur Odoo local"),
        ("Tarifs", "20 / 16 / 11 jours par prestation", "ch. 6", "Premier déploiement réel"),
        ("Tarifs", f"Remise client de référence de {FM.REFERENCE_DISCOUNT:.0%}", "ch. 10",
         "Négociation avec Medicka"),
        ("Coûts", f"Rémunération fondateurs {money(FM.FOUNDER_MONTHLY_TND[1])} &rarr; "
         f"{money(FM.FOUNDER_MONTHLY_TND[3])} par mois", "ch. 7", "Accord entre fondateurs"),
        ("Coûts", f"Effectif {FM.HEADCOUNT[1]} &rarr; {FM.HEADCOUNT[3]}", "ch. 7", "Charge de livraison"),
        ("Coûts", "Postes de charges d'exploitation, les trois années", "ch. 7", "Dépenses réelles"),
        ("Montée en charge", f"Nouveaux clients {FM.RAMP[1]['new']} / {FM.RAMP[2]['new']} / "
         f"{FM.RAMP[3]['new']}", "ch. 8", "**L'hypothèse la plus sensible du plan** (&sect; 9.2)"),
        ("Montée en charge", f"Attrition {FM.RAMP[1]['churn']} / {FM.RAMP[2]['churn']} / "
         f"{FM.RAMP[3]['churn']}", "ch. 8",
         "Aucun client n'est jamais parti ; aucune preuve dans un sens ou l'autre"),
        ("Montée en charge", "Répartition géographique Tunisie / Maghreb", "ch. 8",
         "Entrée au Maghreb non tentée"),
        ("Montée en charge", "Répartition des offres par année", "ch. 8", "Tailles de clients observées"),
        ("Marché", f"{FM.ADDRESSABLE_SHARE:.0%} des sites pharma tunisiens sont dans notre cible",
         "ch. 3", "Question ouverte n° 1"),
        ("Marché", "La population compléments / cosmétique est significative", "ch. 3",
         "**Non quantifiée. Question ouverte n° 1**"),
        ("Marché", "Maroc exclu du TAM", "ch. 3", "Conservateur par choix"),
        ("Produit", "Le déploiement reste proche de 20 jours chez d'autres clients", "ch. 13",
         "Deuxième déploiement"),
        ("Produit", "Une marche parallèle de 4 à 8 semaines suffit", "ch. 11", "Pilote Medicka"),
        ("Produit", "L'adaptateur Odoo réel fonctionne en production", "ch. 4, 12",
         "Risque R1 &mdash; une journée de travail"),
        ("Déploiement", "Les acheteurs BPF préfèrent l'hébergement sur site", "ch. 5, 6",
         "Question ouverte n° 7 &mdash; affirmé, jamais mesuré"),
        ("Commercial", "Le canal intégrateur acceptera un partage de marge", "ch. 10",
         "Question ouverte n° 5"),
        ("Commercial", "Les mises à jour réglementaires sont absorbables dans l'abonnement",
         "ch. 6", "Coût de la première évolution réglementaire"),
    ]
    s += [heading("Annexe D &nbsp; Registre des hypothèses", 0),
          para("Toutes les [HYPOTHÈSE] de ce document, réunies pour qu'un lecteur puisse les "
               "attaquer d'un bloc plutôt que de les traquer chapitre par chapitre. C'est la "
               "liste que nous remettrions à quelqu'un dont la mission serait de trouver le "
               "point le plus faible du plan."),
          Spacer(1, 3),
          table(["Domaine", "Hypothèse", "Où", "Ce qui la validerait"],
                [[a, b, c, d] for a, b, c, d in assumptions],
                [28 * mm, 60 * mm, 18 * mm, 64 * mm]),
          Spacer(1, 5),
          callout("Les trois qui comptent le plus",
                  "**La montée en charge clients** (le &sect; 9.2 montre qu'en la divisant par "
                  "deux le résultat devient une perte), **la taille du marché adressable** (le "
                  "&sect; 3.3 montre que nous ne pouvons pas énoncer notre propre part), et "
                  "**la disposition à payer** (aucun prix n'a été éprouvé auprès de "
                  "quiconque). Si seulement trois éléments pouvaient être validés avant "
                  "d'accorder du crédit à ce plan, ce sont ces trois-là &mdash; et aucun ne "
                  "coûte d'argent à trancher.", "warn"),
          PageBreak()]
    return s


def references():
    refs = [
        ("[1]", "Capterra &mdash; tarifs et avis MasterControl. "
         "https://www.capterra.com/p/148011/MasterControl/"),
        ("[2]", "OEC.sh &mdash; tarifs Odoo Enterprise par pays. https://oec.sh/odoo-pricing"),
        ("[3]", "Odoo &mdash; tarifs officiels. https://www.odoo.com/pricing"),
        ("[4]", "iFactory &mdash; eBR pharmaceutique et automatisation du dossier de lot : "
         "réduction de 40 à 60 % du délai de libération. "
         "https://ifactoryapp.com/blog/pharma-ebr-batch-record-automation"),
        ("[5]", "MasterControl GxP Lifeline &mdash; bénéfices du dossier de lot électronique "
         "pour la revue. https://www.mastercontrol.com/gxp-lifeline/"
         "benefits-electronic-batch-records-for-batch-record-review/"),
        ("[6]", "GMP Pros &mdash; difficultés du passage du papier au dossier de lot "
         "électronique ; insuffisances de dossier dans 42 % des inspections, 2020-2023. "
         "https://gmppros.com/challenges-transitioning-from-paper-to-electronic-batch-records/"),
        ("[7]", "Pharmaceutical Online &mdash; ce que les lettres d'avertissement FDA 2025 "
         "révèlent de la conformité BPF. https://www.pharmaceuticalonline.com/doc/"
         "what-fda-warning-letters-tell-us-about-gmp-compliance-0001"),
        ("[8]", "QBench &mdash; analyse de 470 lettres d'avertissement FDA de 2025. "
         "https://qbench.com/resources/inside-470-fda-warning-letters-from-2025-what-labs-need-to-know"),
        ("[9]", "Maghreb Pharma &mdash; avec 218 usines, l'Algérie conforte sa place de leader "
         "africain, 21 mai 2025. https://www.maghrebpharma.com/en/2025/05/21/"
         "pharmaceuticals-sector-with-218-plants-algeria-reinforces-its-position-as-african-leader/"),
        ("[10]", "African Manager &mdash; la Tunisie 9ᵉ marché pharmaceutique le plus "
         "compétitif d'Afrique en 2025. https://en.africanmanager.com/"
         "tunisia-ranked-9th-most-competitive-pharmaceutical-market-in-africa-in-2025/"),
        ("[11]", "Maximize Market Research &mdash; marché pharmaceutique tunisien, analyse et "
         "prévisions 2025-2032. "
         "https://www.maximizemarketresearch.com/market-report/tunisia-pharmaceutical-market/119566/"),
        ("[12]", "BatchLine &mdash; guide de mise en œuvre du dossier de lot électronique 2026. "
         "https://batchline.com/electronic-batch-record-ebr-implementation-guide/"),
        ("[13]", "A3P &mdash; eBR (Electronic Batch Record) : opportunités et écueils à éviter. "
         "https://www.a3p.org/en/electronic-batch-record/"),
        ("[14]", "Vimachem &mdash; comment le dossier de lot électronique dans un MES améliore "
         "la fabrication. https://www.vimachem.com/resources/articles/"
         "how-electronic-batch-records-in-mes-improve-manufacturing/"),
        ("[15]", "Glassdoor, levels.fyi et worldsalaries &mdash; salaire d'ingénieur logiciel, "
         "Tunisie / Tunis, 2025-2026. https://www.glassdoor.com/Salaries/"
         "tunisia-software-engineer-salary-SRCH_IL.0,7_IN236_KO8,25.htm"),
        ("[16]", "Pharmaceutical Technology &mdash; les dossiers de lot électroniques offrent "
         "des avantages au-delà de l'automatisation. https://www.pharmtech.com/view/"
         "electronic-batch-records-offer-advantages-beyond-automation"),
        ("[17]", "*Lecture complémentaire, non citée pour un chiffre précis.* EY &mdash; les "
         "dossiers de lot électroniques améliorent la fabrication pharmaceutique. "
         "https://www.ey.com/en_us/insights/life-sciences/"
         "electronic-batch-records-improve-pharma-manufacturing"),
        ("[18]", "*Lecture complémentaire, non citée pour un chiffre précis.* IntuitionLabs "
         "&mdash; panorama des logiciels MES et eBR pour la fabrication BPF. "
         "https://intuitionlabs.ai/articles/pharma-mes-ebr-software-gmp-manufacturing"),
        ("[19]", "Banque Centrale de Tunisie, taux moyen EUR/TND au 10 juillet 2026, via "
         "exchange-rates.org. https://www.exchange-rates.org/exchange-rate-history/eur-tnd-2026"),
        ("[20]", "US FDA &mdash; 21 CFR Part 11, enregistrements et signatures électroniques. "
         "https://www.fda.gov/regulatory-information/search-fda-guidance-documents/"
         "part-11-electronic-records-electronic-signatures-scope-and-application"),
    ]
    s = [heading("Références", 0),
         para("Tout chiffre [SOURCÉ] de ce document renvoie à une entrée ci-dessous. Consulté "
              "en juillet 2026."),
         Spacer(1, 4)]
    s += [table(["", "Référence"], [[a, b] for a, b in refs], [12 * mm, 158 * mm])]
    s += [Spacer(1, 8),
          callout("Note finale sur la méthode",
                  "Ce document comporte plusieurs endroits où la réponse honnête était « nous "
                  "ne savons pas » : la perte matière réelle, la taille de notre propre marché "
                  "adressable, ce qu'un client paiera, le fonctionnement de l'adaptateur Odoo "
                  "en production. Chacun est énoncé comme une lacune assortie de l'action qui "
                  "la referme, plutôt que comblé par un chiffre plausible. Ce choix rend le "
                  "plan moins complet en apparence et considérablement plus utile en pratique : "
                  "tout nombre qui y demeure peut être vérifié, et ceux qui ne le peuvent pas "
                  "sont étiquetés comme tels.", "info")]
    return s
