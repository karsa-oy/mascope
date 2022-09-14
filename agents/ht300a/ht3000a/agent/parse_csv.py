import csv
import os
import sys

def parse_csv_report(f):
    def dup_cycles(rows):
        res = []
        for row in rows:
            cycles = row.get('Cycle(s)', 1)
            row['Cycle(s)'] = 1
            for i in range(int(cycles)):
                res.append(row)
        return res

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
    return dup_cycles(res)


# example of usage
if __name__ == "__main__":
    filename = sys.argv[1]
    # read
    with open(filename) as f:
        res = parse_csv_report(f)
    # write
    new_filename = '_'.join(os.path.splitext(filename))
    with open(new_filename, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=res[0].keys())
        writer.writeheader()
        writer.writerows(res)