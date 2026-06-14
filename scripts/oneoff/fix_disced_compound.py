#!/usr/bin/env python3
"""Fix EDU_disced descriptions: replace wrong-granularity '(compound:)' labels.

All 790 EDU_disced rows carried descriptions of the form
'<4-digit-prefix label> (compound: <8-digit code>)' — i.e. the label of the
4-digit DISCED programme *group* was pasted onto every 8-digit programme code
(source tags CSV:EDU_disced_compound_start/_end). 776 of 790 contradict the
official 8-digit titles.

The official Danish titles for ALL 790 codes exist in the DST AUDD/UDD↔DISCED
crosswalk tables (crosswalks/edu/df_{AUDD,UDD}_DISCED.parquet, column
code4/title4; the two tables agree on every overlapping code). This script:

  - description_da     <- official crosswalk title (source='crosswalk_edu_disced')
  - description_en     <- existing MASTER translation of the same Danish title
                          where one exists (94 titles, audd/udd rows), else a
                          Fable 5 translation composed from the base-name
                          dictionary below (description_en_source='fable-5-edu')
  - description_short  <- same as description_en
  - description        (legacy column) left untouched for history

A full audit worklist is written to
scripts/worklists/disced_title_translations.tsv.

Run from the repo root. Regenerate MAPPINGS/ and SOURCE_CATALOG.csv afterwards.
"""

import csv
import re
import sys

import pandas as pd

MASTER = "MASTER_CATEGORY_MAPPINGS.csv"
WORKLIST = "scripts/worklists/disced_title_translations.tsv"

# Danish level suffixes kept as-is in English (house style, cf. EDU_udd rows)
SUFFIXES = {"KVU", "MVU", "LVU", "BACH", "Ph.d.", "AMU"}

# English translations of the unique base names (level suffix stripped).
# Translation only — the Danish meaning is given by the official DST title.
BASE_EN = {
    "0. klasse": "Grade 0 (kindergarten class)",
    "1 erhverssprog, korrespondent": "One business language, correspondent",
    "8.klasse": "8th grade",
    "Adgangseksamen - videregående uddannelse": "Entrance examination for higher education",
    "Adgangsgivende værkstedsskoleforløb": "Qualifying workshop school programme",
    "Administration mv.": "Administration etc.",
    "Administration, forvaltning og ledelse": "Administration, public governance and management",
    "Administrationsøkonom mv.": "Administrative economist etc.",
    "Andre pædagogiske uddannelser": "Other pedagogical programmes",
    "Andre udenlandske gymnasiale uddannelser": "Other foreign upper secondary programmes",
    "Animationsuddannelse": "Animation programme",
    "Antropologi": "Anthropology",
    "Arabisk": "Arabic",
    "Arkitektur": "Architecture",
    "Arkæologi": "Archaeology",
    "Arkæologi, forhistorisk": "Archaeology, prehistoric",
    "Arkæologi, klassisk": "Archaeology, classical",
    "Arkæologi, middelalder": "Archaeology, medieval",
    "Arkæologi, nærorientalsk": "Archaeology, Near Eastern",
    "Astronomi": "Astronomy",
    "Audiologopædi": "Speech and hearing therapy (audiologopedics)",
    "Automatik og automationsproces": "Automatics and automation processes",
    "Bandagist": "Orthopaedic technician (bandagist)",
    "Biblioteks- og informationsuddannelser": "Library and information programmes",
    "Bil, fly og andre transportmidler, grundforløb": "Cars, aircraft and other means of transport, basic course",
    "Bildende kunst": "Visual arts",
    "Bioanalytiker": "Biomedical laboratory scientist",
    "Bioinformatik": "Bioinformatics",
    "Biokemi og molekylær biologi": "Biochemistry and molecular biology",
    "Biologi": "Biology",
    "Biomedicin": "Biomedicine",
    "Biomedicn og molekylær biomedicin": "Biomedicine and molecular biomedicine",
    "Bioteknologi": "Biotechnology",
    "Boligmontering og møbelpolstring mv.": "Home furnishing and furniture upholstery etc.",
    "Brolægger og struktør mv.": "Paver and structural worker etc.",
    "Bygge og anlæg uden nærmere angivelse": "Building and construction, not further specified",
    "Bygge og anlæg, grundforløb": "Building and construction, basic course",
    "Byggeri- og anlægsteknik i øvrigt": "Other building and civil engineering",
    "Bygnings- og anlægsteknik": "Building and civil engineering",
    "Bygnings- og brugerservice, grundforløb": "Building and user services, basic course",
    "Bygningskonstruktør": "Constructing architect",
    "Byudvikling og byplanlægning mv.": "Urban development and town planning etc.",
    "Chauffør mv., personbefordring": "Driver etc., passenger transport",
    "Chauffør mv., vejgodstransport": "Driver etc., road freight transport",
    "Cnc-teknikuddannelsen": "CNC technology programme",
    "Cykel-, auto- og skibsmekanikere uden nærmere angivelse": "Bicycle, car and ship mechanics, not further specified",
    "Dans": "Dance",
    "Danseruddannelser": "Dance programmes",
    "Dansk-Fransk Bacalaurétte": "Danish-French Baccalauréat",
    "Dansk-Tysk studentereksamen": "Danish-German upper secondary leaving examination",
    "Dansk-nordisk sprog og litteratur": "Danish-Nordic language and literature",
    "Data- og kommunikationsteknik": "Data and communication technology",
    "Datalogi og datahåndtering": "Computer science and data management",
    "Designer uden nærmere angivelse": "Designer, not further specified",
    "Designer, digitale medier, kommunikation": "Designer, digital media, communication",
    "Designer, grafisk design": "Designer, graphic design",
    "Designer, industriel design": "Designer, industrial design",
    "Designer, keramik og glas": "Designer, ceramics and glass",
    "Designer, mode, accessories": "Designer, fashion, accessories",
    "Designer, mode, tekstil, beklædning": "Designer, fashion, textiles, clothing",
    "Designer, møbel, rum, indretning": "Designer, furniture, space, interior design",
    "Designer, unika design": "Designer, one-off (unika) design",
    "Designteknolog": "Design technologist",
    "Designuddannelser uden nærmere angivelse": "Design programmes, not further specified",
    "Det merkantile område, grundforløb": "The mercantile field, basic course",
    "Detailhandelsuddannelse": "Retail trade programme",
    "Detailslagter": "Retail butcher",
    "Didaktik og undervisningsteori": "Didactics and teaching theory",
    "Digital design og interaktionsdesign": "Digital design and interaction design",
    "Digital media": "Digital media",
    "Digitale medier og design": "Digital media and design",
    "Dramaturgi og teatervidenskab": "Dramaturgy and theatre studies",
    "Dyr, planter og natur, grundforløb": "Animals, plants and nature, basic course",
    "EU-studier og europæiske studier": "EU studies and European studies",
    "Ejendoms- og anden service": "Property and other services",
    "Ejendoms- og anden service uden nærmere angivelse": "Property and other services, not further specified",
    "Elektronik i øvrigt": "Other electronics",
    "Elektronik i øvrigt, teknisk": "Other electronics, technical",
    "Elektronik i øvrigt, teknisk videnskab": "Other electronics, engineering science",
    "Energi- og stærkstrømsteknisk": "Energy and high-voltage engineering",
    "Energiteknologi i øvrigt": "Other energy technology",
    "Engelsk": "English",
    "Engros- og detailhandel": "Wholesale and retail trade",
    "Entreprenør- og landbrugsmaskinmekaniker": "Construction and agricultural machinery mechanic",
    "Ergo- og fysioterapeut": "Occupational therapist and physiotherapist",
    "Ergoterapi": "Occupational therapy",
    "Erhvervsfaglige uddannelser uden nærmere angivelse": "Vocational programmes, not further specified",
    "Erhvervsfiskeri mv.": "Commercial fishing etc.",
    "Erhvervsintroduktion, kurser": "Introduction to trades, courses",
    "Erhvervssprog og europæiske studier": "Business language and European studies",
    "Erhvervssprog, afgangseksamen EA": "Business language, EA final examination",
    "Erhvervssprog, begynderprøve": "Business language, beginner examination",
    "Erhvervssprog, diplomprøve ED": "Business language, ED diploma examination",
    "Erhvervssprog, interpret.": "Business language, interpreter",
    "Erhvervssprog, kombineret uden nærmere angivelse": "Business language, combined, not further specified",
    "Erhvervssprog, ling.merc.": "Business language, ling.merc.",
    "Erhvervssprog, øvrige uddannelser": "Business language, other programmes",
    "Erhvervssproglig grundstudium": "Business language basic studies",
    "Erhvervssproglige bachelorer": "Business language bachelors",
    "Erhvervsøkonomi uden nærmere angivelse": "Business economics, not further specified",
    "Erhvervsøkonomi, HA": "Business economics, HA",
    "Erhvervsøkonomi, HD": "Business economics, HD",
    "Erhvervsøkonomi, cand.merc.": "Business economics, cand.merc.",
    "Erhvervsøkonomi-erhvervssprog mv., negot.": "Business economics and business language etc., negot.",
    "Ernæring og sundhed": "Nutrition and health",
    "Ernæringsassistenter": "Nutrition assistants",
    "Eskimologi": "Eskimology",
    "Etnologi": "Ethnology",
    "Europas historie": "History of Europe",
    "European Baccalaureate": "European Baccalaureate",
    "Farmaci og lægemiddelvidenskab": "Pharmacy and pharmaceutical sciences",
    "Farmakonom": "Pharmaconomist",
    "Film og medievidenskab": "Film and media studies",
    "Film og tv uddannelser uden nærmere angivelse": "Film and TV programmes, not further specified",
    "Film- og tv-produktion": "Film and TV production",
    "Filmklipper": "Film editor",
    "Filmproducer": "Film producer",
    "Filosofi": "Philosophy",
    "Finans mv.": "Finance etc.",
    "Finansuddannelse": "Finance programme",
    "Finansøkonom mv.": "Financial economist etc.",
    "Finsk": "Finnish",
    "Flere erhvervssprog, korrespondent": "Several business languages, correspondent",
    "Flygtninge adgangskursus til videregående udd.": "Refugee access course for higher education",
    "Folkeskolelærer": "Primary and lower secondary school teacher",
    "Folkesundhedsvidenskab": "Public health science",
    "Forsikringsvidenskab": "Actuarial science",
    "Forsvaret": "The Danish Defence",
    "Fotograf, film og tv": "Photographer, film and TV",
    "Fotojournalist": "Photojournalist",
    "Fra jord til bord, grundforløb": "From farm to table, basic course",
    "Fransk": "French",
    "Fritid, kultur og sport mv.": "Leisure, culture and sports etc.",
    "Frontline pc-supporter": "Frontline PC supporter",
    "Fysik": "Physics",
    "Fysioterapi": "Physiotherapy",
    "Fysiske fag i øvrigt": "Other physical sciences",
    "Fængselsvæsnet": "The prison service",
    "Fødevare- og ernæringsvidenskab i øvrigt": "Other food and nutrition science",
    "Fødevarer i øvrigt": "Other food subjects",
    "Fødevarer, Bio- og laboratorieteknik uden nærmere angivelse": "Food, bio- and laboratory technology, not further specified",
    "Fødevarer, bio- og laboratorieteknik uden nærmere angivelse": "Food, bio- and laboratory technology, not further specified",
    "Fødevareuddannelser i øvrigt": "Other food programmes",
    "Fødevarevidenskab": "Food science",
    "Gartner efteruddannelse": "Gardener continuing education",
    "Gastronomuddannelse": "Gastronome (chef) programme",
    "Gastronomuddannelser i øvrigt": "Other gastronome programmes",
    "Geodæsi og geoinformatik": "Geodesy and geoinformatics",
    "Geofysik": "Geophysics",
    "Geografi": "Geography",
    "Geologi": "Geology",
    "Globalisering og internationale samfundsstudier": "Globalisation and international social studies",
    "Grafisk design og kommunikation": "Graphic design and communication",
    "Grafisk teknik": "Graphic technology",
    "Grafisk teknik og medieproduktion uden nærmere angivelse": "Graphic technology and media production, not further specified",
    "Grafisk-teknisk": "Graphic-technical",
    "Greenkeeper og groundman": "Greenkeeper and groundsman",
    "Grundskole 10. årgang": "Grade 10 (lower secondary school)",
    "Grundskole 7.-9. årgang": "Grades 7-9 (lower secondary school)",
    "Grundskole til og med 6. årgang": "Primary school up to grade 6",
    "Græsk": "Greek",
    "Gymnasiet uden linieopdeling, 1.g.": "Gymnasium (general upper secondary) without streaming, year 1",
    "Gymnasiet uden linieopdeling, 2.g.": "Gymnasium (general upper secondary) without streaming, year 2",
    "Gymnasiet uden linieopdeling, 3.g.": "Gymnasium (general upper secondary) without streaming, year 3",
    "HF 2-årig, 1. år": "HF two-year, 1st year",
    "HF 2-årig, 2. år": "HF two-year, 2nd year",
    "Handel og markedsføring mv.": "Trade and marketing etc.",
    "Handels- og markedsføringsøkonom mv.": "Trade and marketing economist etc.",
    "Handelsuddannelse": "Commercial trade programme",
    "Havne- og terminaluddannelser": "Port and terminal programmes",
    "Hebraisk": "Hebrew",
    "Hf 2-årig": "HF two-year",
    "Hhx 1-årig": "HHX one-year",
    "Hhx 3-årig": "HHX three-year",
    "Hhx 3-årig, 1. år": "HHX three-year, 1st year",
    "Hhx 3-årig, 2. år": "HHX three-year, 2nd year",
    "Hhx 3-årig, 3. år": "HHX three-year, 3rd year",
    "Historie": "History",
    "Htx, 1. år": "HTX, 1st year",
    "Htx, 2. år": "HTX, 2nd year",
    "Htx, 3. år": "HTX, 3rd year",
    "Humanistisk uden nærmere angivelse": "Humanities, not further specified",
    "Humanistiske uddannelser i øvrigt": "Other humanities programmes",
    "Husdyrvidenskab": "Animal science",
    "Husholdningskursus, andre": "Household course, other",
    "Håndværk og teknik, grundforløb": "Crafts and technology, basic course",
    "Idehistorie": "History of ideas",
    "Idræt": "Sports science",
    "Indianske sprog og kulturer": "Native American languages and cultures",
    "Indien og Sydasienstudier": "India and South Asia studies",
    "Indoeuropæisk": "Indo-European",
    "Indonesisk": "Indonesian",
    "Informatik": "Informatics",
    "Informationsvidenskab mv.": "Information science etc.",
    "Ingen uddannelse Indv.udd": "No education (immigrant education record)",
    "Installatør af stærkstrøms- og vvs-teknik uden nærmere angivelse": "Installer of electrical and plumbing technology, not further specified",
    "Installatør af stærkstrømsteknik": "Electrical (high-voltage) installer",
    "Installatør af vvs-teknik": "Plumbing (VVS) installer",
    "Instruktør, film og tv": "Director, film and TV",
    "Interaktionsdesign": "Interaction design",
    "International Baccalaureate": "International Baccalaureate",
    "International Baccalaureate, 1. år": "International Baccalaureate, 1st year",
    "International Baccalaureate, 2. år": "International Baccalaureate, 2nd year",
    "It og sundhedsvidenskab": "IT and health science",
    "It-uddannelser": "IT programmes",
    "Italiensk": "Italian",
    "Japanstudier": "Japanese studies",
    "Jern og metal": "Iron and metal",
    "Jordbrug og natur i øvrigt": "Other agriculture and nature",
    "Jordbrug, fødevarer og miljø kombineret": "Agriculture, food and environment combined",
    "Jordbrug, natur og miljø uden nærmere angivelse": "Agriculture, nature and environment, not further specified",
    "Jordbrugsbiologi": "Agricultural biology",
    "Jordbrugsteknologisk": "Agricultural technology",
    "Jordbrugsvidenskab": "Agricultural science",
    "Jordbrugsøkonomi": "Agricultural economics",
    "Jordemoder": "Midwife",
    "Jordemodervidenskab": "Midwifery science",
    "Journalist og journalistisk arbejde": "Journalist and journalistic work",
    "Journalistik": "Journalism",
    "Juniorofficerer": "Junior officers",
    "Jura": "Law",
    "Karosseriuddannelse": "Vehicle body programme",
    "Kemi": "Chemistry",
    "Kemi og bioteknologi": "Chemistry and biotechnology",
    "Kemisk og biokemisk teknologi": "Chemical and biochemical technology",
    "Kinastudier": "China studies",
    "Kiropraktor": "Chiropractor",
    "Klassisk Indisk - sanskrit": "Classical Indian - Sanskrit",
    "Klassisk filologi": "Classical philology",
    "Klassisk græsk-romersk": "Classical Graeco-Roman",
    "Klimaforandringer, vand og miljø": "Climate change, water and environment",
    "Kommunikation og formidling": "Communication and dissemination",
    "Kommunikation og formidling uden nærmere angivelse": "Communication and dissemination, not further specified",
    "Komponist og dirigent": "Composer and conductor",
    "Konservering - restaurering uden nærmere angivelse": "Conservation-restoration, not further specified",
    "Konservering - restaurering, grafisk": "Conservation-restoration, graphic",
    "Konservering - restaurering, kulturhistorisk": "Conservation-restoration, cultural history",
    "Konservering - restaurering, kunst": "Conservation-restoration, art",
    "Konservering - restaurering, monumental": "Conservation-restoration, monumental",
    "Konservering - restaurering, naturhistorisk": "Conservation-restoration, natural history",
    "Kontoruddannelse, generel og med speciale": "Office programme, general and specialised",
    "Koreastudier": "Korea studies",
    "Krop og stil, grundforløb": "Body and style, basic course",
    "Kultur og sprogmøde": "Culture and language encounters",
    "Kulturgeografi": "Cultural geography",
    "Kultursociologi": "Cultural sociology",
    "Kulturteori og kulturanalyse": "Cultural theory and cultural analysis",
    "Kundekontaktcenteruddannelse": "Customer contact centre programme",
    "Kunsthistorie": "Art history",
    "Kunsthåndværk": "Arts and crafts",
    "Kunstnerisk i øvrigt": "Other artistic",
    "Kunstnerisk uden nærmere angivelse": "Artistic, not further specified",
    "Kunstteori og -formidling": "Art theory and dissemination",
    "Laborant": "Laboratory technician",
    "Laboratorie-, fødevare- og procesteknologi": "Laboratory, food and process technology",
    "Laboratorie-, fødevare- og procesteknologi i øvrigt": "Other laboratory, food and process technology",
    "Lager- og terminaluddannelser": "Warehouse and terminal programmes",
    "Landbrugsuddannelse": "Agricultural programme",
    "Landinspektørvidenskab": "Chartered surveying science",
    "Landskabsarkitektur og -forvaltning": "Landscape architecture and management",
    "Latin": "Latin",
    "Ledelse i sundhedssektoren": "Management in the health sector",
    "Lingvistik": "Linguistics",
    "Litteraturvidenskab": "Comparative literature",
    "Lydteknik, musik": "Sound engineering, music",
    "Mad til mennesker, grundforløb": "Food for people, basic course",
    "Manuskriptuddannelse, film og tv": "Screenwriting programme, film and TV",
    "Marinarkæologi": "Maritime archaeology",
    "Maritime uddannelser": "Maritime programmes",
    "Maritime uddannelser i øvrigt": "Other maritime programmes",
    "Maskinmester": "Marine engineer (maskinmester)",
    "Maskinsnedker mv.": "Industrial joiner etc.",
    "Maskinteknik og maskinkonstruktion": "Mechanical engineering and machine design",
    "Maskinteknik og produktion uden nærmere angivelse": "Mechanical engineering and production, not further specified",
    "Maskinteknisk i øvrigt": "Other mechanical engineering",
    "Matematik": "Mathematics",
    "Matematik og økonomi": "Mathematics and economics",
    "Matematisk gymnasium, 1.g.": "Mathematics-stream gymnasium, year 1",
    "Matematisk gymnasium, 2.g.": "Mathematics-stream gymnasium, year 2",
    "Matematisk gymnasium, 3.g.": "Mathematics-stream gymnasium, year 3",
    "Matematisk studenterkursus 1. år": "Mathematics-stream studenterkursus, 1st year",
    "Matematisk studenterkursus 2. år": "Mathematics-stream studenterkursus, 2nd year",
    "Medialogi": "Medialogy",
    "Medicin": "Medicine",
    "Medicin og teknologi": "Medicine and technology",
    "Medicinalbiologi": "Medical biology",
    "Medicinalkemi mv.": "Medicinal chemistry etc.",
    "Medieproduktion, grundforløb": "Media production, basic course",
    "Medier og kommunikation i øvrigt": "Other media and communication",
    "Mejeribrugsvidenskab": "Dairy science",
    "Mejeriuddannelse": "Dairy programme",
    "Mekanik, transport og logistik, grundforløb": "Mechanics, transport and logistics, basic course",
    "Mellemøstens sprog uden nærmere angivelse": "Middle Eastern languages, not further specified",
    "Merkantile uddannelser i øvrigt": "Other mercantile programmes",
    "Merkantile uddannelser uden nærmere angivelse": "Mercantile programmes, not further specified",
    "Miljøbiologi": "Environmental biology",
    "Miljøkemi": "Environmental chemistry",
    "Miljøteknisk": "Environmental engineering",
    "Miljøteknologi mv.": "Environmental technology etc.",
    "Multimediedesign": "Multimedia design",
    "Music management": "Music management",
    "Musik og musikpædagogik": "Music and music pedagogy",
    "Musikteori": "Music theory",
    "Musikterapi": "Music therapy",
    "Musikuddannelser i øvrigt": "Other music programmes",
    "Musikvidenskab": "Musicology",
    "Nanoscience og nanobioscience": "Nanoscience and nanobioscience",
    "Nanoteknologi og nanobioteknologi": "Nanotechnology and nanobiotechnology",
    "Naturressourcer og miljø i øvrigt": "Other natural resources and environment",
    "Naturvidenskab i øvrigt": "Other natural sciences",
    "Naturvidenskab uden nærmere angivelse": "Natural sciences, not further specified",
    "Naturvidenskabelig miljøplanlægning": "Scientific environmental planning",
    "Naturvidenskabelige it-uddannelser i øvrigt": "Other natural science IT programmes",
    "Nederlandsk": "Dutch",
    "Odontologi": "Odontology (dentistry)",
    "Officer i flyvevåbnet": "Officer in the air force",
    "Officer i forsvaret uden nærmere angivelse": "Officer in the armed forces, not further specified",
    "Officer i hæren": "Officer in the army",
    "Officer i søværnet": "Officer in the navy",
    "Oldtidskundskab": "Classical studies",
    "Oldtidssprog": "Ancient languages",
    "Omsorgsarbejde": "Care work",
    "Omsorgsarbejde, videreuddannelse": "Care work, further education",
    "Oplevelses-design": "Experience design",
    "Optometri og synsvidenskab": "Optometry and vision science",
    "Optometrist": "Optometrist",
    "Parasitologi": "Parasitology",
    "Persisk": "Persian",
    "Person- og lastvognsmekaniker": "Car and truck mechanic",
    "Politi og forsvar uden nærmere angivelse": "Police and defence, not further specified",
    "Politologiske uddannelser i øvrigt": "Other political science programmes",
    "Polsk": "Polish",
    "Portugisisk og brasilliansk": "Portuguese and Brazilian",
    "Postoperatører": "Postal operators",
    "Pre International Baccalaureate": "Pre International Baccalaureate",
    "Produktion og udvikling, grundforløb": "Production and development, basic course",
    "Psykologi": "Psychology",
    "Psykomotorik og afspænding mv.": "Psychomotor therapy and relaxation etc.",
    "Pædagog": "Educator (pædagog)",
    "Pædagogik": "Pedagogy",
    "Pædagogisk arbejde med børn og unge i øvrigt": "Other pedagogical work with children and young people",
    "Pædagogisk assistentuddannelse": "Pedagogical assistant programme",
    "Pædagogiske uddannelser uden nærmere angivelse": "Pedagogical programmes, not further specified",
    "Radiograf": "Radiographer",
    "Redderuddannelser": "Rescue worker programmes",
    "Religion og religionsvidenskab": "Religion and religious studies",
    "Retorik": "Rhetoric",
    "Rumænsk": "Romanian",
    "Russisk": "Russian",
    "Samfundsfaglig, Økonomisk-Merkantil uden nærmere angivelse": "Social science, economic-mercantile, not further specified",
    "Samfundsvidenskab uden nærmere angivelse": "Social sciences, not further specified",
    "Sangskrivning": "Songwriting",
    "Sceneinstruktør": "Stage director",
    "Scenekunst": "Performing arts",
    "Scenograf": "Scenographer",
    "Seniorofficerer": "Senior officers",
    "Serbokroatisk": "Serbo-Croatian",
    "Service, grundforløb": "Service, basic course",
    "Serviceassistentuddannelse": "Service assistant programme",
    "Serviceøkonom mv.": "Service economist etc.",
    "Skibsførere": "Ship masters",
    "Skibsofficerer uden nærmere angivelse": "Ship officers, not further specified",
    "Skibstekniske uddannelser": "Marine engineering programmes",
    "Skomager og ortopædiskomager": "Shoemaker and orthopaedic shoemaker",
    "Skorstensfejer og kedelanlægstekniker": "Chimney sweep and boiler plant technician",
    "Skovbrug, efteruddannelse": "Forestry, continuing education",
    "Skovbrugsvidenskab": "Forestry science",
    "Skuespiller": "Actor",
    "Slavisk, østeuropa og balkan uden nærmere angivelse": "Slavic, Eastern Europe and Balkans, not further specified",
    "Snedker mv.": "Joiner etc.",
    "Social- og sundhedsuddannelse uden nærmere angivelse": "Social and health care programme, not further specified",
    "Socialrådgivning og -formidling mv.": "Social counselling and dissemination etc.",
    "Socialt entrepreneurskab mv.": "Social entrepreneurship etc.",
    "Sociologi": "Sociology",
    "Sociologiske uddannelser i øvrigt": "Other sociological programmes",
    "Softwareudvikling": "Software development",
    "Spansk": "Spanish",
    "Sprog - international politik og historie": "Language - international politics and history",
    "Sprog og virksomhedskommunikation": "Language and corporate communication",
    "Sproglig gymnasium 1.g.": "Language-stream gymnasium, year 1",
    "Sproglig gymnasium 2.g.": "Language-stream gymnasium, year 2",
    "Sproglig gymnasium 3.g.": "Language-stream gymnasium, year 3",
    "Sproglig studenterkursus 1. år": "Language-stream studenterkursus, 1st year",
    "Sproglig studenterkursus 2. år": "Language-stream studenterkursus, 2nd year",
    "Sprogofficer": "Language officer",
    "Statistik": "Statistics",
    "Statskundskab": "Political science",
    "Strøm og elektronik uden nærmere angivelse": "Electricity and electronics, not further specified",
    "Strøm, styring og it, grundforløb": "Electricity, control systems and IT, basic course",
    "Studenterkursus uden linieopdeling": "Studenterkursus without streaming",
    "Studenterkursus uden linieopdeling 1. år": "Studenterkursus without streaming, 1st year",
    "Studenterkursus uden linieopdeling 2. år": "Studenterkursus without streaming, 2nd year",
    "Sundhed og omsorg": "Health and care",
    "Sundhed, omsorg og pædagogik i øvrigt": "Other health, care and pedagogy",
    "Sundhed, omsorg og pædagogik uden nærmere angivelse": "Health, care and pedagogy, not further specified",
    "Sundhed, omsorg og pædagogik, grundforløb": "Health, care and pedagogy, basic course",
    "Sundheds- og omsorgsteknologi": "Health and care technology",
    "Sundhedsfaglig uddannelse uden nærmere angivelse": "Health programme, not further specified",
    "Sundhedsfaglige uddannelser i øvrigt": "Other health programmes",
    "Sundhedsteknologi": "Health technology",
    "Sundhedsvidenskab i øvrigt": "Other health science",
    "Sundhedsvidenskab uden nærmere angivelse": "Health science, not further specified",
    "Sygepleje og sundhedspleje": "Nursing and health visiting",
    "Sygeplejevidenskab": "Nursing science",
    "Særlige ungdomsuddannelser": "Special youth education programmes",
    "Tandplejer og klinisk tandteknik": "Dental hygienist and clinical dental technology",
    "Teater-, udstillings- og eventteknik": "Theatre, exhibition and event technology",
    "Teaterteknik": "Theatre technology",
    "Tegnsprogstolk": "Sign language interpreter",
    "Teknik og forretningsudvikling": "Technology and business development",
    "Teknik- og industriuddannelser i øvrigt": "Other technical and industrial programmes",
    "Teknik-naturvidenskab, kombineret": "Technology-natural science, combined",
    "Teknisk i øvrigt": "Other technical",
    "Teknisk offshore": "Technical offshore",
    "Teknisk uden nærmere angivelse": "Technical, not further specified",
    "Teknisk videnskab i øvrigt": "Other engineering science",
    "Teknisk videnskab uden nærmere angivelse": "Engineering science, not further specified",
    "Teknisk videnskabelige it-uddannelser": "Engineering science IT programmes",
    "Teknisk, beredskab og risikostyring": "Technical, emergency preparedness and risk management",
    "Teknisk, produktion og produktudvikling i øvrigt": "Other technical, production and product development",
    "Teknisk, tekstil- og beklædning": "Technical, textiles and clothing",
    "Teknologi og forretningsudvikling": "Technology and business development",
    "Teknologi og kommunikation, grundforløb": "Technology and communication, basic course",
    "Teknologi, produktion og produktudvikling": "Technology, production and product development",
    "Teknologi, råstofudvinding": "Technology, raw materials extraction",
    "Teknologi, transportteknik og logistik": "Technology, transport engineering and logistics",
    "Teknologi-naturvidenskab, kombineret": "Technology-natural science, combined",
    "Tekstil- og beklædningshåndværk": "Textile and clothing crafts",
    "Tele-, data- og it-teknologi mv.": "Tele, data and IT technology etc.",
    "Tele-, data- og it-teknologi mv., teknisk": "Tele, data and IT technology etc., technical",
    "Tele-, data- og it-teknologi mv., teknisk videnskab": "Tele, data and IT technology etc., engineering science",
    "Teologi": "Theology",
    "Tf-kurser mv.": "TF courses etc.",
    "Thai": "Thai",
    "Tibetologi": "Tibetology",
    "Tjekkisk": "Czech",
    "Togklargøringsuddannelser": "Train preparation programmes",
    "Tolk i fremmedsprog": "Interpreter in foreign languages",
    "Tonemester, film og tv": "Sound engineer (tonemester), film and TV",
    "Tonemester, musik": "Sound engineer (tonemester), music",
    "Transport og logistik uden nærmere angivelse": "Transport and logistics, not further specified",
    "Transport og logistik, grundforløb": "Transport and logistics, basic course",
    "Transport- og logistik i øvrigt": "Other transport and logistics",
    "Transport- og logistikøkonom mv.": "Transport and logistics economist etc.",
    "Transportteknisk": "Transport engineering",
    "Tv studieproducer og tv-tilrettelægger": "TV studio producer and TV production planner",
    "Tyrkisk": "Turkish",
    "Tysk": "German",
    "Tømrer mv.": "Carpenter etc.",
    "Underviser i dansk som andetsprog": "Teacher of Danish as a second language",
    "Ungarsk": "Hungarian",
    "Velfærdsteknologi": "Welfare technology",
    "Veterinærmedicin": "Veterinary medicine",
    "Videnskabshistorie": "History of science",
    "Videregående uddannelser uden nærmere angivelse": "Higher education, not further specified",
    "Vindenergi": "Wind energy",
    "Vindmølleoperatør": "Wind turbine operator",
    "Vognmaler": "Vehicle painter",
    "Vvs-teknik": "Plumbing (VVS) technology",
    "Værktøjsuddannelser": "Tooling programmes",
    "Web-integrator": "Web integrator",
    "Æstetik og kultur": "Aesthetics and culture",
    "Økonomi": "Economics",
    "Østasiatiske sprog uden nærmere angivelse": "East Asian languages, not further specified",
    "Øvrige erhvervsfaglige uddannelser": "Other vocational programmes",
}


def split_suffix(title):
    parts = [p.strip() for p in title.split(",")]
    suffix = []
    while len(parts) > 1 and parts[-1] in SUFFIXES:
        suffix.insert(0, parts.pop())
    return ", ".join(parts), suffix


def main():
    # official 8-digit titles (the two crosswalks agree on all overlaps)
    ref = {}
    for p in ("crosswalks/edu/df_UDD_DISCED.parquet",
              "crosswalks/edu/df_AUDD_DISCED.parquet"):
        df = pd.read_parquet(p)
        for k, t in zip(df["code4"].astype(str), df["title4"]):
            ref.setdefault(k, t)

    with open(MASTER, newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    # reusable existing translations (non-compound rows), markers stripped
    da2en = {}
    marker = re.compile(r"\s*\[(current|completed) education\]\s*$")
    for r in rows:
        da, en = r["description_da"].strip(), r["description_en"].strip()
        if da and en and "(compound:" not in da:
            da2en.setdefault(da, marker.sub("", en))

    def translate(title):
        if title in da2en:
            return da2en[title], "reused-master"
        base, suffix = split_suffix(title)
        if base not in BASE_EN:
            sys.exit(f"FATAL: no translation for base {base!r} (title {title!r})")
        return ", ".join([BASE_EN[base]] + suffix), "fable-5"

    n = 0
    worklist = []
    for r in rows:
        if r["category"] != "EDU_disced":
            continue
        title = ref.get(r["value"])
        if title is None:
            sys.exit(f"FATAL: {r['code']} not in crosswalk")
        en, how = translate(title)
        worklist.append((r["value"], r["description_da"], title, en, how))
        r["description_da"] = title
        r["description_en"] = en
        r["description_short"] = en
        r["source"] = "crosswalk_edu_disced"
        r["description_en_source"] = "fable-5-edu"
        n += 1

    with open(MASTER, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)

    with open(WORKLIST, "w", newline="") as f:
        w = csv.writer(f, delimiter="\t", lineterminator="\n")
        w.writerow(["value", "old_description_da", "new_description_da",
                    "description_en", "translation_source"])
        w.writerows(worklist)

    reused = sum(1 for x in worklist if x[4] == "reused-master")
    print(f"updated {n} EDU_disced rows "
          f"({reused} en reused from MASTER, {n - reused} translated)")
    print(f"worklist: {WORKLIST}")


if __name__ == "__main__":
    main()
