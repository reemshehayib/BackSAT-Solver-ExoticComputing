import csv

def parse_cnf_csv(filename):
    with open(filename, newline='') as f:
        sample = f.read(2048)
        f.seek(0)
        try:
            delim = csv.Sniffer().sniff(sample, delimiters=',\t').delimiter
        except csv.Error:
            delim = '\t' if '\t' in sample else ','
        rows = list(csv.reader(f, delimiter=delim))

    rows = [[cell.strip() for cell in row if cell.strip() != ''] for row in rows]
    rows = [row for row in rows if row]

    wffs = []
    i = 0
    while i < len(rows):
        row = rows[i]
        assert row[0] == 'c', f"Expected 'c' row at line {i}, got {row}"
        problem_id = int(row[1])
        max_lits = int(row[2])
        label = row[3] if len(row) > 3 else None
        i += 1

        prow = rows[i]
        assert prow[0] == 'p' and prow[1] == 'cnf'
        n_vars = int(prow[2])
        n_clauses = int(prow[3])
        i += 1

        clauses = []
        for _ in range(n_clauses):
            crow = rows[i]
            lits = [int(x) for x in crow]
            assert lits[-1] == 0, f"Clause did not end in 0: {crow}"
            clauses.append(lits[:-1])  
            i += 1

        wffs.append({
            'problem_id': problem_id,
            'max_lits': max_lits,
            'label': label,
            'n_vars': n_vars,
            'n_clauses': n_clauses,
            'clauses': clauses,
        })

    return wffs