"""Trim GeoNames dumps to the compact files the engine ships (run once, commit output).

Inputs (downloaded from https://download.geonames.org/export/dump/): cities15000.txt,
countryInfo.txt, admin1CodesASCII.txt  -> outputs: cities.tsv, countries.tsv, admin1.tsv
"""
from pathlib import Path

D = Path(__file__).resolve().parents[1] / "src" / "kundli" / "data"

with (D / "cities15000.txt").open(encoding="utf-8") as f, (D / "cities.tsv").open("w", encoding="utf-8") as out:
    out.write("name\tascii\talts\tlat\tlon\tcc\tadmin1\tpop\ttz\n")
    rows = []
    for line in f:
        p = line.rstrip("\n").split("\t")
        alts = sorted({a for a in p[3].split(",") if a and a.isascii()} - {p[1], p[2]})
        rows.append((int(p[0]), [p[1], p[2], "|".join(alts), p[4], p[5], p[8], p[10], p[14], p[17]]))
    for _, r in sorted(rows):  # sorted by geonameid: deterministic
        out.write("\t".join(r) + "\n")

with (D / "countryInfo.txt").open(encoding="utf-8") as f, (D / "countries.tsv").open("w", encoding="utf-8") as out:
    for line in f:
        if line.startswith("#") or not line.strip():
            continue
        p = line.split("\t")
        out.write(f"{p[0]}\t{p[4]}\n")

with (D / "admin1CodesASCII.txt").open(encoding="utf-8") as f, (D / "admin1.tsv").open("w", encoding="utf-8") as out:
    for line in f:
        p = line.rstrip("\n").split("\t")
        out.write(f"{p[0]}\t{p[2]}\n")
