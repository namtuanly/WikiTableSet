import argparse
import bz2
import ujson
import os
import numpy as np
from WikiTableGeneration import wiki_table_parser
from collections import Counter

if __name__ == "__main__":
    # number processes
    nproc = 16

    # path of wiki table json file
    json_file = '../html_wiki_tables/en.jsonl'

    save_path_ = '../wiki_en_tables_borderless/'

    parser = wiki_table_parser.WikiTableParser(jsonl_path=json_file, save_path=save_path_, start_id=1, end_id=-1, chunks_nums=nproc)
    count, table_statistics = parser.get_table_statistics()

    sorted_table_statistics = dict(Counter(table_statistics).most_common(30))
    print('Table count:' + str(count))
    print(str(sorted_table_statistics))



