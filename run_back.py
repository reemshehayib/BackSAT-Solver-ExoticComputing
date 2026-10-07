import argparse
import csv
import os
import platform
import sys

from parser import parse_cnf_csv
from backsat import back_sat_with_timeout, check_assignment
from paths import find, RESULTS


def run_file(input_filename, output_filename, timeout_sec=15, show_assignment_upto=30, use_unit=False):
    wffs = parse_cnf_csv(input_filename)
    results = []

    for wff in wffs:
        status, assignment, count, elapsed, st = back_sat_with_timeout(
            wff['n_vars'], wff['clauses'], timeout_sec=timeout_sec, use_unit=use_unit)

        matched = None
        if wff['label'] in ('S', 'U') and status != 'TIMEOUT':
            expected = 'SAT' if wff['label'] == 'S' else 'UNSAT'
            matched = (status == expected)

        # independent check: a reported SAT assignment must satisfy every clause
        verified = None
        if status == 'SAT':
            verified = check_assignment(wff['clauses'], assignment) == wff['n_clauses']

        results.append({
            'problem_id': wff['problem_id'],
            'n_vars': wff['n_vars'],
            'n_clauses': wff['n_clauses'],
            'n_literals': sum(len(c) for c in wff['clauses']),
            'max_lits': wff['max_lits'],
            'label': wff['label'],
            'status': status,
            'satisfied_count': count,
            'elapsed_sec': elapsed,
            'matched_label': matched,
            'verified': verified,
            'nodes': st.nodes,
            'shallow_bt': st.shallow,
            'deep_bt': st.deep,
            'evals': st.evals,
            'max_depth': st.max_depth,
        })

        print(f"problem {wff['problem_id']}: n={wff['n_vars']} m={wff['n_clauses']} "
              f"-> {status} ({count}/{wff['n_clauses']}) in {elapsed:.4f}s "
              f"nodes={st.nodes} shallow={st.shallow} deep={st.deep} "
              f"[label={wff['label']}, matched={matched}]")
        if status == 'SAT' and wff['n_vars'] <= show_assignment_upto:
            print("  Assignment: " + ", ".join(
                f"x{v}={'T' if val else 'F'}" for v, val in sorted(assignment.items())))

    with open(output_filename, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)

    n_sat = sum(r['status'] == 'SAT' for r in results)
    n_unsat = sum(r['status'] == 'UNSAT' for r in results)
    n_to = sum(r['status'] == 'TIMEOUT' for r in results)
    n_match = sum(r['matched_label'] is True for r in results)
    n_mis = sum(r['matched_label'] is False for r in results)
    n_bad = sum(r['verified'] is False for r in results)
    has_labels = any(r['label'] in ('S', 'U') for r in results)

    print()
    print(f"SUMMARY (BACK-SAT): {input_filename}")
    print("-" * 44)
    print(f"Total problems:       {len(results)}")
    print(f"Satisfiable:          {n_sat}")
    print(f"Unsatisfiable:        {n_unsat}")
    print(f"Timed out ({timeout_sec:g}s):     {n_to}")
    if has_labels:
        print(f"Matched label:        {n_match}")
        print(f"Mismatched label:     {n_mis}")
    print(f"SAT assignments that failed verification: {n_bad}")
    print(f"Total search time:    {sum(r['elapsed_sec'] for r in results):.2f}s")
    print(f"Results written to:   {output_filename}")
    print("=" * 44)
    print()
    return results


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('files', nargs='*', default=['kSAT.cnf.csv', 'kSATu.cnf.csv'],
                    help='CNF/CSV files (found automatically in BackSAT/ or the parent exotic-SAT/ folders)')
    ap.add_argument('--timeout', type=float, default=15)
    ap.add_argument('--outdir', default=RESULTS)
    ap.add_argument('--unit', action='store_true', help='use the unit clause rule in Step 1')
    args = ap.parse_args()

    print(f"Machine: {platform.node()} | {platform.platform()} | "
          f"{platform.processor() or platform.machine()} | Python {sys.version.split()[0]}")
    os.makedirs(args.outdir, exist_ok=True)
    for name in args.files:
        fn = find(name)
        print(f"Input: {fn}")
        base = os.path.basename(fn).replace('_cnf.csv', '').replace('.cnf.csv', '').replace('.csv', '')
        run_file(fn, os.path.join(args.outdir, f'back_{base}_results.csv'), args.timeout, use_unit=args.unit)