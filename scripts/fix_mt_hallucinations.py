#!/usr/bin/env python3
"""Fix confirmed MarianMT/Qwen hallucinations in HEA_ICD10 description_en
that survived the earlier WHO-ICD-10 mapping (because the Danish code
had a Danish-specific subdivision beyond what WHO publishes).

Each entry below was found by:
  1. Keyword-based Danish→English presence check (e.g., DA has "kræft"
     but EN has no cancer-related term)
  2. Manual inspection for confirmation

Pre-existing wrong translations come from the MarianMT step in the
original data pipeline. WHO ICD-10 exact codes were correct; these
are 4-5-6-character Danish ICD-10 extensions without an exact WHO
equivalent at the leaf, so the MT translation was preserved.

Usage:
    python3 scripts/fix_mt_hallucinations.py [--dry-run]
"""
import argparse
import csv

MASTER_PATH = "MASTER_CATEGORY_MAPPINGS.csv"

# Confirmed wrong translations → correct English
FIXES = {
    # Musculoskeletal / injuries
    "HEA_ICD10_DG4761": ("Rastløse ben", "Restless legs"),
    "HEA_ICD10_DG4764": ("Tænderskæren", "Bruxism (teeth grinding)"),
    "HEA_ICD10_DS500":  ("Kontusion af albue", "Contusion of elbow"),
    "HEA_ICD10_DS510":  ("Åbent sår på albue", "Open wound of elbow"),
    "HEA_ICD10_DS520A": ("Fraktur af albue UNS", "Fracture of elbow, NOS"),
    "HEA_ICD10_DM703":  ("Anden bursitis i albue", "Other bursitis of elbow"),
    "HEA_ICD10_DM754":  ("Afklemningssyndrom i skulder", "Shoulder impingement syndrome"),
    # Urinary / renal
    "HEA_ICD10_DN200":  ("Nyresten UNS", "Kidney stone, NOS"),
    "HEA_ICD10_DN209A": ("Nyrebækkenbetændelse med nyresten",
                          "Pyelonephritis with kidney stone"),
    # Gastrointestinal / defecation
    "HEA_ICD10_DR194":  ("Ændret afføringsmønster", "Altered bowel habit"),
    "HEA_ICD10_DR195":  ("Abnorm afføring UNS", "Abnormal stool, NOS"),
    "HEA_ICD10_DR159":  ("Afføringsinkontinens", "Faecal incontinence"),
    # Neoplasms
    "HEA_ICD10_DC569":  ("Æggestokkræft", "Ovarian cancer"),
    "HEA_ICD10_DC329":  ("Kræft i strubehovedet UNS", "Cancer of larynx, NOS"),
    "HEA_ICD10_DC700":  ("Kræft i hjernehinde", "Cancer of the meninges"),
    "HEA_ICD10_DC713":  ("Kræft i hjernens isselap", "Cancer of parietal lobe of the brain"),
    "HEA_ICD10_DC714":  ("Kræft i hjernens nakkelap", "Cancer of occipital lobe of the brain"),
    # Toxicology
    "HEA_ICD10_DT599B": ("Røgforgiftning UNS", "Smoke poisoning, NOS"),
    # Infectious / zoonotic
    "HEA_ICD10_DA821":  ("Flagermusrabies (European Bat Lyssavirus - EBL)",
                          "Bat rabies (European Bat Lyssavirus)"),
    # Batch 2 — intestines / bladder / ulcers
    "HEA_ICD10_DC189":  ("Kræft i tyktarmen UNS", "Cancer of colon, NOS"),
    "HEA_ICD10_DN300":  ("Akut blærebetændelse", "Acute cystitis"),
    "HEA_ICD10_DK251":  ("Akut mavesår med perforation",
                          "Acute gastric ulcer with perforation"),
    "HEA_ICD10_DK566F": ("Tyndtarmsstenose", "Small intestine stenosis"),
    "HEA_ICD10_DK566G": ("Tyktarmsstenose", "Colon stenosis"),
    "HEA_ICD10_DK550F": ("Akut tyndtarmsiskæmi", "Acute small-intestine ischaemia"),
    "HEA_ICD10_DK572A": ("Divertikulitis i tyktarmen med absces",
                          "Diverticulitis of colon with abscess"),
    "HEA_ICD10_DK562B": ("Tyktarmsvolvulus", "Colon volvulus"),
    "HEA_ICD10_DS035":  ("Forvridning af andet eller ikke specificeret led eller ledbånd på "
                         "hovedet",
                          "Sprain of other or unspecified joint or ligament of head"),
    "HEA_ICD10_DS03":   ("Ledskred og forvridning af ledbånd på hovedet",
                          "Dislocation and sprain of joints and ligaments of head"),
    "HEA_ICD10_DS034B": ("Distorsion af ledbånd i kæbeled",
                          "Sprain of ligaments of temporomandibular joint"),
    # Batch 3 — untranslated single Danish words
    "HEA_ICD10_DR119C": ("Opkastning", "Vomiting"),
    "HEA_ICD10_DR119B": ("Kvalme", "Nausea"),
    "HEA_ICD10_DR539F": ("Utilpashed", "Malaise"),
    "HEA_ICD10_DR539A": ("Udmattelse", "Fatigue / exhaustion"),
    "HEA_ICD10_DN502C": ("Anejakulation", "Anejaculation"),
    "HEA_ICD10_DD249A": ("Fibroadenom i mamma", "Fibroadenoma of breast"),
    "HEA_ICD10_DZ306":  ("Svangerskabsforebyggelse (P-stav)",
                          "Contraception (contraceptive implant)"),
    "HEA_ICD10_DG903":  ("Multipel systemdegeneration i autonome nervesystem",
                          "Multiple system degeneration of the autonomic nervous system"),
    "HEA_ICD10_DC560":  ("Neopl mal ovarii, st. I", "Malignant neoplasm of ovary, stage I"),
    "HEA_ICD10_DD249G": ("Fibromatose i mamma", "Fibromatosis of breast"),
    "HEA_ICD10_DG564":  ("Kausalgi i arm", "Causalgia of arm"),
    "HEA_ICD10_DD249D": ("Adenom i brystvorte", "Adenoma of nipple"),
    "HEA_ICD10_DD249F": ("Harmartom i mamma", "Hamartoma of breast"),
    # Batch 4 — mistranslated neoplasms from the broader audit
    "HEA_ICD10_DD123":  ("Godartet tumor i colon transversum",
                          "Benign neoplasm of transverse colon"),
    "HEA_ICD10_DD292":  ("Godartet tumor i testikel", "Benign neoplasm of testis"),
    "HEA_ICD10_DM775":  ("Anden entesopati på fod", "Other enthesopathy of foot"),
    # Batch 5 — brain regions (frontal/parietal/temporal/occipital lobes, meninges)
    "HEA_ICD10_DC711":  ("Kræft i hjernens pandelap", "Cancer of the frontal lobe"),
    "HEA_ICD10_DC712":  ("Kræft i hjernens tindingelap", "Cancer of the temporal lobe"),
    "HEA_ICD10_DC717C": ("Infratentoriel kræft i hjernen UNS",
                          "Infratentorial brain cancer, NOS"),
    "HEA_ICD10_DD330A": ("Godartet tumor i hjernens pandelap",
                          "Benign neoplasm of the frontal lobe"),
    "HEA_ICD10_DD330B": ("Godartet tumor i hjernens nakkelap",
                          "Benign neoplasm of the occipital lobe"),
    "HEA_ICD10_DD330C": ("Godartet tumor i hjernens isselap",
                          "Benign neoplasm of the parietal lobe"),
    "HEA_ICD10_DD330D": ("Godartet tumor i hjernens tindingelap",
                          "Benign neoplasm of the temporal lobe"),
    "HEA_ICD10_DD430C": ("Ikke specificeret tumor i hjernens nakkelap",
                          "Unspecified tumor of the occipital lobe"),
    "HEA_ICD10_DD430D": ("Ikke specificeret tumor i hjernens isselap",
                          "Unspecified tumor of the parietal lobe"),
    "HEA_ICD10_DD430E": ("Ikke specificeret tumor i hjernens tindingelap",
                          "Unspecified tumor of the temporal lobe"),
    "HEA_ICD10_DD431":  ("Infratentoriel ikke specificeret tumor i hjernen",
                          "Unspecified infratentorial brain tumor"),
    "HEA_ICD10_DG03":   ("Hjernehindebetændelse af andre og ikke specificerede årsager",
                          "Meningitis of other and unspecified causes"),
    "HEA_ICD10_DD32":   ("Godartede tumorer i hjernehinder og rygmarvshinder",
                          "Benign neoplasms of meninges of brain and spinal cord"),
    "HEA_ICD10_DE23":   ("Nedsat aktivitet og andre sygdomme i hypofysen",
                          "Hypofunction and other disorders of the pituitary gland"),
    # Batch 6 — more mistranslated terms
    "HEA_ICD10_DZ033D": ("Observation pga. mistanke om hjernerystelse",
                          "Observation due to suspicion of concussion"),
    "HEA_ICD10_DP38":   ("Betændelse i navle hos nyfødt",
                          "Omphalitis in the neonate"),
    "HEA_ICD10_DZ380Q": ("Levendefødt barn født på sygehus overf. u planlagt hj.fødsel",
                          "Liveborn infant delivered in hospital after unplanned home birth"),
    # Batch 7 — tå/underarm/rygmarv/organs systematic errors
    "HEA_ICD10_DS901":  ("Kontusion af tå uden beskadigelse af negl",
                          "Contusion of toe without nail injury"),
    "HEA_ICD10_DS901A": ("Kontusion af tå UNS", "Contusion of toe, NOS"),
    "HEA_ICD10_DS902":  ("Kontusion af tå med beskadigelse af negl",
                          "Contusion of toe with nail injury"),
    "HEA_ICD10_DS925":  ("Fraktur af anden specificeret tå",
                          "Fracture of other specified toe"),
    "HEA_ICD10_DS925A": ("Fraktur af 2. tå", "Fracture of the second toe"),
    "HEA_ICD10_DM205":  ("Anden erhvervet deformitet af tå",
                          "Other acquired deformity of toe"),
    "HEA_ICD10_DS501":  ("Kontusion af anden eller ikke specificeret del af underarm",
                          "Contusion of other or unspecified part of forearm"),
    "HEA_ICD10_DS507":  ("Multiple overfladiske læsioner af albueregion eller underarm",
                          "Multiple superficial lesions of the elbow region or forearm"),
    "HEA_ICD10_DS508":  ("Anden overfladisk læsion af albueregion eller underarm",
                          "Other superficial lesion of the elbow region or forearm"),
    "HEA_ICD10_DS509":  ("Overfladisk læsion af albueregion eller underarm UNS",
                          "Superficial lesion of elbow region or forearm, NOS"),
    "HEA_ICD10_DS517":  ("Multiple åbne sår på albueregion eller underarm",
                          "Multiple open wounds of the elbow region or forearm"),
    "HEA_ICD10_DS518":  ("Åbent sår på anden del af albueregion eller underarm",
                          "Open wound of other part of the elbow region or forearm"),
    "HEA_ICD10_DS519":  ("Åbent sår på albueregion eller underarm UNS",
                          "Open wound of elbow region or forearm, NOS"),
    "HEA_ICD10_DS529":  ("Fraktur i underarm UNS", "Fracture of forearm, NOS"),
    "HEA_ICD10_DS540":  ("Læsion af nervus ulnaris i albueregion eller underarm",
                          "Injury of ulnar nerve at elbow region or forearm"),
    "HEA_ICD10_DS565":  ("Læsion af muskel eller sene af anden ekstensor på underarm",
                          "Injury of muscle or tendon of other extensor of forearm"),
    "HEA_ICD10_DS568":  ("Læsion af anden eller ikke specificeret muskel eller sene i "
                         "albueregion eller underarm",
                          "Injury of other or unspecified muscle or tendon at elbow region or forearm"),
    "HEA_ICD10_DS597":  ("Multiple læsioner af albueregion eller underarm",
                          "Multiple injuries of the elbow region or forearm"),
    "HEA_ICD10_DS598":  ("Anden læsion af albueregion eller underarm",
                          "Other injury of elbow region or forearm"),
    "HEA_ICD10_DM921":  ("Juvenil osteokondrose i underarm",
                          "Juvenile osteochondrosis of forearm (radius and ulna)"),
    "HEA_ICD10_DS141":  ("Anden eller ikke specificeret læsion af den cervikale rygmarv",
                          "Other or unspecified injury of cervical spinal cord"),
    "HEA_ICD10_DS241":  ("Anden eller ikke specificeret læsion af den torakale rygmarv",
                          "Other or unspecified injury of thoracic spinal cord"),
    "HEA_ICD10_DS241C": ("Kontusion af den torakale rygmarv",
                          "Contusion of thoracic spinal cord"),
    "HEA_ICD10_DS341":  ("Anden eller ikke specificeret læsion af den lumbale rygmarv",
                          "Other or unspecified injury of lumbar spinal cord"),
    "HEA_ICD10_DS341C": ("Kontusion af den lumbale rygmarv",
                          "Contusion of lumbar spinal cord"),
    "HEA_ICD10_DQ068":  ("Anden medfødt misdannelse i rygmarv",
                          "Other congenital malformation of spinal cord"),
    # Batch 8 — organ-mistranslations
    "HEA_ICD10_DC739":  ("Kræft i skjoldbruskkirtlen", "Cancer of the thyroid gland"),
    "HEA_ICD10_DZ031XD": ("Observation pga. mistanke om kræft i skjoldbruskkirtlen",
                          "Observation for suspicion of thyroid cancer"),
    "HEA_ICD10_DD350":  ("Godartet tumor i binyre", "Benign neoplasm of the adrenal gland"),
    "HEA_ICD10_DC749":  ("Kræft i binyre UNS", "Cancer of the adrenal gland, NOS"),
    "HEA_ICD10_DZ080L": ("Kontrolundersøgelse efter operation af kræft i livmoder",
                          "Follow-up examination after surgery for uterine cancer"),
    "HEA_ICD10_DZ080C": ("Kontrolundersøgelse efter operation af kræft i mavesæk",
                          "Follow-up examination after surgery for gastric cancer"),
    "HEA_ICD10_DC500B": ("Kræft i brystvorte", "Cancer of the nipple"),
    "HEA_ICD10_DK149":  ("Sygdom i tunge UNS", "Disease of the tongue, NOS"),
    "HEA_ICD10_DZ804":  ("Familieanamnese med kræft i kønsorganer",
                          "Family history of cancer of genital organs"),
    "HEA_ICD10_DK253":  ("Akut mavesår uden blødning eller perforation",
                          "Acute gastric ulcer without haemorrhage or perforation"),
    "HEA_ICD10_DM244C": ("Habituel luksation af albueled",
                          "Habitual dislocation of elbow joint"),
    "HEA_ICD10_DD381":  ("Ikke specificeret tumor i luftrør, bronkie eller lunge",
                          "Unspecified tumor of trachea, bronchus or lung"),
    "HEA_ICD10_DZ851":  ("Anamnese med kræft i luftrør, bronkier eller lunger",
                          "History of cancer of trachea, bronchi or lungs"),
    # Batch 9 — spiserør (oesophagus) — MT wrongly mapped to pharynx/ear structures
    "HEA_ICD10_DC159":  ("Kræft i spiserøret UNS", "Cancer of the oesophagus, NOS"),
    "HEA_ICD10_DC155":  ("Kræft i spiserørets nederste tredjedel",
                          "Cancer of the lower third of the oesophagus"),
    "HEA_ICD10_DC158":  ("Kræft i spiserøret overgribende flere lokalisationer",
                          "Cancer of oesophagus, overlapping lesion"),
    "HEA_ICD10_DC159M": ("Kræft i spiserøret med metastaser",
                          "Cancer of the oesophagus with metastases"),
    "HEA_ICD10_DC159X": ("Lokalrecidiv fra kræft i spiserøret",
                          "Local recurrence from cancer of the oesophagus"),
    "HEA_ICD10_DD130":  ("Godartet tumor i spiserøret",
                          "Benign neoplasm of the oesophagus"),
    "HEA_ICD10_DD377B": ("Ikke specificeret tumor i spiserøret",
                          "Unspecified tumor of the oesophagus"),
    "HEA_ICD10_DK224":  ("Spiserørsdyskinesi", "Oesophageal dyskinesia"),
    "HEA_ICD10_DK228":  ("Anden sygdom i spiserøret",
                          "Other disease of the oesophagus"),
    "HEA_ICD10_DK228F": ("Blødning i spiserøret UNS",
                          "Bleeding of the oesophagus, NOS"),
    "HEA_ICD10_DZ031C": ("Observation pga. mistanke om kræft i spiserøret eller mavesækken",
                          "Observation for suspicion of cancer of the oesophagus or stomach"),
    "HEA_ICD10_DZ031CR": ("Observation pga. mistanke om recidiv af kræft i spiserøret eller "
                          "mavesækken",
                          "Observation for suspicion of recurrence of cancer of the oesophagus or stomach"),
    # Batch 10 — spytkirtel (salivary gland) — MT went wild with unrelated structures
    "HEA_ICD10_DK110":  ("Atrofi af spytkirtel", "Atrophy of salivary gland"),
    "HEA_ICD10_DK111":  ("Hypertrofi af spytkirtel", "Hypertrophy of salivary gland"),
    "HEA_ICD10_DK112":  ("Betændelse i spytkirtel", "Sialoadenitis (salivary gland inflammation)"),
    "HEA_ICD10_DK113":  ("Absces i spytkirtel", "Abscess of salivary gland"),
    "HEA_ICD10_DK116":  ("Mukocele i spytkirtel", "Mucocele of salivary gland"),
    "HEA_ICD10_DK117":  ("Sekretionsforstyrrelse i spytkirtel",
                          "Disturbance of salivary secretion"),
    "HEA_ICD10_DK118":  ("Anden sygdom i spytkirtel", "Other disease of salivary gland"),
    "HEA_ICD10_DK119":  ("Sygdom i spytkirtel UNS", "Disease of salivary gland, NOS"),
    "HEA_ICD10_DD117":  ("Godartet tumor i anden stor spytkirtel",
                          "Benign neoplasm of other major salivary gland"),
    "HEA_ICD10_DZ031XC": ("Observation pga. mistanke om kræft i spytkirtel",
                          "Observation for suspicion of salivary gland cancer"),
    "HEA_ICD10_DK85":   ("Akut betændelse i bugspytkirtel",
                          "Acute pancreatitis (inflammation of the pancreas)"),
    # Batch 11 — other isolated bugs
    "HEA_ICD10_DR198C": ("Meteorismus", "Flatulence / bloating"),
    "HEA_ICD10_DS920":  ("Fraktur af hælben", "Fracture of calcaneus (heel bone)"),
    # Batch 12 — untranslated Danish rows
    "HEA_ICD10_DF100":  ("Akut alkoholintoksikation", "Acute alcohol intoxication"),
    "HEA_ICD10_DN109C": ("Akut pyelonefritis", "Acute pyelonephritis"),
    # Batch 13 — håndled (wrist) consistently mistranslated as forearm/arm/finger
    "HEA_ICD10_DS602":  ("Kontusion af håndled eller hånd",
                          "Contusion of wrist or hand"),
    "HEA_ICD10_DS602A": ("Kontusion af håndled", "Contusion of wrist"),
    "HEA_ICD10_DS607":  ("Multiple overfladiske læsioner af håndled eller hånd",
                          "Multiple superficial injuries of wrist or hand"),
    "HEA_ICD10_DS609":  ("Overfladisk læsion af håndled eller hånd UNS",
                          "Superficial injury of wrist or hand, NOS"),
    "HEA_ICD10_DS618":  ("Åbent sår på anden del af håndled eller hånd",
                          "Open wound of other part of wrist or hand"),
    "HEA_ICD10_DS619":  ("Åbent sår på håndled eller hånd UNS",
                          "Open wound of wrist or hand, NOS"),
    "HEA_ICD10_DS628A": ("Fraktur af håndled UNS", "Fracture of wrist, NOS"),
    "HEA_ICD10_DS633":  ("Traumatisk ruptur af ligament i håndled eller hånd",
                          "Traumatic rupture of ligament of wrist or hand"),
    "HEA_ICD10_DS635":  ("Distorsion af håndled", "Sprain of wrist"),
    "HEA_ICD10_DS663":  ("Læsion af ekstensorsene til anden specificeret finger i "
                         "håndled eller hånd",
                          "Injury of extensor tendon of other specified finger at "
                          "wrist or hand"),
    "HEA_ICD10_DT230":  ("Forbrænding UNS på håndled og hånd",
                          "Burn of wrist and hand, NOS"),
    "HEA_ICD10_DT922":  ("Følgetilstand efter fraktur i håndled eller hånd",
                          "Sequela of fracture of wrist or hand"),
    # Batch 14 — other mistranslations found
    "HEA_ICD10_DS833":  ("Fraktur af ledbrusk i knæled",
                          "Fracture of articular cartilage of knee"),
    "HEA_ICD10_DS534":  ("Distorsion af albueled", "Sprain of elbow joint"),
    "HEA_ICD10_DL024F": ("Absces på skinneben", "Abscess of the shin"),
    "HEA_ICD10_DK590A": ("Kronisk forstoppelse", "Chronic constipation"),
    # Batch 15 — strube (larynx/throat) mistranslations
    "HEA_ICD10_DD141":  ("Godartet tumor i strubehovedet",
                          "Benign neoplasm of the larynx"),
    "HEA_ICD10_DZ031XE": ("Observation pga. mistanke om kræft i struben eller svælget",
                          "Observation for suspicion of cancer of the larynx or pharynx"),
    "HEA_ICD10_DZ963":  ("Tilstand med kunstig strube", "Condition with artificial larynx"),
    "HEA_ICD10_DJ37":   ("Kronisk strubekatar og luftrørskatar",
                          "Chronic laryngitis and tracheitis"),
    "HEA_ICD10_DQ319":  ("Medfødt misdannelse i strubehovedet UNS",
                          "Congenital malformation of the larynx, NOS"),
    "HEA_ICD10_DS135":  ("Distorsion i strubehovedet", "Sprain of the larynx"),
    "HEA_ICD10_DA155":  ("Tuberkulose i struben, luftrøret eller bronkier verificeret "
                         "bakteriologisk eller histologisk",
                          "Tuberculosis of larynx, trachea or bronchus, confirmed "
                          "bacteriologically or histologically"),
    # Batch 16 — livmoder / livmoderhals (uterus / cervix) mistranslations
    "HEA_ICD10_DN71":   ("Betændelsestilstande i livmoderen, undtagen livmoderhalsen",
                          "Inflammatory diseases of uterus, except cervix"),
    "HEA_ICD10_DQ518":  ("Anden medfødt misdannelse i livmoder eller livmoderhals",
                          "Other congenital malformation of uterus or cervix"),
    "HEA_ICD10_DQ519":  ("Medfødt misdannelse i livmoder eller livmoderhals UNS",
                          "Congenital malformation of uterus or cervix, NOS"),
    # Batch 17 — vagina / rectocele
    "HEA_ICD10_DN816":  ("Vaginalt enterocele", "Vaginal enterocele"),
    "HEA_ICD10_DN818D": ("Lateraldefekt i vagina", "Lateral vaginal wall defect"),
    # Batch 18 — lyske (groin / inguinal)
    "HEA_ICD10_DC774C": ("Metastase i lymfeknude i lyske",
                          "Metastasis in inguinal lymph node"),
    "HEA_ICD10_DC774":  ("Metastase eller kræft UNS i lymfeknude i lyske eller "
                         "underekstremitet",
                          "Metastasis or cancer NOS in lymph node in groin or "
                          "lower extremity"),
    # Batch 19 — prostata
    "HEA_ICD10_DC791J": ("Fjernmetastase i prostata",
                          "Secondary malignant neoplasm of the prostate"),
    # Batch 20 — barsel (puerperium)
    "HEA_ICD10_DO990A": ("Anæmi som komplicerer barselsperiode",
                          "Anaemia complicating the puerperium"),
    # Batch 21 — mellemøre (middle ear) → not "midfacial"
    "HEA_ICD10_DD140":  ("Godartet tumor i mellemøre, næsehulen eller bihule",
                          "Benign neoplasm of middle ear, nasal cavity or paranasal sinuses"),
    "HEA_ICD10_DH669":  ("Mellemørebetændelse UNS", "Otitis media, NOS"),
    "HEA_ICD10_DH660":  ("Akut purulent mellemørebetændelse",
                          "Acute suppurative otitis media"),
    "HEA_ICD10_DH652":  ("Kronisk serøs mellemørebetændelse",
                          "Chronic serous otitis media"),
    # Batch 22 — endetarm (rectum) → not colon / intestinal wall
    "HEA_ICD10_DC209":  ("Kræft i endetarmen", "Cancer of the rectum"),
    "HEA_ICD10_DD129A": ("Godartet tumor i endetarmsåbningen",
                          "Benign neoplasm of anus"),
    "HEA_ICD10_DZ018A": ("Kontakt som følge af positiv screening for tyk- og "
                         "endetarmskræft (det nationale screeningsprogram)",
                          "Contact following positive screening for colorectal "
                          "cancer (national screening programme)"),
    # Batch 23 — bindevæv (connective tissue) → not ligament / fascia
    "HEA_ICD10_DD212":  ("Godartet tumor i bindevæv i underekstremitet",
                          "Benign neoplasm of connective tissue of lower extremity"),
    "HEA_ICD10_DD213":  ("Godartet tumor i bindevæv i thorax",
                          "Benign neoplasm of connective tissue of thorax"),
    "HEA_ICD10_DD219":  ("Godartet tumor i bindevæv UNS",
                          "Benign neoplasm of connective tissue, NOS"),
    # Batch 24 — untranslated DA
    "HEA_ICD10_DJ479":  ("Bronkiektasi", "Bronchiectasis"),
    # Batch 25 — endetarm again (in follow-up / anamnese contexts)
    "HEA_ICD10_DZ081G": ("Kontrolundersøgelse efter strålebehandling af kræft i endetarm",
                          "Follow-up examination after radiotherapy for rectal cancer"),
    "HEA_ICD10_DZ850G": ("Anamnese med kræft i endetarm",
                          "History of rectal cancer"),
    # Batch 26 — bindevæv (connective tissue), MT keeps saying "fascia"
    "HEA_ICD10_DC491":  ("Kræft i bindevæv og bløddelsvæv i overekstremitet",
                          "Cancer of connective and soft tissue of upper extremity"),
    "HEA_ICD10_DD200":  ("Godartet tumor i bindevæv i retroperitoneum",
                          "Benign neoplasm of connective tissue of retroperitoneum"),
    "HEA_ICD10_DD211":  ("Godartet tumor i bindevæv i overekstremitet",
                          "Benign neoplasm of connective tissue of upper extremity"),
    "HEA_ICD10_DD215":  ("Godartet tumor i bindevæv i bækkenet",
                          "Benign neoplasm of connective tissue of pelvis"),
    "HEA_ICD10_DD216":  ("Godartet tumor i bindevæv i kroppen UNS",
                          "Benign neoplasm of connective tissue of trunk, NOS"),
    "HEA_ICD10_DD217":  ("Godartet tumor i bindevæv med anden lokalisation",
                          "Benign neoplasm of connective tissue with other localisation"),
    # Batch 27 — more mellemøre
    "HEA_ICD10_DH651C": ("Akut mellemørebetændelse uden pusdannelse UNS",
                          "Acute nonsuppurative otitis media, NOS"),
    "HEA_ICD10_DZ038H": ("Observation pga. mistanke om gigt- eller bindevævssygdom",
                          "Observation for suspicion of rheumatic or connective-tissue disease"),
    # Batch 28 — lænd (loin / lower back) → not thigh/groin
    "HEA_ICD10_DS300":  ("Kontusion af lænden eller bækkenet",
                          "Contusion of lower back and pelvis"),
    "HEA_ICD10_DS300B": ("Kontusion af lænden", "Contusion of lower back"),
    "HEA_ICD10_DS310":  ("Åbent sår på lænden eller bækkenet",
                          "Open wound of lower back and pelvis"),
    "HEA_ICD10_DT001":  ("Overfladiske læsioner af både thorax, abdomen, lænden og bækkenet",
                          "Superficial injuries of thorax, abdomen, lower back and pelvis"),
    # Batch 29 — misc mistranslated
    "HEA_ICD10_DR091":  ("Lungehindebetændelse IKA", "Pleurisy / pleuritis, NEC"),
    "HEA_ICD10_DN938C": ("Abnorm blødning fra livmoderen efter fødsel",
                          "Abnormal bleeding from uterus after delivery"),
    "HEA_ICD10_DC795":  ("Fjernmetastase i knogle eller knoglemarven",
                          "Distant metastasis in bone or bone marrow"),
    "HEA_ICD10_DT182":  ("Fremmedlegeme i mavesækken", "Foreign body in the stomach"),
    "HEA_ICD10_DT172":  ("Fremmedlegeme i svælget", "Foreign body in the pharynx"),
    "HEA_ICD10_DH019":  ("Betændelse af øjenlåg UNS", "Inflammation of eyelid, NOS"),
    "HEA_ICD10_DD259":  ("Fibromyom i livmoderen UNS", "Uterine fibroid, NOS"),
    # Batch 30 — mellemørebetændelse → otitis media (consistent)
    "HEA_ICD10_DH650":  ("Akut serøs mellemørebetændelse", "Acute serous otitis media"),
    "HEA_ICD10_DH653":  ("Kronisk mucinøs mellemørebetændelse",
                          "Chronic mucoid otitis media"),
    "HEA_ICD10_DH659":  ("Mellemørebetændelse uden pusdannelse UNS",
                          "Nonsuppurative otitis media, NOS"),
    "HEA_ICD10_DH661":  ("Kronisk purulent tubotympanisk mellemørebetændelse",
                          "Chronic tubotympanic suppurative otitis media"),
    "HEA_ICD10_DH663":  ("Anden form for kronisk purulent mellemørebetændelse",
                          "Other chronic suppurative otitis media"),
    # Batch 31 — underben / underkæbe / intervertebral disc
    "HEA_ICD10_DS034":  ("Distorsion af underkæben", "Sprain of lower jaw"),
    "HEA_ICD10_DS828":  ("Fraktur af anden del af underben",
                          "Fracture of other part of lower leg"),
    "HEA_ICD10_DS899":  ("Læsion i knæregion eller på underben UNS",
                          "Injury of knee region or lower leg, NOS"),
    "HEA_ICD10_DM50":   ("Sygdomme i halshvirvelsøjlens båndskiver",
                          "Cervical intervertebral disc disorders"),
    # Batch 32 — artrose (osteoarthritis) vs arthritis mixups, and misc
    "HEA_ICD10_DM159":  ("Polyartrose UNS", "Polyosteoarthritis, NOS"),
    "HEA_ICD10_DM161A": ("Primær hofteledsartrose UNS",
                          "Primary osteoarthritis of hip, NOS"),
    "HEA_ICD10_DM162":  ("Dysplastisk dobbeltsidig hofteledsartrose",
                          "Dysplastic bilateral osteoarthritis of hip"),
    "HEA_ICD10_DM181":  ("Primær enkeltsidig artrose i tommelfingers rodled",
                          "Primary unilateral osteoarthritis of first carpometacarpal joint (thumb)"),
    "HEA_ICD10_DM189":  ("Artrose i tommelfingers rodled UNS",
                          "Osteoarthritis of first carpometacarpal joint (thumb), NOS"),
    "HEA_ICD10_DM199":  ("Artrose UNS", "Osteoarthritis, NOS"),
    "HEA_ICD10_DM250":  ("Hæmartrose", "Haemarthrosis"),
    "HEA_ICD10_DR219":  ("Hududslæt UNS", "Skin rash, NOS"),
    "HEA_ICD10_DH101":  ("Akut allergisk konjunktivitis",
                          "Acute allergic conjunctivitis"),
    # Batch 33 — misc
    "HEA_ICD10_DS636":  ("Distorsion af fingerled", "Sprain of finger joint"),
    "HEA_ICD10_DJ00":   ("Forkølelse", "Common cold"),
    "HEA_ICD10_DN42":   ("Andre sygdomme i blærehalskirtlen",
                          "Other diseases of prostate"),
    "HEA_ICD10_DN41":   ("Betændelse i blærehalskirtlen",
                          "Inflammation of prostate (prostatitis)"),
    "HEA_ICD10_DG459A": ("Spasme i cerebral arterie", "Cerebral artery spasm"),
    "HEA_ICD10_DO15":   ("Fødselskrampe", "Eclampsia"),
    "HEA_ICD10_DG404C": ("Infantile spasmer", "Infantile spasms"),
    # Batch 34 — synsnedsættelse (visual impairment) & skelen (strabismus) mixed up
    "HEA_ICD10_DH542":  ("Moderat synsnedsættelse på begge øjne",
                          "Moderate visual impairment, both eyes"),
    "HEA_ICD10_DH543":  ("Let eller ingen synsnedsættelse på begge øjne",
                          "Mild or no visual impairment, both eyes"),
    "HEA_ICD10_DH545":  ("Svær synsnedsættelse på eet øje",
                          "Severe visual impairment in one eye"),
    "HEA_ICD10_DH546":  ("Moderat synsnedsættelse på eet øje",
                          "Moderate visual impairment in one eye"),
    "HEA_ICD10_DH547":  ("Synsnedsættelse UNS", "Visual impairment, NOS"),
    "HEA_ICD10_DH498":  ("Anden skelen forårsaget af lammelse",
                          "Other paralytic strabismus"),
    "HEA_ICD10_DH499":  ("Skelen ved lammelse UNS", "Paralytic strabismus, NOS"),
    "HEA_ICD10_DH49":   ("Skelen ved lammelse af øjenmuskler",
                          "Paralytic strabismus"),
    # Batch 35 — other specific mistranslations
    "HEA_ICD10_DK137":  ("Anden eller ikke nærmere specificeret sygdom i mundslimhinde",
                          "Other or unspecified disease of oral mucosa"),
    "HEA_ICD10_DN40":   ("Forstørret blærehalskirtel", "Enlarged prostate"),
    "HEA_ICD10_DO41":   ("Andre sygdomme i amnionvæske og fosterhinder",
                          "Other disorders of amniotic fluid and fetal membranes"),
    # Batch 36 — obstetric: placenta / umbilical cord
    "HEA_ICD10_DO45":   ("For tidlig løsning af moderkagen",
                          "Premature separation of placenta (placental abruption)"),
    "HEA_ICD10_DO459":  ("For tidlig løsning af moderkagen UNS",
                          "Placental abruption, NOS"),
    "HEA_ICD10_DO449":  ("Forliggende moderkage UNS", "Placenta praevia, NOS"),
    "HEA_ICD10_DO69":   ("Fødsel med navlesnorskomplikation",
                          "Labour and delivery complicated by umbilical cord complications"),
    "HEA_ICD10_DP546":  ("Vaginal blødning hos nyfødt",
                          "Vaginal haemorrhage in newborn"),
    "HEA_ICD10_DP211":  ("Let neonatal asfyksi", "Mild neonatal asphyxia"),
    # Batch 37 — bryst (chest) vs breast; tilknytning (attachment)
    "HEA_ICD10_DR074":  ("Brystsmerter UNS", "Chest pain, NOS"),
    "HEA_ICD10_DR073":  ("Andre brystsmerter", "Other chest pain"),
    "HEA_ICD10_DN951E": ("Klimakteriel svimmelhed",
                          "Menopausal dizziness (vertigo)"),
    "HEA_ICD10_DF941":  ("Reaktiv tilknytningsforstyrrelse i barndom",
                          "Reactive attachment disorder of childhood"),
    "HEA_ICD10_DR418A": ("Hukommelsessvigt", "Memory failure"),
    # Batch 38 — brysthule (chest cavity) vs breast
    "HEA_ICD10_DC398":  ("Kræft i brysthule og luftveje overgribende flere lokalisationer",
                          "Cancer of the chest cavity and airways, overlapping lesion"),
    "HEA_ICD10_DD177C": ("Lipom i mamma", "Lipoma of breast"),
    # Batch 39 — grå stær (cataract) — MT invented many wrong translations
    "HEA_ICD10_DH250":  ("Begyndende aldersbetinget grå stær",
                          "Early age-related cataract"),
    "HEA_ICD10_DH251":  ("Aldersbetinget nukleær grå stær",
                          "Age-related nuclear cataract"),
    "HEA_ICD10_DH259":  ("Aldersbetinget grå stær (>=50 år) UNS",
                          "Age-related cataract (≥50 years), NOS"),
    "HEA_ICD10_DH260":  ("Grå stær hos småbørn, børn, unge og voksne",
                          "Cataract in infants, children, adolescents and adults"),
    "HEA_ICD10_DH260B": ("Grå stær hos børn og unge (2 år til <18 år)",
                          "Cataract in children and adolescents (2 to <18 years)"),
    "HEA_ICD10_DH260C": ("Grå stær hos yngre voksne (18 år til <50 år)",
                          "Cataract in younger adults (18 to <50 years)"),
    "HEA_ICD10_DH262":  ("Grå stær sekundært til anden øjensygdom",
                          "Cataract secondary to other eye disease"),
    "HEA_ICD10_DH269":  ("Grå stær UNS", "Cataract, NOS"),
    "HEA_ICD10_DH280":  ("Diabetisk grå stær", "Diabetic cataract"),
    "HEA_ICD10_DQ120":  ("Medfødt grå stær", "Congenital cataract"),
    # Batch 40 — glaslegeme (vitreous body) vs lens of eye
    "HEA_ICD10_DH432":  ("Krystallinske aflejringer i øjets glaslegeme",
                          "Crystalline deposits in the vitreous body"),
    "HEA_ICD10_DH433":  ("Anden opacitet i øjets glaslegeme",
                          "Other vitreous opacity"),
    "HEA_ICD10_DH438":  ("Anden forandring i øjets glaslegeme",
                          "Other change in the vitreous body"),
    "HEA_ICD10_DH438D": ("Kollaps af øjets glaslegeme",
                          "Vitreous collapse"),
    "HEA_ICD10_DH439":  ("Forandring i øjets glaslegeme UNS",
                          "Change in the vitreous body, NOS"),
    # Batch 41 — nethinde (retina)
    "HEA_ICD10_DH330":  ("Nethindeløsning med ruptur",
                          "Retinal detachment with retinal break"),
    "HEA_ICD10_DH332A": ("Nethindeløsning uden ruptur",
                          "Retinal detachment without retinal break"),
    "HEA_ICD10_DH358":  ("Anden forandring i nethinde", "Other retinal disorder"),
    "HEA_ICD10_DH359":  ("Forandring i nethinde UNS", "Retinal disorder, NOS"),
    "HEA_ICD10_DD312":  ("Godartet tumor i nethinde", "Benign neoplasm of retina"),
    "HEA_ICD10_DQ141":  ("Medfødt misdannelse i nethinden",
                          "Congenital malformation of retina"),
    # Batch 42 — bihulebetændelse (sinusitis) → "bilateral salpingitis" !
    "HEA_ICD10_DJ019":  ("Akut bihulebetændelse UNS", "Acute sinusitis, NOS"),
    "HEA_ICD10_DJ329":  ("Kronisk bihulebetændelse UNS", "Chronic sinusitis, NOS"),
    # Batch 43 — brainstem
    "HEA_ICD10_DC717":  ("Kræft i hjernestammen eller 4. ventrikel",
                          "Cancer of the brainstem or fourth ventricle"),
    # Batch 44 — mavekatar (gastritis) vs acute abdomen / hernia
    "HEA_ICD10_DK291":  ("Anden form for akut mavekatar",
                          "Other form of acute gastritis"),
    "HEA_ICD10_DK296":  ("Anden form for mavekatar", "Other form of gastritis"),
    # Batch 45 — hyperemesis gravidarum
    "HEA_ICD10_DO210":  ("Graviditetsopkastninger i lettere grad",
                          "Mild hyperemesis gravidarum"),
    # Batch 46 — hæshed, abstinens kramper, pandehule, bihule, kæbe-tinding
    "HEA_ICD10_DR490A": ("Hæshed", "Hoarseness"),
    "HEA_ICD10_DF1031": ("Abstinenstilstand forårsaget af alkoholbrug med kramper",
                          "Alcohol withdrawal state with seizures"),
    "HEA_ICD10_DF1131": ("Abstinenstilstand forårsaget af opioidbrug med kramper",
                          "Opioid withdrawal state with seizures"),
    "HEA_ICD10_DJ011":  ("Akut pandehulebetændelse", "Acute frontal sinusitis"),
    "HEA_ICD10_DJ321":  ("Kronisk pandehulebetændelse", "Chronic frontal sinusitis"),
    "HEA_ICD10_DJ018":  ("Anden form for akut bihulebetændelse",
                          "Other form of acute sinusitis"),
    "HEA_ICD10_DS014":  ("Åbent sår på hagen eller i kæbe-tindingeregion",
                          "Open wound of chin or temporomandibular region"),
    "HEA_ICD10_DS014B": ("Åbent sår i kæbe-tindingeregion",
                          "Open wound of temporomandibular region"),
    "HEA_ICD10_DQ858":  ("Anden fakomatose IKA", "Other phakomatosis, NEC"),
    "HEA_ICD10_DK598D": ("Sterkoraldiarré", "Stercoral diarrhoea"),
    # Batch 47 — brok (hernia) mistranslated as pain/rupture/diarrhea
    "HEA_ICD10_DK43":   ("Bugvægsbrok", "Ventral hernia"),
    "HEA_ICD10_DK45":   ("Andre former for brok i bugvæggen",
                          "Other abdominal wall hernia"),
    "HEA_ICD10_DK46":   ("Abdominalt brok ikke nærmere specificeret",
                          "Unspecified abdominal hernia"),
    "HEA_ICD10_DN43":   ("Vandbrok og sædbrok", "Hydrocele and spermatocele"),
    # Batch 48 — lymphoma, myxoedema, pregnancy edema
    "HEA_ICD10_DD728G": ("Pseudolymfom", "Pseudolymphoma"),
    "HEA_ICD10_DE031":  ("Medfødt myksødem uden struma",
                          "Congenital myxoedema without goitre"),
    "HEA_ICD10_DO120":  ("Graviditetsødem", "Pregnancy-related oedema"),
    # Batch 49 — kløe (itch) → "claw"/"fissure"/"eczema"
    "HEA_ICD10_DL290":  ("Analkløe", "Pruritus ani"),
    "HEA_ICD10_DL298":  ("Anden form for kløe", "Other form of pruritus"),
    "HEA_ICD10_DL299":  ("Kløe UNS", "Pruritus, NOS"),
    # Batch 50 — bihule (sinus) → "bile duct" / "parotid gland"
    "HEA_ICD10_DT170":  ("Fremmedlegeme i bihule", "Foreign body in paranasal sinus"),
    "HEA_ICD10_DD140C": ("Godartet tumor i bihule",
                          "Benign neoplasm of paranasal sinus"),
    "HEA_ICD10_DC318":  ("Kræft i bihuler overgribende flere lokalisationer",
                          "Cancer of paranasal sinuses, overlapping lesion"),
    # Batch 51 — galdeveje (bile ducts) → salivary glands / ureter
    "HEA_ICD10_DK83":   ("Andre sygdomme i galdevejene",
                          "Other diseases of biliary tract"),
    "HEA_ICD10_DK839":  ("Galdevejssygdom UNS", "Biliary tract disease, NOS"),
    "HEA_ICD10_DK851":  ("Akut pankreatitis forårsaget af galdevejslidelse",
                          "Acute pancreatitis caused by biliary-tract disease"),
    "HEA_ICD10_DC249M": ("Kræft i galdeveje med metastaser",
                          "Cancer of the bile ducts with metastases"),
    # Batch 52 — lårbrok (femoral hernia), nyresten variants
    "HEA_ICD10_DK41":   ("Lårbrok", "Femoral hernia"),
    "HEA_ICD10_DN200M": ("Metabolisk nyresten", "Metabolic kidney stone"),
    "HEA_ICD10_DN200F": ("Funktionel nyresten", "Functional kidney stone"),
    # Batch 53 — lyske (groin) mistranslated
    "HEA_ICD10_DL022T": ("Absces i lysken", "Abscess of the groin"),
    "HEA_ICD10_DL022D": ("Furunkel i lysken", "Furuncle of the groin"),
    # Batch 54 — tooth / jaw anatomy
    "HEA_ICD10_DK004B": ("Hypoplasi af tandemalje", "Hypoplasia of tooth enamel"),
    "HEA_ICD10_DK071C": ("Prominerende overkæbe", "Prominent maxilla (upper jaw)"),
    "HEA_ICD10_DK072C": ("Dybt bid med fortandssammenbid",
                          "Deep bite with incisor malocclusion"),
    "HEA_ICD10_DC031":  ("Kræft i tandkødet i undermunden", "Cancer of lower gum"),
    # Batch 55 — brystben (sternum), haleben (coccyx)
    "HEA_ICD10_DS222":  ("Fraktur af brystbenet", "Fracture of sternum"),
    "HEA_ICD10_DS234B": ("Distorsion af brystbenet", "Sprain of sternum"),
    "HEA_ICD10_DS322":  ("Fraktur af halebenet", "Fracture of coccyx"),
    "HEA_ICD10_DL05":   ("Hårrede over halebenet", "Pilonidal cyst"),
    # Batch 56 — tibial nerve
    "HEA_ICD10_DG574":  ("Neuropati i nervus tibialis", "Tibial nerve neuropathy"),
    # Batch 57 — livmoder (uterus) bleeding mistranslated as abdominal-cavity / placenta
    "HEA_ICD10_DN93":   ("Anden abnorm blødning fra livmoderen og vagina",
                          "Other abnormal bleeding from the uterus and vagina"),
    "HEA_ICD10_DN938":  ("Anden form for abnorm blødning fra livmoderen eller vagina",
                          "Other abnormal bleeding from the uterus or vagina"),
    "HEA_ICD10_DN938A": ("Anden form for abnorm blødning fra livmoderen",
                          "Other abnormal uterine bleeding"),
    "HEA_ICD10_DN939B": ("Abnorm blødning fra livmoderen UNS",
                          "Abnormal uterine bleeding, NOS"),
    # Batch 58 — biskjoldbruskkirtel (parathyroid) → parotid
    "HEA_ICD10_DD351":  ("Godartet tumor i biskjoldbruskkirtel",
                          "Benign neoplasm of parathyroid gland"),
    "HEA_ICD10_DC750":  ("Kræft i biskjoldbruskkirtel",
                          "Cancer of the parathyroid gland"),
    # Batch 59 — insulinoma
    "HEA_ICD10_DD137A": ("Insulinom", "Insulinoma"),
    # Batch 60 — puerperium breast/lactation
    "HEA_ICD10_DO92":   ("Andre forstyrrelser i brystkirtel og amning i barselsperiode",
                          "Other disorders of the breast and lactation in the puerperium"),
    # Batch 61 — snorken (snoring), byld (abscess), lungebetændelse (pneumonia)
    "HEA_ICD10_DR065A": ("Snorken", "Snoring"),
    "HEA_ICD10_DK61":   ("Byld i og omkring endetarmen",
                          "Abscess of anal and rectal regions"),
    "HEA_ICD10_DJ100":  ("Influenza med lungebetændelse forårsaget af anden type "
                         "influenzavirus",
                          "Influenza with pneumonia caused by other influenza virus type"),
    "HEA_ICD10_DJ18":   ("Lungebetændelse forårsaget af ikke nærmere specificeret "
                         "mikroorganisme",
                          "Pneumonia, organism unspecified"),
    "HEA_ICD10_DJ17":   ("Lungebetændelse ved sygdomme klassificeret andetsteds",
                          "Pneumonia in diseases classified elsewhere"),
    "HEA_ICD10_DJ16":   ("Lungebetændelse forårsaget af andre infektiøse agentia IKA",
                          "Pneumonia due to other infectious organisms, NEC"),
    "HEA_ICD10_DJ69":   ("Lungeinflammation forårsaget af aspiration af faste og "
                         "flydende stoffer",
                          "Pneumonitis due to aspiration of solids and liquids"),
    "HEA_ICD10_DP23":   ("Medfødt lungebetændelse", "Congenital pneumonia"),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    with open(MASTER_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames)
        rows = list(reader)

    applied = 0
    not_found = 0
    da_mismatch = 0
    for r in rows:
        if r["code"] not in FIXES:
            continue
        expected_da, new_en = FIXES[r["code"]]
        # Sanity check: confirm DA matches what we expect
        if r["description_da"].strip() != expected_da:
            da_mismatch += 1
            print(f"  DA mismatch {r['code']}:")
            print(f"    expected: {expected_da!r}")
            print(f"    actual:   {r['description_da']!r}")
            continue
        r["description_en"] = new_en
        r["description_short"] = new_en
        r["description_en_source"] = "translated"
        applied += 1

    # Check dictionary fully applied
    codes_in_master = {r["code"] for r in rows}
    for code in FIXES:
        if code not in codes_in_master:
            not_found += 1
            print(f"  Dictionary code not in MASTER: {code}")

    print(f"\nFixed: {applied} rows")
    print(f"DA mismatches (skipped): {da_mismatch}")
    print(f"Codes not in MASTER:     {not_found}")

    if args.dry_run:
        print("\n[dry-run] no changes written")
        return

    with open(MASTER_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"\nWrote {len(rows)} rows")


if __name__ == "__main__":
    main()
