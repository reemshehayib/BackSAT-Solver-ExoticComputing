import os

HERE = os.path.dirname(os.path.abspath(__file__))
PARENT = os.path.dirname(HERE)
SEARCH = [HERE, os.path.join(HERE, 'data'), os.path.join(HERE, 'results'),
          PARENT, os.path.join(PARENT, 'data'), os.path.join(PARENT, 'results'),
          os.path.join(PARENT, 'code')]

RESULTS = os.path.join(HERE, 'results')   
CHARTS = os.path.join(HERE, 'charts')     
DATA = os.path.join(HERE, 'data')        


def find(name, required=True):
    """Return the full path of a file, looking in SEARCH. Paths that already
    exist (e.g. typed on the command line) are returned unchanged."""
    if os.path.exists(name):
        return os.path.abspath(name)
    for d in SEARCH:
        p = os.path.join(d, os.path.basename(name))
        if os.path.exists(p):
            return p
    if required:
        raise FileNotFoundError(
            f"Could not find {name}. Looked in:\n  " + "\n  ".join(SEARCH) +
            "\nPass the full path instead, e.g. python run_back.py /path/to/" + os.path.basename(name))
    return None
