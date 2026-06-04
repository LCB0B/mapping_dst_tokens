#!/usr/bin/env python3
"""HEA_speciale translation: expand Danish billing abbreviations -> full Danish
(description_da_full) and translate -> English (description_en), for the unique
worklist strings. Glossary + structural rules authored by Opus; rows still
containing Danish letters after translation are flagged for manual review.

Outputs scripts/hea_speciale_auto.tsv (id, da_full, en, confidence, residual).
"""
import csv, re, sys

WL = "scripts/hea_speciale_worklist.csv"
OUT = "scripts/hea_speciale_auto.tsv"

# --- Danish billing abbreviation -> full Danish word (matched as whole tokens,
#     with optional trailing '.'; case-insensitive) ---
ABBR = {
    "kons": "konsultation", "kons": "konsultation", "kont": "kontrol",
    "us": "undersøgelse", "und": "undersøgelse", "uds": "undersøgelse", "un": "undersøgelse",
    "beh": "behandling", "vejl": "vejledning", "svang": "svangre",
    "tlf": "telefon", "bes": "besøg", "ope": "operation", "operat": "operation", "op": "operation",
    "flg": "følgende", "fjern": "fjernelse", "till": "tillæg",
    "u": "uden", "m": "med", "t": "til", "i": "i", "af": "af", "o": "og",
    "pat": "patienter", "reg": "regional", "sympat": "sympaticus", "bl": "blokade",
    "mikr": "mikroskopi", "bakt": "bakteriologisk", "frs": "forsendelse", "bio": "biopsi",
    "matr": "materiale", "mat": "materiale", "eks": "eksklusive", "led": "led", "se": "sene",
    "kl": "klinisk", "tand": "tandbehandling", "punkt": "punktur", "grp": "gruppe",
    "ps": "personer", "sikr": "sikring", "adg": "adgang", "lægepr": "lægepraksis",
    "db": "dobbelt", "funku": "funktionsundersøgelse", "rygs": "rygsøjle", "an": "anæstesi",
    "alm": "almindelig", "us.": "undersøgelse", "per": "periode", "pr": "per",
    "sa": "samme", "hj": "hjem", "li": "linse", "cysto": "cystoskopi", "flex": "fleksibel",
    "diagn": "diagnostisk", "diagnost": "diagnostisk", "tym": "tympanometri",
    "fkt": "funktion", "lungefkt": "lungefunktion", "indiv": "individuel",
    "samtalebeh": "samtalebehandling", "koord": "koordineret", "rygsm": "rygsmerter",
    "kont": "kontrol", "rev": "reversibilitet", "konsul": "konsultation",
}

# --- Danish term/phrase -> English (longest-first phrase replacement on the
#     expanded Danish). Covers the recurring billing vocabulary. ---
DA2EN = {
    "grå stær": "cataract", "grå-stær": "cataract",
    "regional §2-aftale": "regional §2 agreement",
    "procedure ikke dokumenteret": "procedure not documented",
    "konsultation i stedet for hjemmebesøg": "consultation in lieu of home visit",
    "opfølgende hjemmebesøg": "follow-up home visit",
    "aftalt specifik forebyggelsesindsats": "agreed specific preventive effort",
    "e-mail konsultation": "e-mail consultation", "e-konsultation": "e-consultation",
    "telefon konsultation": "telephone consultation", "telefonkonsultation": "telephone consultation",
    "anæstesi med intubation": "anaesthesia with intubation",
    "anæstesiologi": "anaesthesiology", "anæstesi": "anaesthesia", "bedøvelse": "anaesthesia",
    "konsultation": "consultation", "undersøgelse": "examination", "behandling": "treatment",
    "vejledning": "guidance", "svangre": "pregnant women", "svangerskab": "pregnancy",
    "graviditet": "pregnancy", "telefon": "telephone", "besøg": "visit", "hjemmebesøg": "home visit",
    "operation": "operation", "kontrol": "follow-up", "følgende": "subsequent", "senere": "later",
    "fjernelse": "removal", "tillæg": "supplement", "afstandstillæg": "distance supplement",
    "akupunktur": "acupuncture", "biopsi": "biopsy", "materiale": "material", "blokade": "block",
    "sympaticus": "sympathetic", "mikroskopi": "microscopy", "bakteriologisk": "bacteriological",
    "forsendelse": "shipment", "punktur": "puncture", "gruppe": "group", "personer": "persons",
    "sikring": "assurance", "adgang": "access", "lægepraksis": "medical practice",
    "dobbelt": "double", "funktionsundersøgelse": "function test", "rygsøjle": "spine",
    "klinisk": "clinical", "tandbehandling": "dental treatment", "cystoskopi": "cystoscopy",
    "fleksibel": "flexible", "diagnostisk": "diagnostic", "tympanometri": "tympanometry",
    "audiometri": "audiometry", "abortstøttesamtale": "abortion counselling",
    "blod": "blood", "urin": "urine", "antistof": "antibody", "antistoffer": "antibodies",
    "led": "joint", "sene": "tendon", "linse": "lens", "øjen": "eye", "øre": "ear",
    "barn": "child", "børn": "children", "ældre": "elderly", "voksen": "adult",
    "første": "first", "anden": "second", "halvt": "half", "helt": "whole", "år": "years",
    "uden": "without", "med": "with", "til": "to", "og": "and", "eller": "or", "per": "per",
    "patienter": "patients", "patient": "patient", "kronikere": "chronic patients",
    "leddegigt": "rheumatoid arthritis", "tolk": "interpreter", "tolkebistand": "interpreter assistance",
    "samtale": "conversation", "pårørende": "relatives", "attest": "certificate",
    "vaccination": "vaccination", "prøve": "test", "prøvetagning": "sample collection",
    "røntgenundersøgelse": "X-ray examination", "røntgen": "X-ray", "scanning": "scan",
    "henvisning": "referral", "henviser": "refers", "indrullering": "enrolment",
    "almindelig": "ordinary", "regional": "regional", "kommunen": "the municipality",
    "i stedet for": "in lieu of", "i alt": "in total", "i øvrigt": "otherwise",
    "afslutning": "conclusion", "kronikerhonorar": "chronic-care fee", "årsstatus": "annual status",
    "eksklusive": "excluding", "inklusive": "including", "samme": "same", "hjem": "home",
    "spec": "specialty",
    # --- extended vocabulary (from residual-token analysis) ---
    "anæstæsi": "anaesthesia", "kortvarig": "short-term", "længvarig": "long-lasting",
    "langvarig": "long-lasting", "maske": "mask", "intubation": "intubation",
    "kørselsgodtgørelse": "mileage allowance", "kørselsgodtgør": "mileage allowance",
    "tidsforbrugstillæg": "time-spent supplement", "afstandstillæg": "distance supplement",
    "rådgivning": "advice", "praktiserende læge": "general practitioner", "læge": "doctor",
    "lægehjælp": "medical care", "praktiserende": "practising",
    "sygebesøg": "sick-home visit", "indlæggelse": "admission", "indlæg": "orthotic insole",
    "ingen tekst tilgængelig": "no text available", "tilgængelig": "available",
    "sår": "wound", "småsår": "minor wounds", "betændelse": "inflammation",
    "hånd": "hand", "håndled": "wrist", "knæ": "knee", "lår": "thigh", "bækken": "pelvis",
    "kæbeled": "temporomandibular joint", "kæbehule": "maxillary sinus", "næse": "nose",
    "næsen": "the nose", "åre": "vein", "åreknuder": "varicose veins", "årekn": "varicose veins",
    "injektion": "injection", "injekt": "injection", "optræning": "rehabilitation training",
    "optræn": "rehabilitation training", "holdtræning": "group training", "holdtræn": "group training",
    "træning": "training", "afspænding": "relaxation therapy", "opfølgning": "follow-up",
    "dødsattest": "death certificate", "attest": "certificate", "større": "larger",
    "særlig": "special", "fjernelse": "removal", "fj": "removal", "fjern": "removal",
    "fæces": "faeces", "bøjle": "brace", "bøjler": "braces", "blærekaterisation": "bladder catheterisation",
    "elektrokardiografi": "electrocardiography", "elkardiografi": "electrocardiography",
    "elektroencefalografi": "electroencephalography", "hæmorroider": "haemorrhoids",
    "hæmorr": "haemorrhoids", "hammertå": "hammer toe", "cutanprøve": "skin test",
    "møde": "meeting", "urinprøvetagning": "urine sampling", "urinprøve": "urine test",
    "blodprøve": "blood test", "blodprøvetagning": "blood sampling", "prøvetagning": "sample collection",
    "røde": "red", "rød": "red", "grøn": "green", "opsætning": "fitting", "opsætn": "fitting",
    "anlæg": "placement", "oplivningsforsøg": "resuscitation attempt", "påsætning": "attachment",
    "påsæt": "attach", "påbegyndt": "commenced", "korrektion": "correction", "korr": "correction",
    "excision": "excision", "exc": "excision", "allergi": "allergy", "allergisk": "allergic",
    "allerg": "allergy", "væske": "fluid", "søvn": "sleep", "søvnkurve": "sleep curve",
    "hørelse": "hearing", "hør": "hearing", "differentialtælling": "differential count",
    "hæmoglobin": "haemoglobin", "sjælland": "Sjælland", "hovedstaden": "Hovedstaden",
    "midtjylland": "Midtjylland", "nordjylland": "Nordjylland", "syddanmark": "Syddanmark",
    "øfeldt": "Øfeldt", "på": "on", "når": "when", "ifm": "in connection with",
    "undersøg": "examination", "operere": "operate", "oper": "operation", "operativ": "operative",
    "ydelse": "service", "tekst": "text", "kaustisk": "caustic", "kaust": "caustic",
    "præmolar": "premolar", "præmo": "premolar", "molar": "molar", "tand": "tooth",
    "af": "of", "ved": "by", "samt": "and", "mv": "etc.", "stær": "cataract",
    "gråstær": "cataract", "for": "for", "fra": "from", "halv": "half",
    # extended batch 2
    "inkl": "incl.", "tilfælde": "case", "genindlæggelse": "readmission", "genindlæg": "readmission",
    "tåreveje": "tear ducts", "cutanprøver": "skin tests", "mellemøreoperation": "middle-ear operation",
    "mellemøreop": "middle-ear operation", "stritøre": "protruding ears", "spiserør": "oesophagus",
    "lænde": "lower back", "overkæbe": "upper jaw", "underkæbe": "lower jaw", "regelmæssig": "regular",
    "før": "before", "døende": "dying", "opsøgende": "outreach", "urinundersøgelse": "urine examination",
    "børneundersøgelse": "child examination", "lungefunktionsundersøgelse": "lung function test",
    "læsioner": "lesions", "læsion": "lesion", "ørevoks": "earwax", "håndflade": "palm",
    "ledbåndsrekonstruktion": "ligament reconstruction", "øjenlåg": "eyelid", "svælg": "pharynx",
    "efterfølgende": "subsequent", "sfærisk": "spherical", "spiral": "coil (IUD)",
    "ekg": "ECG", "ekkokardiografi": "echocardiography", "ætsning": "cauterisation",
    "fødselsforberedelse": "antenatal class", "graviditetsundersøgelse": "pregnancy examination",
    "børneorm": "pinworm", "ligsyn": "death inspection", "rådgiver": "adviser",
    # dotted lab/billing compounds (whole-phrase)
    "tlf.rådg.prakt.læge": "telephone advice from GP",
    "sikr.u.adg.t.lægepr.": "assurance without access to medical practice",
    "sikr.u.adg.t.lægepr": "assurance without access to medical practice",
    "b-differentialtæll.": "B-differential count", "b-hæmoglob.(fotom.)": "B-haemoglobin (photometric)",
    "svælg-strept.antig.": "throat streptococcus antigen", "udf.dødsa.s.1": "issuing death certificate",
    # extended batch 3 (surgical/ophthalmology shorthand)
    "længvarig": "long-lasting", "længvar": "long-lasting", "søvnkurve": "sleep recording",
    "søvnk": "sleep recording", "efterstær": "after-cataract", "nethindeløsning": "retinal detachment",
    "nethindeløsn": "retinal detachment", "tåresæk": "lacrimal sac", "tåresækken": "the lacrimal sac",
    "nødvendig": "necessary", "øjenlåg": "eyelid", "indadvendt": "inward-turned (entropion)",
    "udadvendt": "outward-turned (ectropion)", "stæroperation": "cataract operation",
    "stæropr": "cataract operation", "yaglaser": "YAG laser", "tillægsydelse": "supplementary service",
    "tillægsyd": "supplementary service", "slidgigt": "osteoarthritis", "slidg": "osteoarthritis",
    "storetå": "big toe", "håndflade": "palm", "håndfl": "palm",
    "ledbåndsrekonstruktion": "ligament reconstruction", "ledbåndsrekon": "ligament reconstruction",
    "knæoperation": "knee operation", "artroskopi": "arthroscopy", "intraokulær": "intraocular",
    "konservativ": "conservative", "trommehinde": "eardrum", "mellemøre": "middle ear",
    "skeleoperation": "strabismus operation", "skelen": "strabismus", "grøn stær": "glaucoma",
    "grønstær": "glaucoma", "nyfødt": "newborn", "spædbarn": "infant",
    # extended batch 4 (remaining freq>=2 tail)
    "urinprøvetagning": "urine sampling", "urinprøvetag": "urine sampling",
    "øvelsesterapi": "exercise therapy", "øvre": "upper", "øje": "eye", "øjet": "the eye",
    "høreapparat": "hearing aid", "høreprøve": "hearing test", "høreundersøgelse": "hearing examination",
    "kæbe": "jaw", "øreprop": "earplug", "vævsmikroskopi": "tissue microscopy", "væv": "tissue",
    "hudkræft": "skin cancer", "kræft": "cancer", "hæmatologisk": "haematological",
    "blære": "bladder", "gærsvamp": "yeast infection", "overlæbe": "upper lip", "læbe": "lip",
    "blodtryksmåling": "blood-pressure measurement", "måling": "measurement", "fremmøde": "attendance",
    "lyske": "groin", "højre": "right", "venstre": "left", "bilateral": "bilateral",
    "åreknud": "varicose veins", "spiseforstyrrelse": "eating disorder", "samtaleterapi": "talk therapy",
    "hos": "to", "akut": "acute", "kronisk": "chronic", "diverse": "various", "ekstra": "extra",
    # extended batch 5 (PLO full-text + remaining tail)
    "svangerskabsforebyggende": "contraceptive", "benyttelse": "use", "metoder": "methods",
    "metode": "method", "præparation": "preparation", "præp": "preparation",
    "prøveforberedelse": "test preparation", "prøveforb": "test preparation",
    "forsøgsordning": "trial scheme", "vedrørende": "regarding", "måneder": "months", "måned": "month",
    "næseblødning": "nosebleed", "næsebl": "nosebleed", "alfaføtoprotein": "alpha-fetoprotein",
    "blodåre": "blood vessel", "antinucleære": "antinuclear", "antinukleære": "antinuclear",
    "røntgenoptagelse": "X-ray image", "mæslinger": "measles", "næsetamponade": "nasal packing",
    "udlån": "loan", "ødembehandling": "oedema treatment", "ødem": "oedema", "ørepolypper": "ear polyps",
    "polypper": "polyps", "tidskrævende": "time-consuming", "særligt": "especially",
    "børneundersøgelser": "child examinations", "spædbørn": "infants", "halsbetændelse": "tonsillitis",
    "i": "in", "efter": "after", "individuel": "individual", "funktion": "function",
    "lungefunktion": "lung function", "samtalebehandling": "talk therapy", "koordineret": "coordinated",
    "reversibilitet": "reversibility", "rygsmerter": "back pain", "videre": "etc.", "mv.": "etc.",
    # --- lab analyte/allergen vocabulary (KPLL/SSI/laboratory codes) ---
    "dyrkning": "culture", "dyrkn": "culture", "forsendelse": "shipment", "forsendel": "shipment",
    "forsende": "shipment", "antistof": "antibody", "antistoffer": "antibodies",
    "indsendte prøver": "submitted samples", "indsendte": "submitted", "prøver": "samples",
    "blodprøve exp": "blood sample, dispatch", "exp": "dispatch", "blodprøve": "blood sample",
    "mikroskopi": "microscopy", "mikrosk": "microscopy", "farvet": "stained", "farv": "stained",
    "ufarvet": "unstained", "ufar": "unstained", "sekret": "secretion", "sek": "secretion",
    "mørkefeltsmikroskopi": "dark-field microscopy", "mørkefeltsmikros": "dark-field microscopy",
    "glukose": "glucose", "leukocytter": "leukocytes", "leukocyt": "leukocytes",
    "trombocytter": "platelets", "trombocyt": "platelets", "erytrocyt": "erythrocyte",
    "cylindre": "casts", "kornede": "granular", "korn": "granular", "kromosomundersøgelse": "chromosome analysis",
    "kromosomunders": "chromosome analysis", "kviksølv": "mercury", "kapillær": "capillary",
    "blødningstid": "bleeding time", "glucosetolerance": "glucose tolerance", "glucose toleran": "glucose tolerance",
    "lactosebelastning": "lactose tolerance test", "lactosebelastn": "lactose tolerance test",
    "binyrebark": "adrenal cortex", "intrinsic faktor": "intrinsic factor", "intrinsic fak": "intrinsic factor",
    "døgn": "24-hour", "blodtryksmåling": "blood-pressure measurement", "bt-måling": "blood-pressure measurement",
    "for fremmøde i lab": "for attendance at the laboratory", "fremmøde": "attendance",
    "hæmokromatosegen": "haemochromatosis gene", "lungefunktion før/efter bronkodilatator": "lung function before/after bronchodilator",
    # allergens (Danish -> English)
    "acajounød": "cashew nut", "acetylsalicyl": "acetylsalicylic acid", "blåmusling": "blue mussel",
    "bladselleri": "celery", "bladsel": "celery leaf", "bøg": "beech", "børnekost": "children's food panel",
    "engrottehår": "rat epithelium", "engrotteh": "rat epithelium", "fisk": "fish", "grå bynke": "mugwort",
    "grå el": "grey alder", "hasselnød": "hazelnut", "hvidløg": "garlic", "hønsekød": "chicken meat",
    "jordbær": "strawberry", "jordnød": "peanut", "kokosnød": "coconut", "komælk": "cow's milk",
    "koskæl": "cow dander", "kødpanel": "meat panel", "blåmuslinger": "blue mussels", "hønsekod": "chicken meat",
    "erhverv": "occupational panel", "erhv": "occupational panel", "formaldehyd": "formaldehyde", "formaldeh": "formaldehyde",
    "lactalbumin": "lactalbumin", "lactalbum": "lactalbumin", "lactoglobulin": "lactoglobulin", "lactoglobu": "lactoglobulin",
    # microbiology / serology analytes
    "borrelia": "Borrelia", "gonokok": "gonococcus", "clamydia": "chlamydia", "chlamydia": "chlamydia",
    "influenza": "influenza", "legionella": "Legionella", "helicobacter": "Helicobacter", "helicob": "Helicobacter",
    "denguevirus": "dengue virus", "dengue virus": "dengue virus", "difteritoksin": "diphtheria toxin",
    "endomysium": "endomysium", "gliadin": "gliadin", "cardiolipin": "cardiolipin", "imipramin": "imipramine",
    "benzodiazepiner": "benzodiazepines", "benzodiazepin": "benzodiazepines", "bilirubin": "bilirubin",
    "fraktioneret": "fractionated", "frakt": "fractionated", "basisk fraktion": "alkaline fraction", "basisk frakt": "alkaline fraction",
    "amylase": "amylase", "pancreas": "pancreatic", "panc": "pancreatic", "albumin": "albumin",
    "alfaføtoprotein": "alpha-fetoprotein", "alfa føtoprotein": "alpha-fetoprotein", "alfa føtoprot": "alpha-fetoprotein",
    "ankeltryk": "ankle pressure", "ankeltr": "ankle pressure", "lymfogranuloma venereum": "lymphogranuloma venereum",
    # --- extended batch 6 (clinical/lab tail) ---
    "tapning": "drainage", "forebyggelse": "prevention", "tandrensning": "dental scaling",
    "rensning": "cleaning", "fyldning": "filling", "glasionomerfyldning": "glass-ionomer filling",
    "biologisk": "biological", "journaloptagelse": "record-taking", "ultralydsscanning": "ultrasound scan",
    "ultralydsundersøgelse": "ultrasound examination", "ultralydsus": "ultrasound examination",
    "henvendelse": "contact", "blodtagning": "blood draw", "blodprøvetagning": "blood sampling",
    "udstedelse": "issuing", "indkaldelse": "recall", "suturfjernelse": "suture removal",
    "parasitologisk": "parasitological", "cøliaki": "coeliac", "flåtpakke": "tick panel",
    "genotypning": "genotyping", "sensorisk": "sensory", "ø-celle": "islet cell",
    "østrogenstatus": "oestrogen status", "tænder": "teeth", "tand": "tooth",
    "holdundervisning": "group instruction", "strækbehandling": "traction treatment",
    "røntgenundersøgelse": "X-ray examination", "røntgenunder": "X-ray examination", "tolkning": "interpretation",
    "bøjle": "brace", "bøjler": "braces", "bækkenbund": "pelvic floor", "bækkenb": "pelvic floor",
    "fødende": "woman in labour", "sygebesøg": "sick visit", "sygebesøgsstedet": "site of the sick visit",
    "forbindelse": "connection", "ansøgning": "application", "anvendelse": "use",
    "hjælpepersonale": "support staff", "hjælpepers": "support staff", "hjælpeper": "support staff",
    "fremmødehonorar": "attendance fee", "patientledsagelse": "patient escort", "rejsetillæg": "travel supplement",
    "ormeæg": "worm eggs", "øjemed": "purpose", "udtagning": "sampling", "udtrækning": "extraction",
    "udtrækn": "extraction", "forløbsydelse": "care-pathway service", "årskontrol": "annual check",
    "årlig": "annual", "slimsæk": "bursa", "psykisk": "psychological", "journal": "record",
    "telefonisk": "by telephone", "telefonisk koordinering": "telephone coordination",
    " accelereret": "accelerated", "screeningsundersøgelse": "screening examination",
    "mavesmerter": "abdominal pain", "afføring": "stool", "høfeber": "hay fever",
    "fødevareprovokation": "food challenge test", "øjenprovokation": "eye challenge test",
    "anstrengelsesprovokation": "exercise challenge test", "provokationsforsøg": "challenge test",
    "provokation": "challenge", "løbebånd": "treadmill", "adfærdsforstyrrelse": "behavioural disorder",
    "adfærd": "behaviour", "familieterapi": "family therapy", "gruppeterapi": "group therapy",
    "legeterapi": "play therapy", "forældre": "parents", "kautionsbegæring": "cover request",
    "kautionsbeg": "cover request", "karforandringer": "vascular lesions", "pigmentforandringer": "pigment changes",
    "pigmentforandr": "pigment changes", "hårvækst": "hair growth", "uønsket": "unwanted",
    "keloid": "keloid", "kelo": "keloid", "hæmangiomer": "haemangiomas", "hæmangioner": "haemangiomas",
    "eksem": "eczema", "tjærebade": "tar baths", "scleroserende": "sclerosing", "scleroser": "sclerosing",
    "intralæsionel": "intralesional", "intralæsion": "intralesional", "forhudsforsnævring": "phimosis",
    "forhudsfor": "phimosis", "forhudsfors": "phimosis", "alloplastik": "alloplasty", "allopla": "alloplasty",
    "flytning": "transfer", "flytn": "transfer", "hud": "skin", "næse": "nose", "øre": "ear",
    "konusundersøgelse": "cone biopsy examination", "konusunder": "cone biopsy examination",
    "vaginalcytologisk": "vaginal cytology", "immunhistokemisk": "immunohistochemical", "immunhistokemi": "immunohistochemistry",
    "vævsmikroskopi": "tissue microscopy", "spiserør": "oesophagus", "strube": "larynx",
    "fremmedlegeme": "foreign body", "drøbel": "uvula", "drøbelen": "the uvula",
    "spytkirtel": "salivary gland", "spytkirt": "salivary gland", "spytkirtl": "salivary gland",
    "trommehinde": "eardrum", "kæbehule": "maxillary sinus", "kæbeh": "maxillary sinus",
    "ligevægt": "balance", "ligev": "balance", "hypofarynx": "hypopharynx", "hyp": "hypopharynx",
    "skaltilpasning": "shell fitting", "skaltilp": "shell fitting", "udlevering": "dispensing", "udlev": "dispensing",
    "instruktion": "instruction", "instrukt": "instruction", "tubulering": "ventilation-tube insertion",
    "tubulat": "ventilation-tube insertion", "tubulation": "ventilation-tube insertion",
    "tværfaglig": "multidisciplinary", "neglel": "nail bed", "spoleben": "radius bone", "spoleb": "radius bone",
    "seneknude": "ganglion", "senekn": "ganglion", "springfinger": "trigger finger", "springfing": "trigger finger",
    "blefarokalasis": "blepharochalasis", "blefarokal": "blepharochalasis", "synovektomi": "synovectomy",
    "synovect": "synovectomy", "synov": "synovectomy", "knogleforskydning": "bone displacement",
    "knogleforskyds": "bone displacement", "nerveafklemning": "nerve entrapment release",
    "korsben": "sacrum", "korsbenshvirvler": "sacral vertebrae", "galdeblære": "gallbladder",
    "tømning": "emptying", "tømnings": "voiding", "urologi": "urology",
    # --- extended batch 7: allergens, foods, analytes (lab tail) ---
    "æble": "apple", "pære": "pear", "valnød": "walnut", "paranød": "brazil nut", "pecannød": "pecan nut",
    "nøddepanel": "nut panel", "sesamfrø": "sesame seed", "soyabønne": "soybean", "soya": "soy",
    "oksekød": "beef", "svinekød": "pork", "tunfisk": "tuna", "løg": "onion", "æggeblomme": "egg yolk",
    "æggehvide": "egg white", "rajgræs": "ryegrass", "rødgran": "norway spruce", "rug": "rye",
    "birk": "birch", "hassel": "hazel", "elm": "elm", "el": "alder", "bynke": "mugwort",
    "katteskæl": "cat dander", "kat": "cat", "hundeskæl": "dog dander", "hund": "dog",
    "husstøvmide": "house dust mite", "skimmelsvampe": "moulds", "skimmel": "mould",
    "rejer": "shrimp", "torsk": "cod", "laks": "salmon", "krabbe": "crab", "kiwi": "kiwi",
    "banan": "banana", "gulerod": "carrot", "kartoffel": "potato", "tomat": "tomato",
    "hvede": "wheat", "byg": "barley", "havre": "oats", "ris": "rice", "mandel": "almond",
    "mælk": "milk", "ost": "cheese", "kakao": "cocoa", "honning": "honey", "gær": "yeast",
    # analytes / serology
    "væksthormon": "growth hormone", "tetanustoksin": "tetanus toxin", "tetanustox": "tetanus toxin",
    "toxoplasma": "Toxoplasma", "toxoplas": "Toxoplasma", "rubella": "rubella", "rubel": "rubella",
    "parotitis": "mumps", "parotit": "mumps", "mononukleose": "mononucleosis", "mononucleo": "mononucleosis",
    "mononu": "mononucleosis", "streptococcus": "streptococcus", "streptoc": "streptococcus",
    "metamyelocyt": "metamyelocyte", "neutrofilocyt": "neutrophil", "parietalcelle": "parietal cell",
    "parietalcel": "parietal cell", "somatomedin": "somatomedin", "somatom": "somatomedin",
    "tripletest": "triple test", "trombofiliudredning": "thrombophilia work-up", "trombofiliudred": "thrombophilia work-up",
    "urinvejskonkrement": "urinary tract calculus", "urinvejskonkrem": "urinary tract calculus",
    "protein": "protein", "hæmoglobin": "haemoglobin", "priktest": "skin-prick test",
    "vævstransglutaminase": "tissue transglutaminase", "vævtr": "tissue transglutaminase",
    "parasitmikroskopi": "parasite microscopy", "parasitmik": "parasite microscopy",
    "mucor": "Mucor", "bloddyrkning": "blood culture", "bloddyrkn": "blood culture",
    "complement": "complement", "complem": "complement", "intrinsic": "intrinsic",
    "eryvolfrac": "erythrocyte volume fraction", "acetylsalicyl": "acetylsalicylic acid", "acetylsal": "acetylsalicylic acid",
    "allspec": "all specific", "kapillær": "capillary", "kapil": "capillary", "res": "result",
    "tpb": "TPB", "anca": "ANCA", "tsh": "TSH", "ssi": "SSI",
}

# Acronyms/notation to restore after lowercasing, and specimen suffixes
LAB_FIXUP = [(r"\bige\b", "IgE"), (r"\bab\b", "antibody"), (r"\bag\b", "antigen"),
             (r"\bdna\b", "DNA"), (r"\bhiv\b", "HIV"), (r"\bcmv\b", "CMV"), (r"\bebv\b", "EBV"),
             (r"\bccp\b", "CCP"), (r"\bpcr\b", "PCR"), (r"\brna\b", "RNA"), (r"\bekg\b", "ECG"),
             (r"\bpdt\b", "PDT"), (r"\bp-", "P-"), (r"\bb-", "B-"), (r"\bu-", "U-"),
             (r";p\b", " (plasma)"), (r";b\b", " (blood)"), (r";u\b", " (urine)"), (r";s\b", " (serum)"),
             (r"\bkonf\b", "confirmatory")]

DANISH = re.compile(r"[æøåÆØÅ]")
PROPER = {"øfeldt", "sjælland", "hovedstaden", "midtjylland", "nordjylland", "syddanmark"}


# common Danish words/abbrevs lacking æøå that indicate an incomplete translation
DA_BLOCKLIST = {"kons", "beh", "und", "indiv", "konsul", "rev", "ab", "fg", "obs",
                "tils", "med", "uden", "samt", "evt", "div", "iv", "akutte", "akut",
                "tapning", "vandbrok", "underben", "overben", "symmetrisk", "elm",
                "katekolaminer", "narkot", "ydelse", "ingen", "tekst", "videre", "behandl"}
# Danish morphology: word-endings that almost never occur in our English output
DA_SUFFIX = re.compile(r"(ning|else|isk|agtig|hed|inger|erne)$")
# English words that collide with the Danish suffix heuristic — do NOT flag these
ENGLISH_OK = {"training", "screening", "scanning", "planning", "monitoring", "imaging",
              "dressing", "fitting", "sampling", "swelling", "shipment", "casting"}


def has_residual_danish(en):
    """True if EN still contains an untranslated Danish fragment (ignoring kept
    proper nouns). Flags æ/ø/å, trailing-dot abbreviations, Danish word-endings,
    asterisk markers, and a blocklist of common Danish tokens."""
    if "*" in en:
        return True
    tmp = en.lower()
    for p in PROPER:
        tmp = tmp.replace(p, "")
    if DANISH.search(tmp):
        return True  # any æ/ø/å outside a kept proper noun = untranslated
    for t in re.split(r"[\s/,();]+", en):
        bare = t.strip().strip(".").lower()
        if not bare or bare in PROPER or not bare.isalpha():
            continue
        if DANISH.search(bare):
            return True
        if t.strip().endswith(".") and len(bare) >= 2:
            return True  # unexpanded abbreviation like "kons." / "lungefkt.us"
        if bare in ENGLISH_OK:
            continue
        if bare in DA_BLOCKLIST or DA_SUFFIX.search(bare):
            return True
        if bare in DA_BLOCKLIST:
            return True
    return False
# region §2 tag like "(regional §2-aftale, Region Syddanmark)" -> keep & translate
REGION_TAG = re.compile(r"\(regional §2-aftale, (Region \w+)\)")


def _expand_token(raw):
    """Expand a single whitespace-free token, splitting on '.' to handle dotted
    compounds (e.g. 'Lungefkt.us' -> 'lungefunktion undersøgelse')."""
    if not raw or raw.lower() in ("m.v", "m.v."):
        return "mv" if raw else raw
    if "." not in raw:
        k = raw.lower()
        return ABBR[k] if k in ABBR else raw
    parts, outp, changed = raw.split("."), [], False
    for p in parts:
        k = p.lower()
        if k in ABBR:
            outp.append(ABBR[k]); changed = True
        elif p:
            outp.append(p)
    return " ".join(outp) if changed else raw


def expand_abbrev(text):
    out = []
    for tok in re.split(r"(\s+|/|,)", text):
        if tok and not re.fullmatch(r"\s+|/|,", tok):
            out.append(_expand_token(tok))
        else:
            out.append(tok)
    return "".join(out)


def translate(da_full):
    s = da_full
    s = REGION_TAG.sub(r"(regional §2 agreement, \1)", s)
    low = s.lower()
    # phrase replacement, longest key first
    for k in sorted(DA2EN, key=len, reverse=True):
        low = re.sub(r"\b" + re.escape(k) + r"\b", DA2EN[k], low)
    for pat, rep in LAB_FIXUP:
        low = re.sub(pat, rep, low)
    return low


def main():
    rows = list(csv.DictReader(open(WL, encoding="utf-8")))
    out = []
    resid = 0
    for i, r in enumerate(rows):
        da = r["description_da"].replace("¯", "ø")  # fix residual mojibake (¯ -> ø)
        plo = r["plo_fuller"].strip()
        # specialty + procedure split
        m = re.match(r"^([^,]+),\s*(.*)$", da)
        spec_en = r["specialty_name_en"].strip()
        if m:
            proc_da = m.group(2)
            proc_da_full = plo if plo else expand_abbrev(proc_da)
            proc_en = translate(proc_da_full)
            da_full = f"{m.group(1)}, {proc_da_full}"
            proc_en = proc_en[:1].upper() + proc_en[1:] if proc_en else proc_en
            en = f"{spec_en}, {proc_en}" if spec_en else proc_en
        else:
            da_full = da
            en = spec_en if spec_en else translate(expand_abbrev(da))
        residual = has_residual_danish(en)
        conf = "low" if residual or "documented)" in da else ("high" if not residual else "medium")
        if residual:
            resid += 1
        out.append((i, da_full, re.sub(r"\s+", " ", en).strip(), conf, "Y" if residual else ""))
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("# id\tda_full\ten\tconfidence\tresidual\n")
        for t in out:
            f.write("\t".join(map(str, t)) + "\n")
    print(f"Wrote {OUT}: {len(out)} rows | residual-Danish in EN: {resid} ({100*resid/len(out):.0f}%)")


if __name__ == "__main__":
    main()
