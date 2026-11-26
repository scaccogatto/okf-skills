"""Attester for runtime bigquery: the executed SQL must equal the sanctioned SQL.

Input: the sanctioned SQL and the receipt's `executed_sql`, both with parameters
already bound. Output: "pass" or "fail". No network, no model.
"""
import re
import sys


def normalize(sql: str) -> str:
    return re.sub(r"\s+", " ", sql).strip().rstrip(";").lower()


def verdict(sanctioned: str, executed: str) -> str:
    return "pass" if normalize(sanctioned) == normalize(executed) else "fail"


if __name__ == "__main__":
    with open(sys.argv[1], encoding="utf-8") as a, open(sys.argv[2], encoding="utf-8") as b:
        print(verdict(a.read(), b.read()))
