import json5
import subprocess
from collections import Counter, defaultdict


def parse_single_query(query, tables):
    p = subprocess.Popen(["static/query_parser", query] + tables, stdout=subprocess.PIPE,  stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()
    try:
        return json5.loads(str(stdout))
    except Exception as e:
        print("error when parsing query:", query)
        print(stdout)
        print(stderr)
        print(e)


def parse_multiple_query(queries, tables):
    column_access_freq = defaultdict(Counter)
    join_freq = Counter()
    table_acess_freq = Counter()
    for q in queries:
        parse_result = parse_single_query(q, tables)
        if parse_result is None:
            continue
        for col, clause in parse_result['columns_accessed_by_clause']:
            column_access_freq[clause][col] += 1
        for j in parse_result['joins']:
            join_freq[j] += 1
        for t in parse_result['tables_accessed']:
            table_acess_freq[t] += 1
    return column_access_freq, join_freq, table_acess_freq


def concise_report(column_access_freq, join_freq, table_acess_freq):
    return {"column_access_freq": column_access_freq, "join_freq": join_freq, "table_access_freq": table_acess_freq}

