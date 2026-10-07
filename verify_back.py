import argparse
import os

from parser import parse_cnf_csv
from backsat import back_sat, check_assignment
from paths import find, DATA


def brute_max(n, clauses):
    """Exhaustive: returns (is_sat, max number of satisfied clauses)."""
    best = 0
    for i in range(2 ** n):
        a = {v: bool((i >> (v - 1)) & 1) for v in range(1, n + 1)}
        c = check_assignment(clauses, a)
        if c > best:
            best = c
    return best == len(clauses), best


def check1():
    print("=" * 60)
    print("CHECK 1: hand examples (step-by-step trace)")
    print("=" * 60)
    cases = [
        ("(x1 v x2) & (~x1 v x2) & (~x2 v x3)", 3, [[1, 2], [-1, 2], [-2, 3]], 'SAT'),
        ("(x1 v x2) & (x1 v ~x2) & (~x1 v x2) & (~x1 v ~x2)", 2,
         [[1, 2], [1, -2], [-1, 2], [-1, -2]], 'UNSAT'),
        ("(x1) & (~x1 v x2) & (~x2 v ~x3) & (x3 v x1)", 3, [[1], [-1, 2], [-2, -3], [3, 1]], 'SAT'),
    ]
    ok = True
    for text, n, cl, expected in cases:
        print(f"\nwff: {text}   (expected {expected})")
        status, a, count, st = back_sat(n, cl, trace=True)
        good = status == expected and (status == 'UNSAT' or check_assignment(cl, a) == len(cl))
        ok &= good
        print(f"-> {status}, nodes={st.nodes}, shallow={st.shallow}, deep={st.deep}   "
              f"{'PASS' if good else 'FAIL'}")
    return ok


def check2(maxn):
    print("\n" + "=" * 60)
    print(f"CHECK 2: BACK-SAT vs brute force on all wffs with n <= {maxn}")
    print("=" * 60)
    ok = True
    for name in ('kSAT.cnf.csv', 'kSATu.cnf.csv'):
        fn = find(name, required=False)
        if not fn:
            print(f"{name}: not found, skipped"); continue
        wffs = [w for w in parse_cnf_csv(fn) if w['n_vars'] <= maxn]
        disagree = label_bad = unverified = 0
        unsat = exact = 0
        worst_gap = 0
        for w in wffs:
            status, a, count, st = back_sat(w['n_vars'], w['clauses'])
            is_sat, true_max = brute_max(w['n_vars'], w['clauses'])
            if (status == 'SAT') != is_sat:
                disagree += 1
                print(f"  DISAGREE problem {w['problem_id']}: back={status} brute={'SAT' if is_sat else 'UNSAT'}")
            if status == 'SAT' and check_assignment(w['clauses'], a) != w['n_clauses']:
                unverified += 1
            if w['label'] in ('S', 'U') and (status == 'SAT') != (w['label'] == 'S'):
                label_bad += 1
            if status == 'UNSAT':
                unsat += 1
                exact += (count == true_max)
                worst_gap = max(worst_gap, true_max - count)
        ok &= disagree == 0 and label_bad == 0 and unverified == 0
        print(f"{name}: {len(wffs)} wffs checked | disagreements with brute force: {disagree} | "
              f"label mismatches: {label_bad} | bad SAT assignments: {unverified}")
        if unsat:
            print(f"   UNSAT wffs: {unsat}; BACK-SAT best clause count == true maximum on {exact} "
                  f"({100 * exact / unsat:.0f}%), largest shortfall {worst_gap} clause(s)")
    return ok


def check3():
    print("\n" + "=" * 60)
    print("CHECK 3: worst-case family, nodes must be 2^(n+1) - 2")
    print("=" * 60)
    ok = True
    for n in range(4, 17, 2):
        cl = [[n], [-n]] + [[i, -i] for i in range(1, n)]
        status, _, _, st = back_sat(n, cl)
        good = status == 'UNSAT' and st.nodes == 2 ** (n + 1) - 2
        ok &= good
        print(f"n={n:2d}: nodes={st.nodes:7d}  expected {2 ** (n + 1) - 2:7d}  {'PASS' if good else 'FAIL'}")
    return ok


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--maxn', type=int, default=14)
    args = ap.parse_args()
    r1, r2, r3 = check1(), check2(args.maxn), check3()
    print("\n" + "=" * 60)
    print(f"Check 1 {'PASS' if r1 else 'FAIL'} | Check 2 {'PASS' if r2 else 'FAIL'} | "
          f"Check 3 {'PASS' if r3 else 'FAIL'}")
    print("=" * 60)
