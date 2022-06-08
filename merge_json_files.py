import os
import json

"""merge json line of each table into jsonl file"""

split_ = 'train'
directory = '../wiki_jp_tables/' + split_ + '/'
json_line = open('../wiki_jp_tables/WikiTabNet_1.0.0_table_' + split_ + '.jsonl', 'w')
count = 0

for filename in os.listdir(directory):
    f_path = os.path.join(directory, filename)
    if os.path.isfile(f_path) and filename.endswith('.json'):
        count += 1
        print(count)
        with open(f_path) as f:
            data = json.load(f)
            json.dump(data, json_line)
            json_line.write('\n')

json_line.close()