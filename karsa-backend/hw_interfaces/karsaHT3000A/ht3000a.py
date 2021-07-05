import csv

def parse_csv_report(f):
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


def dup_cycles(rows):
    res = []
    for row in rows:
        cycles = row.get('Cycle(s)', 1)
        row['Cycle(s)'] = 1
        for i in range(int(cycles)):
            res.append(row)
    return res
