import csv

def parse_csv_report(file_path):
    with open(file_path, 'r') as f:
        res = []
        d = {}
        rows = csv.reader(f)
        for r in rows:
            if not r:
                continue
            if r == [' ', '', '']:
                if 'Sequence step' in d:
                    res.append(d)
                d = {}
            for c in r:
                try:
                    k, v = c.split(':')
                    if k.startswith('Creation'):
                        # Skip Creation date in last step
                        raise ValueError
                except ValueError:
                    continue
                d[k.strip()] = v.strip()
        if 'Sequence step' in d:
            res.append(d)
    return res