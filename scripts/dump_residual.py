import csv, sys, os
wl=list(csv.DictReader(open('scripts/hea_speciale_worklist.csv')))
auto={}
for l in open('scripts/hea_speciale_auto.tsv'):
    if l.startswith('#') or not l.strip(): continue
    p=l.rstrip('\n').split('\t')
    if p[0].isdigit(): auto[int(p[0])]=p
done=set()
if os.path.exists('scripts/hea_speciale_translations.tsv'):
    for l in open('scripts/hea_speciale_translations.tsv'):
        p=l.split('\t')
        if p and p[0].isdigit(): done.add(int(p[0]))
resid=[i for i in range(len(wl)) if i in auto and len(auto[i])>=5 and auto[i][4]=='Y' and i not in done]
start=int(sys.argv[1]) if len(sys.argv)>1 else 0
count=int(sys.argv[2]) if len(sys.argv)>2 else 220
print(f"# residual_total={len(resid)} (excl already-done) showing [{start}:{start+count}]")
for i in resid[start:start+count]:
    # original abbreviated DA from worklist, plus expanded da_full from auto
    print(f"{i}\t{wl[i]['description_da']}\t||full: {auto[i][1]}")
