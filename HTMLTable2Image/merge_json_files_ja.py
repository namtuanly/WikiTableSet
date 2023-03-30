import os
import json
import shutil

"""merge json line of each table into jsonl file"""

# Japanese
# aspects_val = ['成績', 'テレビアニメ', '人口動態', 'ネット局', 'クレジット']
# aspects_test = ['学区', '大会', '行政', 'メンバー', '放送日程']
aspects_val = ['クレジット']
aspects_test = ['放送日程']

aspects_val_test = aspects_val + aspects_test

base_path = '../wiki_jp_tables_full_border_v3/'

table_image_path = '../wiki_jp_tables_full_border_v3/table_images/'
json_line_train = open(base_path + 'WikiTabNet_jp_v3_table_train.jsonl', 'a')
json_line_val = open(base_path + 'WikiTabNet_jp_v3_table_val.jsonl', 'a')
json_line_test = open(base_path + 'WikiTabNet_jp_v3_table_test.jsonl', 'a')

# make train/val/test folders
os.makedirs(base_path + 'train/', exist_ok=True)
os.makedirs(base_path + 'val/', exist_ok=True)
os.makedirs(base_path + 'test/', exist_ok=True)

count = 0

for filename in os.listdir(table_image_path):
    f_path = os.path.join(table_image_path, filename)
    if os.path.isfile(f_path) and filename.endswith('.json'):
        count += 1
        print(count)
        with open(f_path) as f:
            data = json.load(f)
            if len(data['aspects']) == 0 or data['aspects'][0] not in aspects_val_test:
            # train set
                data['split'] = 'train'
                json.dump(data, json_line_train)
                json_line_train.write('\n')
                shutil.copy(f_path.replace('.json', '.png'), base_path + 'train/')

            elif data['aspects'][0] in aspects_val:
            # val set
                print(data['aspects'][0])
                data['split'] = 'val'
                json.dump(data, json_line_val)
                json_line_val.write('\n')
                shutil.copy(f_path.replace('.json', '.png'), base_path + 'val/')

            elif data['aspects'][0] in aspects_test:
            # test set
                print(data['aspects'][0])
                data['split'] = 'test'
                json.dump(data, json_line_test)
                json_line_test.write('\n')
                shutil.copy(f_path.replace('.json', '.png'), base_path + 'test/')

json_line_train.close()
json_line_val.close()
json_line_test.close()