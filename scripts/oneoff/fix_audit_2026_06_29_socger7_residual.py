#!/usr/bin/env python3
"""
Audit fixes 2026-06-29 PART 5: SOC_ger7 residual garble.
SOC_ger7's English was produced by a broken word-substitution pipeline that left
many rows half-Danish (e.g. "Burglary i forretning", "Frakendelsestid, driving i").
The audit sampled only part of the 938-row category; this pass fixes the remaining
101 garbled rows. Each English string is a faithful translation of the GIVEN Danish
(description_da, unchanged). description_en only.
"""
import csv, io

EN = {
 'SOC_ger7_2610094':'Disqualification period, driving during',
 'SOC_ger7_2610043':'Moped riding, special rules for',
 'SOC_ger7_3810405':'Fire safety legislation / Emergency Preparedness Act',
 'SOC_ger7_2210068':'Traffic accident. Moped rider with high BAC, with personal injury',
 'SOC_ger7_1210505':'Violence etc. against someone in public service etc. (first appears in 1980)',
 'SOC_ger7_1316540':'Burglary in shop, otherwise',
 'SOC_ger7_3810507':'Public Order Regulation, securing public order etc.',
 'SOC_ger7_2220020':'Alcohol, motor-vehicle driver, drink-driving',
 'SOC_ger7_2610092':'Disqualification period, driving during (motor vehicle, except small moped)',
 'SOC_ger7_2610053':'Driving without a licence for the relevant category',
 'SOC_ger7_2610007':'Traffic accident. Did not fulfil one’s obligations',
 'SOC_ger7_2610086':'Overloading, including regulation on weight and axle pressure',
 'SOC_ger7_2610117':'Emergency lane, driving in (penalty points)',
 'SOC_ger7_2610178':'Safety equipment, under 15 years (penalty points) (Not active in 2011)',
 'SOC_ger7_1316215':'Burglary in school',
 'SOC_ger7_1316335':'Burglary in private office, otherwise',
 'SOC_ger7_1324505':'Burglary in holiday house',
 'SOC_ger7_1316625':'Burglary in business, otherwise',
 'SOC_ger7_2610050':'Driving licence etc. not carried (motor vehicle/large moped)',
 'SOC_ger7_2610068':'Duty to provide information etc., not fulfilled',
 'SOC_ger7_1324710':'Burglary in cellar/attic/storage room',
 'SOC_ger7_3830715':'Fisheries legislation',
 'SOC_ger7_2610116':'Solid lines, crossing in connection with overtaking (penalty points)',
 'SOC_ger7_1316235':'Burglary in public office/building, otherwise',
 'SOC_ger7_1320505':'Burglary in detached house etc.',
 'SOC_ger7_1460305':'Negligent manslaughter in connection with a traffic accident',
 'SOC_ger7_3850505':'Electricity legislation',
 'SOC_ger7_3840575':'Other laws regarding company and business legislation',
 'SOC_ger7_2610168':'Transport of more children than seats (penalty points) (Not active in 2011)',
 'SOC_ger7_1316515':'Burglary in grocer/supermarket/dairy',
 'SOC_ger7_1316210':'Burglary in kindergarten/nursery/after-school centre',
 'SOC_ger7_1336568':'Theft in open yard',
 'SOC_ger7_2210044':'Traffic accident. Motor-vehicle driver, drink-driving without personal injury',
 'SOC_ger7_1316505':'Burglary in clothing/leather/footwear shop',
 'SOC_ger7_1316615':'Burglary in workshop',
 'SOC_ger7_1320705':'Burglary in apartment',
 'SOC_ger7_3815530':'Food legislation',
 'SOC_ger7_1292520':'Threats, violence etc. against witnesses and their next of kin (first appears 1992)',
 'SOC_ger7_1316320':'Burglary in petrol station/car dealer',
 'SOC_ger7_1316230':'Burglary in institution/nursing home',
 'SOC_ger7_2610098':'Violated other rules in the Road Traffic Act',
 'SOC_ger7_2210012':'Traffic accident. Motor-vehicle driver, drink-driving with personal injury',
 'SOC_ger7_3835307':'Posting of employees etc., Act on service providers',
 'SOC_ger7_1316525':'Burglary in watchmaker/jeweller',
 'SOC_ger7_1316705':'Burglary in pharmacy',
 'SOC_ger7_2610108':'Traffic island etc., passing to the left of (penalty points)',
 'SOC_ger7_1316520':'Burglary in radio/photo shop',
 'SOC_ger7_1324705':'Burglary in garage/outbuilding',
 'SOC_ger7_1316225':'Burglary in swimming pool/sports facility etc.',
 'SOC_ger7_1316530':'Burglary in cafeteria/restaurant',
 'SOC_ger7_2210052':'Traffic accident. Moped rider, under the influence of alcohol, without personal injury',
 'SOC_ger7_1460705':'Negligent significant bodily harm in connection with a traffic accident',
 'SOC_ger7_1316610':'Burglary in warehouse etc.',
 'SOC_ger7_1210504':'Obstructing the performance (of a police officer)',
 'SOC_ger7_3810509':'Public Order Regulation, securing public order (pornography display)',
 'SOC_ger7_1380904':'Robbery against a person in their own home',
 'SOC_ger7_1316545':'Burglary in weapons depot/factory/shop',
 'SOC_ger7_1320710':'Burglary in room',
 'SOC_ger7_1210508':'Violence against someone in public service',
 'SOC_ger7_1316620':'Burglary in timber merchant/builders’ merchant',
 'SOC_ger7_1316405':'Burglary in bank',
 'SOC_ger7_1316715':'Burglary in doctor’s surgery etc.',
 'SOC_ger7_1316325':'Burglary in private institution',
 'SOC_ger7_1410751':'Failure to comply with an order to disperse',
 'SOC_ger7_3810786':'Visitors in certain premises / violation of a prohibition against',
 'SOC_ger7_1316510':'Burglary in kiosk/tobacconist/wine shop',
 'SOC_ger7_1380911':'Particularly dangerous robbery against a person in their own home',
 'SOC_ger7_2210020':'Traffic accident. Moped rider under the influence of alcohol with personal injury',
 'SOC_ger7_2210076':'Traffic accident. Moped rider with high BAC without personal injury',
 'SOC_ger7_1316110':'Burglary in post office',
 'SOC_ger7_2610030':'Disqualification period, driving during (small moped)',
 'SOC_ger7_1336513':'Theft, trick theft in a residence',
 'SOC_ger7_2210072':'Traffic accident. Moped rider, drink-driving with personal injury',
 'SOC_ger7_1324720':'Burglary in work shed/site office etc.',
 'SOC_ger7_1316605':'Burglary in factory',
 'SOC_ger7_1210520':'Breach of the peace against a person in public service',
 'SOC_ger7_1336558':'Theft in train/ship/aircraft/bus',
 'SOC_ger7_1120506':'Rape by use of violence or threat of violence',
 'SOC_ger7_1316536':'Burglary in IT/computer shop',
 'SOC_ger7_1316710':'Burglary in hospital',
 'SOC_ger7_1210516':'Obstructing the exercise of public authority, aggravating circumstances',
 'SOC_ger7_2610170':'Crash helmet, 5-14 years without seat belt (penalty points) (Not active in 2011)',
 'SOC_ger7_2220045':'Moped rider, medication etc.',
 'SOC_ger7_2220040':'Alcohol, moped rider, drink-driving',
 'SOC_ger7_1292530':'Violence against witnesses and their next of kin',
 'SOC_ger7_1316205':'Burglary in library',
 'SOC_ger7_1460505':'Negligent bodily harm in connection with a traffic accident',
 'SOC_ger7_1410380':'Terrorism, financial support for',
 'SOC_ger7_1316315':'Burglary in campsite/youth hostel',
 'SOC_ger7_3835708':'Driving and rest time, driver, regulation on national provisions',
 'SOC_ger7_1316535':'Burglary in hotel/motel',
 'SOC_ger7_1286535':'Failure to help a person in an accident',
 'SOC_ger7_1316340':'Burglary in function/banquet premises',
 'SOC_ger7_1332305':'Theft from a machine in a laundromat etc.',
 'SOC_ger7_1324725':'Burglary in ice-cream/hot-dog stand',
 'SOC_ger7_1324510':'Burglary in allotment garden house',
 'SOC_ger7_1316504':'Burglary in sports shop',
 'SOC_ger7_1324305':'Burglary in ship/boat (permanently manned)',
 'SOC_ger7_1286515':'Abandoning (someone) in a helpless state',
 'SOC_ger7_1415570':'Negligence in public office',
 'SOC_ger7_2610024':'Driving licence for small moped, not carried or presented',
}

MASTER='MASTER_CATEGORY_MAPPINGS.csv'
with open(MASTER, newline='') as f:
    rows=list(csv.reader(f))
h=rows[0]; idx={c:i for i,c in enumerate(h)}
by={r[idx['code']]:r for r in rows[1:]}
n=0; missing=[]
for code,en in EN.items():
    r=by.get(code)
    if r is None: missing.append(code); continue
    if r[idx['description_en']]!=en:
        r[idx['description_en']]=en; n+=1
buf=io.StringIO(); w=csv.writer(buf,lineterminator='\n'); w.writerows(rows)
open(MASTER,'w').write(buf.getvalue())
print(f"SOC_ger7 residual en fixes: {n}; missing codes: {missing}")
