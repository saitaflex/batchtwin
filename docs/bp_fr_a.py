"""Édition française — liminaires, chapitres 1 à 3."""
from __future__ import annotations

from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, Spacer

import finance_model as FM
from build_business_plan import (M, UE, BE, SENS, MK, SVC, SS, bullets, callout,
                                 heading, kpibox, money, num, para, pc, rule,
                                 srcbox, table)


def front_matter_fr():
    s = [heading("Comment lire les chiffres de ce document", 0),
         para("Un plan d'affaires ne vaut que par la provenance des chiffres qu'il contient. "
              "La plupart confondent trois choses très différentes : ce qui a été mesuré, ce "
              "qu'un tiers a publié, et ce que les auteurs espèrent. Celui-ci les sépare par "
              "une étiquette apposée à chaque chiffre significatif."),
         Spacer(1, 4),
         table(["Étiquette", "Signification", "Exemple dans ce document"],
               [["[MESURÉ]", "Calculé par le code du dépôt BatchTwin, sur les fichiers réels "
                 "de Medicka. Reproductible par une commande listée en annexe B.",
                 "1 205 champs de dossier numérisés"],
                ["[SOURCÉ]", "Chiffre publié par un tiers, cité dans les références.",
                 "55 fabricants pharmaceutiques agréés en Tunisie"],
                ["[CALCULÉ]", "Arithmétique sur des données mesurées ou sourcées, posée "
                 "devant le lecteur pour qu'il puisse la vérifier ou la contester.",
                 "714 TND de taux journalier"],
                ["[HYPOTHÈSE]", "Notre estimation. Non validée. Toutes sont réunies en "
                 "annexe D afin d'être attaquées d'un bloc.",
                 "10 nouveaux clients en année 3"]],
               [26 * mm, 72 * mm, 72 * mm]),
         Spacer(1, 8),
         callout("La règle qui gouverne chaque chiffre",
                 "Aucun chiffre n'apparaît dans ce document s'il n'est pas mesuré, cité, ou "
                 "calculé devant le lecteur. Là où nous n'avons pas de chiffre &mdash; et il y "
                 "a plusieurs endroits, dont la taille de notre propre marché adressable "
                 "&mdash; le document le dit et précise ce qui permettrait de l'obtenir. Un "
                 "chiffre affirmé sans origine est le moyen le plus rapide de perdre un "
                 "lecteur qui vérifie l'arithmétique.", "info"),
         Spacer(1, 8),
         para(f"**Devise.** Tous les montants sont en dinar tunisien (TND). Le produit se vend "
              f"en Tunisie et la base de coûts est tunisienne ; libeller une offre en euro "
              f"pour un directeur qualité tunisien ouvre une discussion sur le taux de change "
              f"plutôt que sur le produit. Lorsqu'un montant en euro est la mesure d'origine, "
              f"il est converti à **1 EUR = {FM.EUR_TND} TND** [SOURCÉ] réf. [19] et les deux "
              f"sont affichés."),
         para("**Reproductibilité.** Chaque chiffre financier de ce document est produit par "
              "`docs/finance_model.py` puis importé par le générateur ; aucun n'est saisi deux "
              "fois. Le document ne peut donc pas diverger du modèle, ni le modèle du code "
              "qu'il mesure. La commande `python docs/finance_model.py` affiche l'ensemble du "
              "modèle, et l'annexe B associe à chaque affirmation mesurée la commande qui la "
              "reproduit."),
         rule(),
         heading("Sigles et abréviations", 1),
         Spacer(1, 3)]
    acr = [
        ("ALCOA+", "Attribuable, Lisible, Contemporain, Original, Exact &mdash; plus Complet, "
                   "Cohérent, Durable, Disponible. Le référentiel d'intégrité des données."),
        ("AQ", "Assurance qualité"),
        ("BPF / GMP", "Bonnes pratiques de fabrication"),
        ("CAPA", "Actions correctives et préventives"),
        ("CA", "Chiffre d'affaires"),
        ("DCOI / DCOII", "Dossier de conditionnement primaire / secondaire"),
        ("DCT", "Dossier de contrôle de la qualité"),
        ("DFA", "Dossier de fabrication"),
        ("DMR", "Dossier de lot électronique (eBR)"),
        ("ERP / PGI", "Progiciel de gestion intégré"),
        ("FEFO", "Premier périmé, premier sorti"),
        ("MCO", "Maintien en condition opérationnelle"),
        ("MES", "Système d'exécution de la fabrication"),
        ("MCO/QI/QO/QP", "Qualification d'installation, opérationnelle, de performance"),
        ("MRR / ARR", "Revenu récurrent mensuel / annuel"),
        ("MCO", "Maintien en conditions opérationnelles"),
        ("Part 11", "21 CFR Part 11 &mdash; enregistrements et signatures électroniques (FDA)"),
        ("MCR", "Moindres carrés ordinaires (régression linéaire)"),
        ("MSP / SPC", "Maîtrise statistique des procédés"),
        ("TAM / SAM / SOM", "Marché total adressable / accessible / atteignable"),
        ("TND", "Dinar tunisien"),
        ("CDC", "Cahier des charges utilisateur (URS)"),
    ]
    # dedupe while preserving order (the list above is hand-written and may repeat)
    seen, rows = set(), []
    for a, b in acr:
        if a in seen:
            continue
        seen.add(a)
        rows.append([a, b])
    s += [table(["Sigle", "Signification"], rows, [30 * mm, 140 * mm]), PageBreak()]
    return s


def ch1():
    y1, y2, y3 = M[1], M[2], M[3]
    s = [heading("1 &nbsp; Résumé exécutif", 0),
         para("**BatchTwin transforme le dossier de lot papier d'un fabricant BPF de taille "
              "moyenne en dossier numérique, par-dessus l'ERP Odoo qu'il exploite déjà "
              "&mdash; sans remplacer Odoo et sans arrêter la production pour migrer.**"),

         heading("1.1 &nbsp; Le problème", 1),
         para("Tout fabricant réglementé vit ou meurt par un document : le *dossier de lot*. "
              "Il prouve, lot par lot, ce qui a été fabriqué, à partir de quelles matières "
              "premières, contrôlé comment, et libéré par qui. Notre partenaire de conception "
              "&mdash; **Laboratoires Medicka**, certifié BPF depuis 2010, une centaine de "
              "salariés, 309 produits &mdash; tient encore ce dossier entièrement sur papier."),
         para("Le papier n'est pas seulement contraignant. C'est la première source de "
              "non-conformités réglementaires : les lettres d'avertissement de la FDA ont "
              "relevé des insuffisances de dossier de lot dans **42 % des inspections "
              "d'établissements pharmaceutiques** entre 2020 et 2023 [SOURCÉ], et sur "
              "l'exercice 2025 plus d'un tiers des lettres citaient des défauts documentaires "
              "&mdash; signatures manquantes, dossiers incomplets [SOURCÉ]. Le papier masque "
              "aussi de l'argent : l'ERP décrémente la quantité *théorique* de la recette, si "
              "bien que la matière réellement perdue à la pesée n'apparaît nulle part."),

         heading("1.2 &nbsp; Le produit", 1),
         para("BatchTwin lit les modèles `.docx` **du client lui-même** et les transforme en "
              "formulaires numériques saisissables. Sur les quatre dossiers réels de Medicka, "
              "cela a produit **1 205 champs saisissables, 135 contrôles de conformité "
              "tactiles, et supprimé 570 lignes papier vierges pré-imprimées** [MESURÉ]. "
              "Aucune retranscription, et aucune ré-implémentation des documents du client "
              "dans le modèle de données d'un éditeur &mdash; ce qui représente l'essentiel du "
              "coût d'un projet eBR classique."),
         para("Par-dessus viennent les fonctions que le papier ne peut pas rendre : une piste "
              "d'audit chaînée par empreintes avec fichier d'ancrage externe, des signatures "
              "électroniques Part 11, une barrière de libération infranchissable, le coût réel "
              "par lot calculé à partir de ce qui a été effectivement pesé, et une prévision "
              "de dérive MSP qui alerte **avant** que la spécification ne soit franchie."),

         heading("1.3 &nbsp; Le modèle économique", 1),
         para(f"Vendu **par site**, non par utilisateur. Les opérateurs travaillent en équipes "
              f"sur des tablettes partagées ; une tarification par utilisateur pousserait le "
              f"client vers des comptes partagés &mdash; ce qui détruirait le modèle "
              f"d'identité sur lequel repose toute la conformité. Trois offres, de "
              f"**{money(FM.PLANS['Essential']['annual_tnd'])}** à "
              f"**{money(FM.PLANS['Standard']['annual_tnd'])}** par site et par an, plus des "
              f"prestations de déploiement non récurrentes de "
              f"**{money(FM.services_total())}** [CALCULÉ]."),
         Spacer(1, 3),
         table(["", "Année 1", "Année 2", "Année 3"],
               [["Sites actifs", y1["active_sites"], y2["active_sites"], y3["active_sites"]],
                ["Revenu licences", money(y1["licence_tnd"]), money(y2["licence_tnd"]),
                 money(y3["licence_tnd"])],
                ["Revenu prestations", money(y1["services_tnd"]), money(y2["services_tnd"]),
                 money(y3["services_tnd"])],
                ["Chiffre d'affaires total", money(y1["revenue_tnd"]), money(y2["revenue_tnd"]),
                 money(y3["revenue_tnd"])],
                ["Charges totales", money(y1["cost_tnd"]), money(y2["cost_tnd"]),
                 money(y3["cost_tnd"])],
                ["Résultat", money(y1["profit_tnd"]), money(y2["profit_tnd"]),
                 money(y3["profit_tnd"])],
                ["Marge nette", pc(y1['margin_pct']), pc(y2['margin_pct']),
                 pc(y3['margin_pct'])]],
               [46 * mm, 41 * mm, 41 * mm, 42 * mm], align_right=(1, 2, 3), bold_rows=(3, 5)),
         Spacer(1, 6),
         callout("Lisez la ligne de résultat avec scepticisme &mdash; nous le faisons",
                 f"BatchTwin est bénéficiaire dès l'année 1, ce qui, pour un éditeur de "
                 f"logiciel, mérite la méfiance plutôt que les applaudissements. Deux causes, "
                 f"dont aucune n'est un exploit. D'abord, les trois fondateurs se rémunèrent "
                 f"{money(FM.FOUNDER_MONTHLY_TND[1])} par mois [HYPOTHÈSE], nettement sous le "
                 f"marché tunisois pour un ingénieur logiciel. Ensuite, "
                 f"{pc(y1['services_tnd'] / y1['revenue_tnd'] * 100, 0)} du chiffre d'affaires "
                 f"de l'année 1 vient de prestations non récurrentes, non de licences. Sur les "
                 f"seules licences, l'entreprise ne couvre sa base de coûts qu'à partir "
                 f"d'environ **{num(BE['sites_for_breakeven_on_licence_alone'], 1)} sites**, atteints "
                 f"au cours de l'année 3. Le chapitre 9 traite la question au fond.", "warn"),

         heading("1.4 &nbsp; Pourquoi ce segment est prenable", 1)]
    s += bullets([
        "**L'eBR d'entreprise est tarifé pour les multinationales.** MasterControl démarre à "
        "1 000 $ par mois et par fonction, avec un coût additionnel par site [SOURCÉ] ; "
        "Werum PAS-X suppose 18 à 24 mois de déploiement et un budget de conseil à six "
        "chiffres [SOURCÉ]. Un site tunisien de cent personnes ne peut justifier ni l'un ni "
        "l'autre : il reste donc sur papier. Cet écart *est* le marché.",
        "**Nous étendons Odoo au lieu de le remplacer.** Odoo est ce que les PME de ce "
        "segment exploitent réellement ; les concurrents leur demandent de l'abandonner.",
        "**Nous lisons les documents du client.** L'analyseur `.docx` est l'actif défendable, "
        "et analyser le dossier réel d'un prospect devant lui est la démonstration qui "
        "emporte la vente.",
        "**Déploiement sur site par défaut.** Les données de lot et les formules ne quittent "
        "jamais l'usine, ce qui supprime entièrement l'objection d'audit fournisseur "
        "(Annexe 11) &mdash; et supprime commercialement la facture cloud par client qui "
        "serait autrement notre premier coût variable.",
        "**L'intégration Odoo est en lecture seule par construction.** Nous ne pouvons pas "
        "corrompre l'ERP du client, puisque nous n'y écrivons jamais.",
    ])
    s += [Spacer(1, 5),
          heading("1.5 &nbsp; Ce qui n'est honnêtement pas démontré", 1),
          para("La donnée d'entrée la moins validée de ce plan est **la taille de notre propre "
               "marché adressable**, et elle l'est pour une raison précise et instructive : "
               "notre partenaire de conception est un fabricant de compléments alimentaires, "
               "et ces fabricants ne figurent dans aucun registre public tunisien. Le "
               "chapitre 3 énonce le problème au lieu de l'estimer de biais. Le chapitre 12 "
               "indique ce qui le résoudrait, et l'annexe D rassemble toutes les hypothèses du "
               "document dans un tableau unique afin qu'elles puissent être attaquées "
               "collectivement."),
          Spacer(1, 4),
          kpibox("Chapitre 1 &mdash; indicateurs clés", [
              ("Champs de dossier numérisés", "1 205", "MESURÉ", "docx_forms.load_all('dossier')"),
              ("Tests automatisés au vert", "143", "MESURÉ", "python -m pytest -q"),
              ("CA année 3", money(y3["revenue_tnd"]), "CALCULÉ", "finance_model.build_model()"),
              ("Seuil de rentabilité, licences seules",
               f"{num(BE['sites_for_breakeven_on_licence_alone'], 1)} sites", "CALCULÉ",
               "finance_model.breakeven()"),
              ("Inspections FDA citant le dossier de lot", "42 %", "SOURCÉ", "réf. [6], 2020-2023"),
          ]),
          Spacer(1, 4),
          srcbox(["[1] Capterra &mdash; tarifs MasterControl",
                  "[6] GMP Pros &mdash; passage du papier à l'eBR",
                  "[7] Pharmaceutical Online &mdash; lettres FDA 2025",
                  "[12] BatchLine &mdash; profil de déploiement PAS-X"]),
          PageBreak()]
    return s


def ch2():
    s = [heading("2 &nbsp; Le problème, chiffré", 0),
         para("Ce chapitre établit que le problème est réel, coûteux et réglementé &mdash; à "
              "partir de preuves publiées plutôt que de nos affirmations. C'est délibérément "
              "le chapitre le plus densément cité du document."),

         heading("2.1 &nbsp; Le dossier papier, première source de non-conformités BPF", 1),
         para("Le constat réglementaire est sans ambiguïté. Entre 2020 et 2023, les lettres "
              "d'avertissement de la FDA ont relevé des insuffisances de dossier de lot dans "
              "**42 % des inspections d'établissements pharmaceutiques** [SOURCÉ]. Sur "
              "l'exercice 2025, l'agence a émis **303 lettres pour les médicaments et "
              "produits biologiques, en hausse de 59 %**, et **plus d'un tiers citaient des "
              "défauts documentaires** &mdash; signatures manquantes, dossiers incomplets, "
              "procédures incohérentes [SOURCÉ]. L'intégrité des données apparaît "
              "spécifiquement dans **15 % de toutes les lettres de l'exercice 2025** [SOURCÉ]."),
         para("Deux observations comptent commercialement. La première : ce sont précisément "
              "les modes de défaillance contre lesquels un dossier papier est sans défense "
              "&mdash; une feuille ne peut pas refuser une libération non signée, ne peut pas "
              "s'horodater, et ne peut pas prouver qu'elle n'a pas été réécrite. La seconde : "
              "la pression de contrôle s'intensifie plutôt qu'elle ne s'allège, ce qui déplace "
              "l'achat du registre de l'efficacité vers celui du risque &mdash; et les achats "
              "de risque survivent aux coupes budgétaires que les achats d'efficacité ne "
              "survivent pas."),

         heading("2.2 &nbsp; Ce que le papier coûte sur un site comme Medicka", 1),
         para("Medicka exploite 309 produits, aux deux tiers des liquides oraux, à travers "
              "quatre étapes documentaires obligatoires : fabrication (DFA), conditionnement "
              "primaire (DCOI), conditionnement secondaire (DCOII) et contrôle qualité (DCT). "
              "Chaque lot génère un jeu papier complet. L'analyse de ces quatre modèles réels "
              "donne la forme exacte de la charge :"),
         Spacer(1, 3),
         table(["Dossier", "Étape", "Champs", "Contrôles", "Lignes vierges supprimées"],
               [["DFA", "Fabrication", "110", "3", "6"],
                ["DCOI", "Cond. primaire", "217", "13", "223"],
                ["DCOII", "Cond. secondaire", "218", "6", "120"],
                ["DCT", "Contrôle qualité", "660", "113", "221"],
                ["Total", "&mdash;", "1 205", "135", "570"]],
               [26 * mm, 34 * mm, 22 * mm, 30 * mm, 58 * mm],
               align_right=(2, 3, 4), bold_rows=(4,)),
         Spacer(1, 5),
         para("**Le chiffre de 570 est celui qu'il faut prononcer à voix haute** [MESURÉ]. Le "
              "DCOI pré-imprime un journal en cours de 92 lignes et le DCT un tableau de "
              "compression de 95 lignes &mdash; parce que le papier ne peut pas s'étendre. Ces "
              "lignes existent pour rester majoritairement vides. Un formulaire numérique "
              "s'étend à la demande : elles disparaissent purement et simplement. Ce n'est pas "
              "une allégation de productivité exigeant une étude, c'est de l'arithmétique sur "
              "les propres documents du client."),

         heading("2.3 &nbsp; L'argent invisible : la perte matière", 1),
         para("À la pesée, la matière première se perd en poussière, en projection et en "
              "résidu de cuve. L'ERP décrémente la quantité théorique de la nomenclature : la "
              "perte n'apparaît donc dans aucun système. Elle gonfle silencieusement le coût "
              "réel et corrompt le stock."),
         para(f"La formule réelle de Medicka pour le produit de démonstration &mdash; un sirop "
              f"oral magnésium et vitamine B6, 200 mL, lot de {UE['units']} unités &mdash; "
              f"coûte **{money(UE['bom_tnd'])}** en matières, soit "
              f"**{UE['cost_per_unit_tnd']:.3f} TND par unité** [MESURÉ]. C'est ce que croit "
              f"Odoo. Ce qui a été réellement consommé est un autre chiffre, et aujourd'hui "
              f"personne, nulle part, ne le connaît."),
         Spacer(1, 3),
         callout("La mesure la plus précieuse de tout ce plan",
                 "Nous nous abstenons délibérément d'annoncer un pourcentage de perte matière, "
                 "parce que nous ne l'avons pas &mdash; et le client non plus, Odoo étant "
                 "structurellement incapable de le produire. L'affirmation honnête n'est pas "
                 "« nous vous économisons X ». C'est : **Odoo ne voit pas ce chiffre du tout, "
                 "et après BatchTwin vous l'avez pour chaque lot.** Un mois de double saisie "
                 "en marche parallèle le crée pour la première fois. Il vaut plus, pour ce "
                 "dossier économique, que n'importe quelle projection de ce document, et le "
                 "chapitre 11 est construit autour de sa capture.", "good"),

         heading("2.4 &nbsp; Les données qualité en cours de production sont jetées", 1),
         para("Toutes les trente minutes, un opérateur mesure le volume de remplissage de dix "
              "flacons et note les résultats sur papier. Ces données pourraient révéler une "
              "tendance au sous-remplissage une heure avant le franchissement de "
              "spécification. Au lieu de quoi elles meurent dans un classeur. Si un "
              "prélèvement dérive à 15 h, personne ne voit la tendance avant que des flacons "
              "ne soient déjà sous-remplis et mis au rebut."),
         para("BatchTwin porte ces mêmes mesures sur une carte de contrôle X&#772;/R avec les "
              "règles Western Electric et ajuste une droite par moindres carrés pour prévoir "
              "le franchissement. C'est présenté comme de la statistique et non comme de l'IA, "
              "délibérément &mdash; voir le chapitre 5."),

         heading("2.5 &nbsp; Pourquoi ils n'ont pas déjà résolu le problème", 1),
         para("Non par ignorance. Par le prix et par le risque d'interruption :"),
         ] + bullets([
        "**L'eBR d'entreprise est hors de portée.** MasterControl démarre à 1 000 $ par mois "
        "et par fonction, puis facture de nouveau par site [SOURCÉ]. Werum PAS-X demande 18 à "
        "24 mois de déploiement et un budget de conseil à six chiffres [SOURCÉ].",
        "**Le risque de déploiement est existentiel.** Les travaux d'intégration causent plus "
        "de retards que toute autre partie d'un projet eBR [SOURCÉ]. Un site BPF ne peut pas "
        "cesser de produire pendant qu'un projet informatique trouve ses marques.",
        "**Le module Qualité d'Odoo n'est pas un dossier de lot.** Il enregistre des "
        "contrôles. Il ne produit pas de dossier de lot conforme et n'a pas de signature "
        "Part 11.",
        "**Développer en interne, c'est 18 mois et aucune expérience de validation.**",
    ]) + [
        Spacer(1, 5),
        kpibox("Chapitre 2 &mdash; indicateurs du problème", [
            ("Inspections FDA citant le dossier de lot", "42 %", "SOURCÉ", "réf. [6], 2020-2023"),
            ("Lettres FDA médicaments, exercice 2025", "303 (+59 %)", "SOURCÉ", "réf. [7]"),
            ("Lettres citant l'intégrité des données", "15 %", "SOURCÉ", "réf. [8]"),
            ("Champs de dossier sur papier aujourd'hui", "1 205", "MESURÉ", "analyseur docx_forms"),
            ("Lignes vierges pré-imprimées supprimées", "570", "MESURÉ", "blocs répétables"),
            ("Coût matière du lot de démonstration", money(UE["bom_tnd"]), "MESURÉ",
             "analytics.mass_balance()"),
            ("Perte matière réelle", "encore inconnue", "&mdash;", "exige une marche parallèle, ch. 11"),
        ]),
        Spacer(1, 4),
        srcbox(["[1] Capterra", "[6] GMP Pros", "[7] Pharmaceutical Online",
                "[8] QBench &mdash; 470 lettres FDA", "[12] BatchLine",
                "[13] A3P &mdash; écueils de l'eBR"]),
        PageBreak()]
    return s


def ch3():
    s = [heading("3 &nbsp; Analyse de marché", 0),
         para("C'est le chapitre le plus faible du document, et il est écrit pour être lu comme "
              "tel. Nous savons sourcer un dénominateur ; nous ne savons pas sourcer le *bon* "
              "dénominateur."),

         heading("3.1 &nbsp; Marché total adressable &mdash; un plancher, pas une estimation", 1),
         para("Sites de fabrication pharmaceutique agréés au Maghreb, en ne comptant que les "
              "pays qui publient un chiffre :"),
         Spacer(1, 3),
         table(["Pays", "Sites de fabrication agréés", "Preuve"],
               [["Algérie", "218", "[SOURCÉ] réf. [9] &mdash; 30 % de l'industrie pharmaceutique africaine"],
                ["Tunisie", "55", "[SOURCÉ] réf. [10] &mdash; plus de 40 laboratoires, export vers ~35 pays"],
                ["Maroc", "non publié", "2ᵉ d'Afrique en volume ; aucun décompte de sites trouvé"],
                ["Total plancher", f"{MK['tam_maghreb_pharma_floor_sites']}",
                 "Exclut entièrement le Maroc"]],
               [30 * mm, 46 * mm, 94 * mm], bold_rows=(3,)),
         Spacer(1, 5),
         para("Nous présentons ce total comme un **plancher** et non comme une estimation, "
              "parce que le Maroc manque réellement, et que gonfler le total d'un chiffre "
              "marocain deviné rendrait le nombre moins utile, non plus utile."),

         heading("3.2 &nbsp; Marché accessible &mdash; Tunisie", 1),
         para(f"Sur les {FM.PHARMA_SITES['Tunisia']} sites pharmaceutiques tunisiens, notre "
              f"cible est de 50 à 300 salariés, déjà équipés d'un ERP, encore sur dossier de "
              f"lot papier. Nous supposons que **{FM.ADDRESSABLE_SHARE:.0%}** qualifient "
              f"[HYPOTHÈSE], soit **{MK['sam_tunisia_pharma_sites']} sites**, représentant "
              f"**{money(MK['sam_tunisia_value_tnd'])} par an** au tarif Standard."),
         para("Les sites déjà dotés d'un MES validé sont écartés &mdash; le coût de "
              "remplacement dépasse la douleur. Les sites sans aucun ERP également, BatchTwin "
              "supposant l'existence d'une nomenclature."),

         heading("3.3 &nbsp; Le problème du dénominateur, énoncé sans détour", 1),
         callout("Notre propre part de marché ne résiste pas à l'examen, et voici pourquoi",
                 f"{MK['som_y3_tunisia_sites']} sites tunisiens représentent "
                 f"{pc(MK['som_y3_share_of_tunisia_pharma_sam_pct'])} d'un marché accessible "
                 f"restreint au pharmaceutique, soit {MK['sam_tunisia_pharma_sites']} sites. "
                 f"Cette part est invraisemblable en soi, et nous n'allons pas la défendre. La "
                 f"résolution est que le dénominateur est faux, non le numérateur : le segment "
                 f"de BatchTwin comprend les nutraceutiques, les compléments alimentaires, les "
                 f"cosmétiques et les dispositifs médicaux autant que le pharmaceutique "
                 f"&mdash; Medicka est elle-même un fabricant de compléments et **ne figure "
                 f"pas** dans les 55. Aucun registre public ne recense cette population en "
                 f"Tunisie. Tant qu'elle n'est pas recensée, la part de marché du plan reste "
                 f"non énoncée plutôt qu'estimée. Ce recensement est la question ouverte n° 1 ; "
                 f"le chapitre 12 en donne la méthode et le coût.", "bad"),
         Spacer(1, 5),
         para("Nous aurions pu masquer cela en gonflant discrètement la part adressable "
              "jusqu'à ce que le pourcentage paraisse modeste. Au lieu de quoi : le numérateur "
              "est défendable, le dénominateur est faux, et le correctif relève du "
              "dénombrement, non de la modélisation. **Recenser la population tunisienne de "
              "fabricants de nutraceutiques, compléments, cosmétiques et dispositifs est la "
              "question ouverte n° 1.**"),
         para("Ce que l'on peut affirmer avec confiance est directionnel : Medicka est un tel "
              "site, elle n'est pas dans les 55, et les sources qui permettraient de recenser "
              "ses pairs &mdash; enregistrements ANCSEP, listes de certificats ISO 22716, "
              "annuaires de fédérations professionnelles &mdash; existent. Elles n'ont "
              "simplement jamais été agrégées par personne, nous compris."),

         heading("3.4 &nbsp; Vent porteur du marché", 1),
         para("Le marché pharmaceutique tunisien était évalué à **2,74 milliards USD en 2025**, "
              "avec une croissance annuelle projetée de **12,9 % jusqu'en 2032** [SOURCÉ]. La "
              "production domestique s'établit à environ **52 %**, et la politique publique "
              "vise **70 % à l'horizon 2030** [SOURCÉ]. La Tunisie était classée **9ᵉ marché "
              "pharmaceutique le plus compétitif d'Afrique en 2025** [SOURCÉ]."),
         para("L'implication pertinente est étroite et mérite d'être formulée avec précision : "
              "une politique de relocalisation signifie davantage de lots fabriqués "
              "localement, davantage de dossiers, et davantage d'exposition à l'inspection "
              "&mdash; et l'ambition export relève le niveau documentaire, puisqu'un "
              "régulateur importateur audite le dossier de lot. La croissance du marché n'est "
              "pas automatiquement notre croissance ; celle de la *production domestique "
              "réglementée* l'est."),

         heading("3.5 &nbsp; Priorisation des segments", 1),
         table(["Segment", "Pourquoi maintenant", "Priorité"],
               [["Compléments alimentaires et nutraceutiques",
                 "Medicka est la référence. Pression ISO 22716 / HACCP sans la tolérance de "
                 "coût du pharmaceutique &mdash; l'écart d'accessibilité tarifaire est le plus "
                 "large ici.", "**Premier**"],
                ["Pharmaceutique (PME, petites molécules)",
                 "Pression réglementaire maximale et disposition à payer la plus nette ; cycle "
                 "de vente le plus long et charge de validation la plus lourde.", "Deuxième"],
                ["Cosmétique",
                 "ISO 22716 s'applique ; les dossiers sont plus légers, donc la valeur du "
                 "contrat est moindre.", "Troisième"],
                ["Dispositifs médicaux",
                 "ISO 13485 pris en charge par un profil métier dans le code, mais aucun "
                 "partenaire de conception.", "Opportuniste"]],
               [50 * mm, 92 * mm, 28 * mm]),
         Spacer(1, 5),
         kpibox("Chapitre 3 &mdash; indicateurs de marché", [
             ("TAM Maghreb, sites pharma (plancher)", f"{MK['tam_maghreb_pharma_floor_sites']}",
              "SOURCÉ", "Tunisie 55 + Algérie 218 ; Maroc exclu"),
             ("SAM Tunisie, sites pharma", f"{MK['sam_tunisia_pharma_sites']}", "HYPOTHÈSE",
              f"{FM.ADDRESSABLE_SHARE:.0%} des 55 qualifient"),
             ("Valeur annuelle du SAM", money(MK["sam_tunisia_value_tnd"]), "CALCULÉ",
              "sites SAM &times; offre Standard"),
             ("Sites année 3, total", f"{MK['som_y3_total_sites']}", "HYPOTHÈSE", "montée en charge, ch. 8"),
             ("Sites année 3, Tunisie", f"{MK['som_y3_tunisia_sites']}", "HYPOTHÈSE", "répartition géographique"),
             ("Part implicite du SAM pharma seul",
              pc(MK['som_y3_share_of_tunisia_pharma_sam_pct']), "CALCULÉ",
              "&#9888; invraisemblable &mdash; voir &sect; 3.3"),
             ("Marché pharma tunisien, 2025", "2,74 Md USD", "SOURCÉ", "réf. [11], TCAC 12,9 %"),
             ("Nombre de sites compléments/cosmétique", "inconnu", "&mdash;", "question ouverte n° 1"),
         ]),
         Spacer(1, 4),
         srcbox(["[9] Maghreb Pharma &mdash; 218 usines en Algérie",
                 "[10] African Manager &mdash; compétitivité tunisienne",
                 "[11] Maximize Market Research &mdash; marché pharma tunisien"]),
         PageBreak()]
    return s
