import os
import json
import shutil

"""merge json line of each table into jsonl file"""

# English
'''Table count:4291914
{'Results': 190838, 'External links': 111393, 'Charts': 104696, 'Filmography': 103217, 'Election results': 96200, 
'References': 90226, 'Discography': 64371, 'Career statistics': 63503, 'Ward results': 61027, 'Schedule': 55790, 
'Regular season': 50164, 'Episodes': 48971, 'Reception': 47853, 'Game summaries': 43775, 'Statistics': 32107, 
'Elections': 30987, 'Competitions': 29669, 'Players': 27658, 'Awards and nominations': 27229, 'Release history': 22183, 
'Electoral history': 21414, 'Transfers': 21154, 'Awards': 21125, 'Medalists': 20081, 'Chart performance': 19961, 
'History': 19085, 'Teams': 18872, 'Demographics': 18420, 'Round robin results': 17997, 'Certifications': 17668}'''

aspects_val = ['Release history', 'Awards and nominations', 'Players', 'Electoral history']
aspects_test = ['History', 'Chart performance', 'Medalists', 'Awards', 'Transfers']

aspects_val_test = aspects_val + aspects_test

base_path = '../wiki_en_tables_borderless/wiki_en_tables_borderless_89/'

table_image_path = '../wiki_en_tables_borderless/part_8/table_images/'
json_line_train = open(base_path + 'WikiTabNet_en_89_table_train.jsonl', 'a')
json_line_val = open(base_path + 'WikiTabNet_en_89_table_val.jsonl', 'a')
json_line_test = open(base_path + 'WikiTabNet_en_89_table_test.jsonl', 'a')

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