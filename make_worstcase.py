import csv, os
from paths import DATA
os.makedirs(DATA, exist_ok=True)
OUT = os.path.join(DATA, 'worstcase_cnf.csv')
with open(OUT, 'w', newline='') as f:
    w = csv.writer(f, delimiter='\t', lineterminator='\n')   # same layout as the course files
    for pid, n in enumerate(range(4, 21, 2), 1):
        clauses = [[n], [-n]] + [[i, -i] for i in range(1, n)]
        # pad every row to 7 cells like the course files, so csv.Sniffer can detect the tab
        pad = lambda row: row + [''] * (7 - len(row))
        w.writerow(pad(['c', pid, 2, 'U']))
        w.writerow(pad(['p', 'cnf', n, len(clauses)]))
        for c in clauses:
            w.writerow(pad(c + [0]))
print('wrote', OUT)