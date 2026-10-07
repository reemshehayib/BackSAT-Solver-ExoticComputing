import signal
import time

TRUE, FALSE, UNDET = 1, 0, 2


class Stats:
    def __init__(self):
        self.nodes = 0
        self.shallow = 0
        self.deep = 0
        self.evals = 0
        self.max_depth = 0
        self.best_count = 0
        self.best_assignment = None


def evaluate(clauses, assign):
    """Evaluate every clause under a partial assignment.
    Returns (n_true, n_false) -- number of TRUE clauses and FALSE clauses.
    assign[v] is True / False / None for v = 1..n."""
    n_true = 0
    n_false = 0
    for clause in clauses:
        status = FALSE
        for lit in clause:
            val = assign[lit if lit > 0 else -lit]
            if val is None:
                status = UNDET
            elif val == (lit > 0):
                status = TRUE
                break
        if status == TRUE:
            n_true += 1
        elif status == FALSE:
            n_false += 1
    return n_true, n_false


def pick_unassigned(assign, n_vars):
    """Step 1 identifier choice: lowest-numbered unassigned identifier."""
    for v in range(1, n_vars + 1):
        if assign[v] is None:
            return v
    return None


def pick_unit(clauses, assign):
    """Unit clause rule: find a clause with no true literal and exactly one
    unassigned identifier. Returns (identifier, value that makes it true) or None."""
    for clause in clauses:
        unassigned = None
        count = 0
        satisfied = False
        for lit in clause:
            val = assign[abs(lit)]
            if val is None:
                if unassigned is None or lit != unassigned:
                    count += 1
                unassigned = lit
            elif val == (lit > 0):
                satisfied = True
                break
        if not satisfied and count == 1:
            return abs(unassigned), unassigned > 0
    return None


def _as_full_assignment(assign, n_vars):
    """Unassigned identifiers are 'don't care'; report them as False."""
    return {v: bool(assign[v]) for v in range(1, n_vars + 1)}


def _fmt(assign, n_vars):
    return ' '.join(f"x{v}={'T' if assign[v] else 'F'}" if assign[v] is not None else f"x{v}=-"
                    for v in range(1, n_vars + 1))


def back_sat(n_vars, clauses, stats=None, trace=False, use_unit=False):
    """Returns (status, assignment_dict, satisfied_count, stats).
    status is 'SAT' or 'UNSAT'. trace=True prints every step (small wffs only)."""
    st = stats if stats is not None else Stats()
    m = len(clauses)
    assign = [None] * (n_vars + 1)
    stack = []                                  # entries: [identifier, tried_both]

    # a wff with no clauses (or only empty-free trivial ones) may already be true
    n_true, n_false = evaluate(clauses, assign)
    st.evals += 1
    st.best_assignment = _as_full_assignment(assign, n_vars)
    st.best_count = check_assignment(clauses, st.best_assignment)
    if n_true == m:
        return 'SAT', st.best_assignment, m, st
    if n_false > 0:                             # an empty clause: unsatisfiable
        return 'UNSAT', st.best_assignment, n_true, st

    while True:
        #Step 1: choose an unassigned identifier, assign it, push
        unit = pick_unit(clauses, assign) if use_unit else None
        if unit is not None:                    # forced value: no need to try the complement
            v, value = unit
            assign[v] = value
            stack.append([v, True])
        else:
            v = pick_unassigned(assign, n_vars)
            assign[v] = True
            stack.append([v, False])
        st.nodes += 1
        if len(stack) > st.max_depth:
            st.max_depth = len(stack)
        if trace:
            print(f"  step1 push x{v}={'T' if assign[v] else 'F'}{' (unit)' if unit else '       '}       | {_fmt(assign, n_vars)}")

        #Step 2: evaluate; backtrack while some clause is FALSE
        while True:
            n_true, n_false = evaluate(clauses, assign)
            st.evals += 1
            if trace:
                print(f"  step2 eval: {n_true} true, {n_false} false, {m - n_true - n_false} undetermined")
            if m - n_false > st.best_count:     # this branch could still beat the best
                full = _as_full_assignment(assign, n_vars)
                count = check_assignment(clauses, full)
                if count > st.best_count:
                    st.best_count = count
                    st.best_assignment = full

            if n_true == m:                     # 2a: all clauses TRUE
                return 'SAT', _as_full_assignment(assign, n_vars), m, st

            if n_false == 0:                    # undetermined only -> Step 1
                break

            # 2b(ii)/(iii): pop identifiers that have tried both values
            while stack and stack[-1][1]:
                var, _ = stack.pop()
                assign[var] = None
                st.deep += 1
                if trace:
                    print(f"  deep backtrack: pop x{var}        | {_fmt(assign, n_vars)}")
            if not stack:
                return 'UNSAT', st.best_assignment, st.best_count, st

            # 2b(i): complement the top identifier (shallow backtrack)
            top = stack[-1]
            assign[top[0]] = not assign[top[0]]
            top[1] = True
            st.shallow += 1
            st.nodes += 1
            if trace:
                print(f"  shallow backtrack: x{top[0]}={'T' if assign[top[0]] else 'F'}   | {_fmt(assign, n_vars)}")


# Timeout wrapper (same idea as Project 1A: Unix SIGALRM)
class SolverTimeout(Exception):
    pass


def _handler(signum, frame):
    raise SolverTimeout()


def back_sat_with_timeout(n_vars, clauses, timeout_sec=15, use_unit=False):
    """Returns (status, assignment, satisfied_count, elapsed_sec, stats).
    status is 'SAT', 'UNSAT' or 'TIMEOUT'. Only the search is timed."""
    st = Stats()
    signal.signal(signal.SIGALRM, _handler)
    signal.setitimer(signal.ITIMER_REAL, timeout_sec)
    start = time.perf_counter()
    try:
        status, assignment, count, st = back_sat(n_vars, clauses, st, use_unit=use_unit)
        elapsed = time.perf_counter() - start
        signal.setitimer(signal.ITIMER_REAL, 0)
        return status, assignment, count, elapsed, st
    except SolverTimeout:
        elapsed = time.perf_counter() - start
        return 'TIMEOUT', st.best_assignment, st.best_count, elapsed, st
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)


def check_assignment(clauses, assignment):
    """Independent verifier: number of clauses a full assignment satisfies."""
    return sum(1 for c in clauses
               if any((lit > 0) == assignment[abs(lit)] for lit in c))