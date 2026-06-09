import csv, sys, os
LAB_SPECS={'44','45','46','48','11'}  # KPLL, Medical Lab, Regional labs, SSI, Clinical chemistry
wl=list(csv.DictReader(open('scripts/worklists/hea_speciale_worklist.csv')))
auto={}
for l in open('scripts/worklists/hea_speciale_auto.tsv'):
    if l.startswith('#') or not l.strip(): continue
    p=l.rstrip('\n').split('\t')
    if p[0].isdigit(): auto[int(p[0])]=p
done=set()
for l in open('scripts/worklists/hea_speciale_translations.tsv'):
    p=l.split('\t')
    if p and p[0].isdigit(): done.add(int(p[0]))
resid=[i for i in range(len(wl)) if i in auto and len(auto[i])>=5 and auto[i][4]=='Y'
       and i not in done and wl[i]['specialty_code'] not in LAB_SPECS]
start=int(sys.argv[1]) if len(sys.argv)>1 else 0
count=int(sys.argv[2]) if len(sys.argv)>2 else 200
print(f"# clinical_residual_total={len(resid)} showing [{start}:{start+count}]")
for i in resid[start:start+count]:
    print(f"{i}\t{wl[i]['description_da']}\t||{auto[i][1]}")
