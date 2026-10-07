import csv
import os
import sys
from collections import defaultdict

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from paths import find, RESULTS as RES, CHARTS as CH
GREEN, RED, GRAY = '#2e9b3e', '#d0342c', '#555555'
BRUTE_C, BACK_C = '#7a5195', '#1f77b4'
TIMEOUT = 15.0

plt.rcParams.update({'axes.grid': True, 'grid.alpha': 0.25, 'grid.linewidth': 0.6,
                     'axes.spines.top': False, 'axes.spines.right': False,
                     'figure.dpi': 110, 'font.size': 10})


def nice_logx(ax, ns):
    from matplotlib.ticker import FixedLocator, NullLocator, FuncFormatter
    ticks = sorted(set(int(n) for n in ns))
    if len(ticks) > 12:
        ticks = ticks[::2]
    ax.xaxis.set_major_locator(FixedLocator(ticks))
    ax.xaxis.set_minor_locator(NullLocator())
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f'{int(v)}'))


def load(fn):
    if not os.path.exists(fn):
        return None
    with open(fn, newline='') as f:
        return list(csv.DictReader(f))


def done(rows):
    return [r for r in rows if r['status'] in ('SAT', 'UNSAT')]


def envelope(rows, key=lambda r: float(r['elapsed_sec']), with_timeouts=False):
    """worst (max) and median value at each n, over completed problems
    (with_timeouts=True counts TIMEOUT runs at the timeout value: a lower bound)"""
    by = defaultdict(list)
    for r in (rows if with_timeouts else done(rows)):
        by[int(r['n_vars'])].append(key(r))
    ns = sorted(by)
    return np.array(ns), np.array([max(by[n]) for n in ns]), np.array([np.median(by[n]) for n in ns])


def fits(ns, ts):
    """power law  t = a*n^p  (log-log slope)  and  exponential  t = a*b^n"""
    m = ts > 0
    x, y = ns[m], ts[m]
    p, lp = np.polyfit(np.log(x), np.log(y), 1)
    c, lc = np.polyfit(x, np.log(y), 1)
    return (np.exp(lp), p), (np.exp(lc), np.exp(c))


def scatter_sat_unsat(ax, rows, yfun):
    for st, col, lab in (('SAT', GREEN, 'satisfiable'), ('UNSAT', RED, 'unsatisfiable')):
        pts = [(int(r['n_vars']), yfun(r)) for r in rows if r['status'] == st]
        if pts:
            x, y = zip(*pts)
            ax.scatter(x, y, s=16, c=col, alpha=0.7, edgecolors='white', linewidths=0.4, label=lab)

def growth(rows, stat):
    """growth factor b in t = a*b^n, using only n where no run timed out"""
    by = defaultdict(list)
    for r in rows:
        by[int(r['n_vars'])].append(None if r['status'] == 'TIMEOUT' else float(r['elapsed_sec']))
    ns = [n for n in sorted(by) if None not in by[n]]
    ys = [stat(by[n]) for n in ns]
    return float(np.exp(np.polyfit(ns, np.log(ys), 1)[0]))

def plot_time(rows, ds, fitlog):
    ns, worst, _ = envelope(rows)
    (pa, pp), (ea, eb) = fits(ns, worst)
    fitlog.append(f"[BACK-SAT {ds}] worst-case fit: power t = {pa:.3g} * n^{pp:.2f}   |   "
                  f"exponential t = {ea:.3g} * {eb:.3f}^n")
    fig, ax = plt.subplots(figsize=(6.4, 4.4))
    scatter_sat_unsat(ax, done(rows), lambda r: float(r['elapsed_sec']))
    xx = np.linspace(ns.min(), ns.max(), 100)
    ax.plot(xx, ea * eb ** xx, color=GRAY, lw=1.6, ls='--',
            label=f'worst-case fit ≈ {ea:.2g}·{eb:.2f}$^n$  (log-log slope {pp:.1f})')
    to = [int(r['n_vars']) for r in rows if r['status'] == 'TIMEOUT']
    if to:
        ax.scatter(to, [TIMEOUT] * len(to), marker='x', c='black', s=24, label=f'timeout ({TIMEOUT:g}s)')
    ax.set(xscale='log', yscale='log', xlabel='number of identifiers (n)', ylabel='execution time (s)',
           title=f'BACK-SAT: execution time vs n ({ds})')
    nice_logx(ax, ns)
    ax.legend(fontsize=8, frameon=False)
    fig.tight_layout(); fig.savefig(f'{CH}/back_time_vs_n_{ds}.png', dpi=150); plt.close(fig)


def plot_per_literal(rows, ds):
    fig, ax = plt.subplots(figsize=(6.4, 4.4))
    scatter_sat_unsat(ax, done(rows), lambda r: float(r['elapsed_sec']) / int(r['n_literals']))
    ax.set(xscale='log', yscale='log', xlabel='number of identifiers (n)',
           ylabel='execution time / number of literals (s)',
           title=f'BACK-SAT: time per literal vs n ({ds})')
    nice_logx(ax, [int(r['n_vars']) for r in rows])
    ax.legend(fontsize=8, frameon=False)
    fig.tight_layout(); fig.savefig(f'{CH}/back_time_per_literal_{ds}.png', dpi=150); plt.close(fig)


def plot_compare(back, brute, ds, fitlog):
    fig, ax = plt.subplots(figsize=(6.4, 4.4))
    for rows, col, name in ((brute, BRUTE_C, 'BRUTE-SAT (1A)'), (back, BACK_C, 'BACK-SAT (1B)')):
        key = lambda r: TIMEOUT if r['status'] == 'TIMEOUT' else float(r['elapsed_sec'])
        ns, worst, med = envelope(rows, key=key, with_timeouts=True)
        ax.plot(ns, worst, '-o', color=col, lw=2, ms=5, label=f'{name} worst')
        ax.plot(ns, med, '--', color=col, lw=1.4, label=f'{name} median')
        to = sorted({int(r['n_vars']) for r in rows if r['status'] == 'TIMEOUT'})
        if to:
            ax.scatter(to, [TIMEOUT] * len(to), marker='x', s=60, c=col, zorder=5,
                       label=f'{name}: some runs timed out (counted as {TIMEOUT:g}s)')
    ax.axhline(TIMEOUT, color='black', lw=0.8, ls=':')
    ax.text(ax.get_xlim()[0], TIMEOUT * 1.2, f' {TIMEOUT:g}s timeout', fontsize=7.5, color=GRAY)
    ax.set(yscale='log', xlabel='number of identifiers (n)', ylabel='execution time (s)',
           title=f'BRUTE-SAT vs BACK-SAT ({ds}), semi-log\n(timeouts counted as {TIMEOUT:g}s, so BRUTE curves are lower bounds)')
    ax.legend(fontsize=8, frameon=False)
    fig.tight_layout(); fig.savefig(f'{CH}/compare_time_{ds}.png', dpi=150); plt.close(fig)

    ns, worst, _ = envelope(brute)
    (pa, pp), (ea, eb) = fits(ns, worst)
    fitlog.append(f"[BRUTE-SAT {ds}] worst-case fit (completed runs only): power n^{pp:.2f} | exponential {eb:.3f}^n")


def plot_nodes(rows, ds, fitlog):
    ns, worst, med = envelope(rows, key=lambda r: int(r['nodes']))
    (_, _), (ea, eb) = fits(ns, worst)
    (_, _), (ma, mb) = fits(ns, med)
    fitlog.append(f"[BACK-SAT {ds}] nodes: worst ≈ {ea:.3g}*{eb:.3f}^n, median ≈ {ma:.3g}*{mb:.3f}^n "
                  f"(full tree = 2^(n+1)-2 ; brute force = up to 2^n assignments)")
    fig, ax = plt.subplots(figsize=(6.4, 4.4))
    scatter_sat_unsat(ax, done(rows), lambda r: int(r['nodes']))
    xx = np.linspace(ns.min(), ns.max(), 100)
    ax.plot(xx, 2.0 ** xx, color=BRUTE_C, lw=1.6, label='$2^n$ (assignments brute force may try)')
    ax.plot(xx, ea * eb ** xx, color=GRAY, lw=1.6, ls='--', label=f'BACK worst ≈ {ea:.2g}·{eb:.2f}$^n$')
    ax.set(yscale='log', xlabel='number of identifiers (n)', ylabel='nodes (assignments tried)',
           title=f'BACK-SAT search-tree size vs n ({ds})')
    ax.legend(fontsize=8, frameon=False)
    fig.tight_layout(); fig.savefig(f'{CH}/nodes_vs_n_{ds}.png', dpi=150); plt.close(fig)


def plot_speedup(back, brute, ds, fitlog):
    b = {r['problem_id']: r for r in back}
    fig, ax = plt.subplots(figsize=(6.4, 4.4))
    allsp = []
    for st, col, lab in (('SAT', GREEN, 'satisfiable'), ('UNSAT', RED, 'unsatisfiable')):
        pts = []
        for r in brute:
            k = b.get(r['problem_id'])
            if k and r['status'] == st and k['status'] == st and float(k['elapsed_sec']) > 0:
                pts.append((int(r['n_vars']), float(r['elapsed_sec']) / float(k['elapsed_sec'])))
        if pts:
            allsp += pts
            x, y = zip(*pts)
            ax.scatter(x, y, s=16, c=col, alpha=0.7, edgecolors='white', linewidths=0.4, label=lab)
    ax.axhline(1, color='black', lw=0.8)
    ax.set(yscale='log', xlabel='number of identifiers (n)', ylabel='BRUTE time / BACK time',
           title=f'Speedup of BACK-SAT over BRUTE-SAT ({ds}, both finished)')
    ax.legend(fontsize=8, frameon=False)
    fig.tight_layout(); fig.savefig(f'{CH}/speedup_{ds}.png', dpi=150); plt.close(fig)
    if allsp:
        sp = np.array([s for _, s in allsp])
        fitlog.append(f"[{ds}] speedup over {len(sp)} problems both finished: median {np.median(sp):.1f}x, "
                      f"min {sp.min():.2f}x, max {sp.max():.0f}x; slower than brute on {int((sp < 1).sum())}")
        solved = sum(1 for r in brute if r['status'] == 'TIMEOUT'
                     and b.get(r['problem_id'], {}).get('status') in ('SAT', 'UNSAT'))
        fitlog.append(f"[{ds}] problems BRUTE timed out on that BACK-SAT solved: {solved}")


if __name__ == '__main__':
    os.makedirs(CH, exist_ok=True)
    fitlog = []
    for ds in ('kSAT', 'kSATu'):
        back = load(os.path.join(RES, f'back_{ds}_results.csv'))
        if back is None:
            print(f'skip {ds}: no BACK-SAT results'); continue
        bfile = find(f'{ds}_results.csv', required=False)   # Project 1A results
        brute = load(bfile) if bfile else None
        print(f'{ds}: BACK results from {RES}; BRUTE (1A) results from {bfile}')
        plot_time(back, ds, fitlog)
        plot_per_literal(back, ds)
        plot_nodes(back, ds, fitlog)
        if brute:
            for name, rows in (('BRUTE', brute), ('BACK', back)):
                fitlog.append(f"[{name} {ds}] time growth per identifier: "
                              f"worst {growth(rows, max):.2f}, median {growth(rows, np.median):.2f}")
            plot_compare(back, brute, ds, fitlog)
            plot_speedup(back, brute, ds, fitlog)
        else:
            print(f'note: {ds}_results.csv (Project 1A) not found; comparison charts skipped')
    with open(os.path.join(RES, 'fits.txt'), 'w') as f:
        f.write('\n'.join(fitlog) + '\n')
    print('\n'.join(fitlog))
