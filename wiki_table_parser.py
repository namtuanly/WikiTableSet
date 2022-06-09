import argparse
import bz2
import ujson
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from tools import *
import cv2
import os
import numpy as np
import random
from bs4 import BeautifulSoup
import multiprocessing
import json


def html_string2list(html_string):
    """this function convert string into list of char and html tag"""
    list_ = []
    idx_tag = -1
    for i, char in enumerate(html_string):
        if char == '<':
            idx_tag = i
        elif idx_tag != -1 and char == '>':
            html_tag = html_string[idx_tag:i+1]

            # ignore comment inside cell content
            if html_tag.startswith('<!--') or html_tag.startswith('<!['):
                idx_tag = -1
                continue

            list_.append(html_tag)
            idx_tag = -1
        elif idx_tag == -1:
            list_.append(char)

    return list_


def create_style(border_cat):
    '''This function will dynamically create stylesheet of tables'''

    style = "<head><style>"
    style += "html{background-color: white;}table{"

    # random center align
    if random.randint(0, 1) == 1:
        style += "text-align:center;"

    style += """border-collapse:collapse;}td,th{padding:6px;padding-left: 6px;padding-right: 6px;"""

    if border_cat == 0:
        style += """ border:1px solid black;} """
    elif border_cat == 2:
        style += """border-bottom:1px solid black;}"""
    elif border_cat == 3:
        style += """border-left: 1px solid black;}
                   th{border-bottom: 1px solid black;} table tr td:first-child, 
                   table tr th:first-child {border-left: 0;}"""
    else:
        style += """}"""

    style += "</style></head>"
    return style


def draw_matrices(img, bboxes, output_file_name):
    ''' This function draws visualizations of cell bounding boxes on a table image '''
    bboxes = bboxes[:, 2:]

    img = img.astype(np.uint8)
    img = np.dstack((img, img, img))

    im = img.copy()
    pad_ = 3
    for box in bboxes:
        cv2.rectangle(im, (int(box[0]) + pad_, int(box[1]) + pad_),
                      (int(box[2]) - pad_, int(box[3]) - pad_),
                      (0, 0, 255), 1)
    img_name = os.path.join('bboxes/', output_file_name)
    cv2.imwrite(img_name, im)


def check_int_span(s):
    # check span col/row is between 2~20
    if not s.isdigit():
        return False
    if int(s) < 2 or int(s) > 20:
        return False
    return True


def transform_html_id_text(html_input):
    """
    change all <th> tag inside <thead> to <td> tag
    add <span id=''> to content of <td> tag (generate location of cell content)
    """

    html = """<html>"""
    html += create_style(1)
    html += """<body>"""
    html += html_input
    html += """</body></html>"""

    html = html.replace('> </td>', '></td>')
    html = html.replace('> </th>', '></th>')
    html = html.replace('\n', '')
    # html = html.replace('border="1"', '')

    # print(html)

    idx_count = 0

    table_ = BeautifulSoup(html, "lxml")

    struc_tokens = []
    list_cell_contents = []

    # ############ Remove caption ##############
    # will be changed to remain the table title in a table image
    caption_ = table_.find_all('caption')
    if len(caption_) > 0:
        for cap_ in caption_:
            cap_.string = ''

    # #################get thead and tbody#################
    thead = table_.find_all('thead')
    if len(thead) > 1:
        return None, None, None, idx_count
    tbody = table_.find_all('tbody')
    if len(tbody) > 1:
        return None, None, None, idx_count

    thead_tbody = thead + tbody
    if len(thead_tbody) == 0:
        return None, None, None, idx_count

    for tag_ in thead_tbody:
        if tag_.name == 'thead':
            struc_tokens.append('<thead>')
        else:
            struc_tokens.append('<tbody>')

        #  get tr and td
        for tr in tag_.find_all('tr'):
            if len(tr.find_all('td') + tr.find_all('th')) == 0:
                continue
            struc_tokens.append('<tr>')

            for td in (tr.find_all('td') + tr.find_all('th')):
                if td.find_all('table'):
                    # if there is a table inside the cell, then ignore this pattern
                    return None, None, None, idx_count
                if len(td.contents) == 0:
                    list_cell_contents.append([])
                    struc_tokens.append('<td>')
                    struc_tokens.append('</td>')
                    continue
                if td.text.strip() == '':
                    list_cell_contents.append([])
                    struc_tokens.append('<td>')
                    struc_tokens.append('</td>')
                    continue

                # print(''.join(str(el) for el in td.contents))
                # print(html_string2list(''.join(str(el) for el in td.contents)))

                # store the content of this cell
                list_cell_contents.append(html_string2list(''.join(str(el) for el in td.contents)))
                # add <span id=''> to content of <td> tag to generate location of cell content
                td.string = '<span id=' + str(idx_count) + '>' + ''.join(str(el) for el in td.contents) + '</span>'
                idx_count = idx_count + 1

                if (not td.has_attr('colspan')) and (not td.has_attr('rowspan')):
                    struc_tokens.append('<td>')
                    struc_tokens.append('</td>')
                else:
                    struc_tokens.append('<td')
                    if td.has_attr('colspan'):
                        if not check_int_span(td['colspan']):
                            return None, None, None, idx_count

                        struc_tokens.append(' colspan="' + td['colspan'] + '"')
                    if td.has_attr('rowspan'):
                        if not check_int_span(td['rowspan']):
                            return None, None, None, idx_count

                        struc_tokens.append(' rowspan="' + td['rowspan'] + '"')

                    struc_tokens.append('>')
                    struc_tokens.append('</td>')

            struc_tokens.append('</tr>')

        if tag_.name == 'thead':
            struc_tokens.append('</thead>')
        else:
            struc_tokens.append('</tbody>')

    return struc_tokens, table_.prettify(formatter=None), list_cell_contents, idx_count


class WikiTableParser(object):
    def __init__(self, jsonl_path, split='train', start_id=0, end_id=-1, nproc=1):
        self.jsonl_path = jsonl_path
        self.split = split
        self.start_id = start_id
        self.end_id = end_id
        self.chunks_nums = nproc
        self.save_path = '../wiki_jp_tables_debug/'


    def get_number_tables(self):
        """
        count number of table in an JsonLine file.
        return:
        """

        if self.jsonl_path.endswith(".bz2"):
            jsonFile = bz2.BZ2File(self.jsonl_path)
        else:
            jsonFile = open(self.jsonl_path, "r")

        count = 0
        idx = self.start_id
        while True:
            line = jsonFile.readline()
            if not line:
                break
            if idx > self.end_id:
                break

            count += 1
            idx += 1

        return count

    def divide_table_ids(self, counts):
        """
        This function is used to divide all tables to nums chunks.
        nums is equal to process nums.
        :param counts:
        :return: table_chunks
        """
        nums_per_chunk = counts // self.chunks_nums
        table_chunks = []
        for n in range(self.chunks_nums):
            if n == self.chunks_nums - 1:
                s = n * nums_per_chunk
                table_chunks.append([s, count])
            else:
                s = n * nums_per_chunk
                e = (n + 1) * nums_per_chunk
                table_chunks.append([s, e])
        return table_chunks


    def parse_wiki_tables_mp(self, table_chunks):
        """
        multiprocessing to parse raw data.
        One process to do one chunk parsing.
        :param table_chunks:
        :return:
        """
        p = multiprocessing.Pool(self.chunks_nums)
        for i in range(self.chunks_nums):
            this_chunk = table_chunks[i]
            p.apply_async(self.read_json_tables, (this_chunk, i,))
        p.close()
        p.join()


    def read_json_tables(self, this_chunk, chunks_idx):
        """
        Read Japanese Wikipedia tables from one table chunk.
        :param: this_chunk
        :param: chunks_idx
        """

        opts = Options()
        opts.add_argument("--headless")

        driver = webdriver.Firefox(options=opts)

        if self.jsonl_path.endswith(".bz2"):
            jsonFile = bz2.BZ2File(self.jsonl_path)
        else:
            jsonFile = open(self.jsonl_path, "r")
        i = 0
        while True:

            line = jsonFile.readline()
            if not line:
                break

            if i < this_chunk[0] or i >= this_chunk[1]:
                i += 1
                continue

            i += 1

            table_obj = ujson.loads(line)
            print(f"{chunks_idx} - {i}. Page " + table_obj["url"] + " - Index: " + str(table_obj["index"]))

            struc_tokens, html_with_id, list_cell_contents, idx_count = transform_html_id_text(table_obj["html"])

            if struc_tokens is None:
                # save error patterns to folder
                with open(self.save_path + 'errors/' + str(i) + '.json', 'w') as s_json:
                    json.dump(table_obj, s_json)
                continue

            im, bboxes = html_to_img(driver, html_with_id, idx_count)
            if bboxes is None:
                # save error patterns to folder
                with open(self.save_path + 'errors/' + str(i) + '.json', 'w') as s_json:
                    json.dump(table_obj, s_json)
                continue

            im.save(self.save_path + self.split + '/' + str(i) + '.png', dpi=(600, 600))

            #
            cells = []
            idx_ = 0
            for cell_token_ in list_cell_contents:
                if len(cell_token_) == 0:
                    cell_ = {'tokens': cell_token_}
                else:
                    cell_ = {'tokens': cell_token_,
                             'bbox': bboxes[idx_][2:]}
                    idx_ += 1

                cells.append(cell_)

            html_json = {'structure': {'tokens': struc_tokens},
                         'cells': cells
                         }

            # save to folder
            table_sample = {'filename': str(i) + '.png',
                            'split': self.split,
                            'imgid': i,
                            'html': html_json}

            with open(self.save_path + self.split + '/' + str(i) + '.json', 'w') as s_json:
                json.dump(table_sample, s_json)

            # # ##########debug
            # with open('bboxes/' + str(i) + '.txt', 'w') as f:
            #     f.write(html_with_id)
            #     f.write(str(table_sample))
            #
            # img = np.asarray(im, np.int64)[:, :, 0]
            # draw_matrices(img, np.array(bboxes), str(i) + '.jpg')
            # # #########################

        driver.quit()


if __name__ == "__main__":
    # number processes
    nproc = 32
    split = 'train'

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--start_id", "-s", default=0, help="First table id to be parsed",
    )
    parser.add_argument(
        "--end_id", "-e", default=-1, help="Last table id to be parsed",
    )
    args = parser.parse_args()

    # path of wiki table json file
    json_file = '../HTML_JA_WP_tables/table_ja_PubTabNet.jsonl'

    parser = WikiTableParser(jsonl_path=json_file, split=split, start_id=int(args.start_id), end_id=int(args.end_id), nproc=nproc)
    count = parser.get_number_tables()
    table_chunks = parser.divide_table_ids(count)
    parser.parse_wiki_tables_mp(table_chunks)


