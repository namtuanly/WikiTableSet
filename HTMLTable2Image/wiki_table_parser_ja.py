import argparse
import bz2
import ujson
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver import ChromeOptions
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from tools import *
import cv2
import os
import numpy as np
import random
from bs4 import BeautifulSoup, Comment
import multiprocessing
import json
from tqdm import tqdm
from gimei import Gimei
import os


MAX_ROWS = 40    # max number rows in table
MAX_ROW_SPAN = 25    # max row spanning in table
MAX_COL_SPAN = 15    # max col spanning in table
MAX_WIDTH_IMAGE = 1366  # max table image width


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


def norm_cell_content_tokens(content_tokens):
    """
    :param content_tokens: [list]. text content of each cell.
    :return: list token of cell content after normalize cell content tokens.
    """
    blank_token = ' '

    html_tag_ = [
                 # tags of a html list
                 '<ol>', '<li>', '</li>', '</ol>', '<dl>', '<dd>',
                 '</dd>', '</dl>', '<ul>', '</ul>', '<dt>', '</dt>',
                 '<bdi>', '</bdi>',

                 # other tags
                 '<hr/>', '<sub>', '</sub>', '<sup>', '</sup>',
                 '<center>', '</center>', '<pre>', '</pre>',
                 '<big>', '</big>',
                 '<blockquote>', '</blockquote>',
                 '<q>', '</q>',

                 # header html
                 '<h2>', '</h2>', '<h3>', '</h3>',
                 '<h4>', '</h4>', '<h5>', '</h5>',

                 # Ruby tags
                 '<ruby>', '</ruby>', '<rb>', '</rb>', '<rp>', '</rp>',
                 '<rt>', '</rt>', '<rtc>', '</rtc>',

                 # MathML tags
                 '<math>', '</math>', '<mstyle>', '</mstyle>', '<mn>', '</mn>',
                 '<msubsup>', '</msubsup>', '<mtable>', '<mtr>', '<mtd>', '</mtd>', '</mtr>', '</mtable>',
                 '<munderover>', '</munderover>', '<msqrt>', '</msqrt>', '<mtext>', '</mtext>',
                 '<mspace>', '</mspace>', '<mrow>', '</mrow>', '<mi>', '</mi>', '<mo>', '</mo>',
                 '<mfrac>', '</mfrac>', '<msup>', '</msup>', '<msub>', '</msub>',
                 '<mmultiscripts>', '</mmultiscripts>', '<mprescripts>', '</mprescripts>',
                 '<mroot>', '</mroot>', '<munder>', '</munder>', '<mpadded>', '</mpadded>',
                 '<mover>', '</mover>'
                 ]

    # define Diagonal split header tags
    html_diagonal_split_header = ['<div class="rightItem">', '</div>',
                                  '<div class="leftItem">', '</div>']

    # define text as special text
    # the html tags in the group have same function -> can be considered as one tag
    html_beak_line_tags = [
                # break line
                '<br>', '<br/>',
                ]
    html_del_tags = [
                # delete
                '</s>', '<s>',
                '<del>', '</del>',
                ]

    html_small_tags = [
                # small tags
                '<small>', '</small>',
                '<samp>', '</samp>',
                '<kbd>', '</kbd>',
                '<code>', '</code>',
                '<tt>', '</tt>',
                ]

    html_underline_tags = [
                # underline
                '<u>', '</u>',
                '<ins>', '</ins>'
                ]

    html_italic_tags = [
                # italic
                '<i>', '</i>',
                '<em>', '</em>',
                '</cite>', '<cite>',
                '<var>', '</var>',
                ]

    html_bold_tags = [
                # bold
                '<b>', '</b>',
                '<strong>', '</strong>',
                ]

    # html tags will be ignored
    ignore_html_tag = ['<urlset>', '<url>', '<be/>',
                       '<source/>', '<track/>', '<be />', '<wbr/>', '<wbr>'
                       '<p>', '</p>', '<abbr>', '</abbr>', '<section>', '</section>',
                       '<annotation>', '</annotation>', '<none>', '</none>',
                       '<font>', '</font>', '<semantics>', '</semantics>',
                       '<ref>', '</ref>', '<meta/>', '<span>', '</span>'
                       ]

    # html tags and their content will be ignored
    ignore_html_tag_and_content = ['<style>',  # '</style>',
                                   '<title>',  # '</title>',
                                   '<video>',  # '</video>',
                                   '<audio>',  # '</audio>',
                                   '<img>',  # '</img>',

                                   # figure
                                   '<figure>',  # '</figure>',
                                   # '<figcaption>', '</figcaption>',
                                   # '<figure-inline>', '</figure-inline>',
                                   ]

    # flag ignore both tag and content
    ignore_content_flag = False
    current_ignore_tag = ''

    new_content = []
    for char in content_tokens:
        # ignore tag and content in ignore_html_tag_and_content
        # ignore_content_flag is True
        if ignore_content_flag:
            if char == current_ignore_tag:
                ignore_content_flag = False
                current_ignore_tag = ''
            continue

        # char is single character
        if len(char) == 1:
            new_content.append(char)
            continue

        # ignore HTML comments
        if char.startswith('<!--'):
            continue
        if char.startswith('<!['):
            continue

        # # define Diagonal split header tags
        if char in html_diagonal_split_header:
            new_content.append(char)
            continue

        # remove attributes parameters in html tags
        space_idx = char.find(' ')
        if char.startswith('<') and char.endswith('>') and space_idx != -1:
            char = char[:space_idx] + '>'

        # ignore tag and content in ignore_html_tag_and_content
        if char in ignore_html_tag_and_content:
            ignore_content_flag = True
            current_ignore_tag = char[:1] + '/' + char[1:]
            continue

        # ignore tags in ignore_html_tag
        if char in ignore_html_tag:
            continue

        # HTML small tags
        if char in html_small_tags:
            if char.startswith('</'):
                new_content.append('</small>')
            else:
                new_content.append('<small>')
            continue

        # HTML beak line tags
        if char in html_beak_line_tags:
            new_content.append('<br>')
            continue

        # HTML underline tags
        if char in html_underline_tags:
            if char.startswith('</'):
                new_content.append('</u>')
            else:
                new_content.append('<u>')
            continue

        # HTML italic tags
        if char in html_italic_tags:
            if char.startswith('</'):
                new_content.append('</i>')
            else:
                new_content.append('<i>')
            continue

        # HTML bold tags
        if char in html_bold_tags:
            if char.startswith('</'):
                new_content.append('</b>')
            else:
                new_content.append('<b>')
            continue

        # HTML del tags
        if char in html_del_tags:
            if char.startswith('</'):
                new_content.append('</del>')
            else:
                new_content.append('<del>')
            continue

        if char in html_tag_:
            new_content.append(char)
            continue

        # if char is html tag and not in html_tag_ then do nothing
        if bool(BeautifulSoup(char, "html.parser").find()):
            continue

        # char is string started with '<'
        new_content.extend(list(char))

    if len(new_content) == 0:
        new_content.append(blank_token)

    return new_content


def create_style(border_cat, border_cell):
    '''This function will dynamically create stylesheet of tables'''

    # list fonts in English
    # https://www.tutorialbrain.com/css_tutorial/css_font_family_list/
    font_list_en = ['Arial', 'Helvetica', 'Verdana', 'Calibri', 'Noto',
                 'Lucida Sans', 'Gill Sans', 'Century Gothic', 'Candara',
                 'Futara', 'Franklin Gothic', 'Medium', 'Trebuchet MS',
                 'Geneva', 'Segoe UI', 'Optima', 'Avanta Garde',
                 'Times New Roman']

    # change in Japanese
    # list font in Japanese
    # https://stackoverflow.com/questions/14563064/japanese-standard-web-fonts
    font_list_ja = ['Osaka', 'YuGothic', 'sans-serif', 'Verdana',
                    '"Hiragino Kaku Gothic Pro"', '']

    html_font = 'font-family:' + random.choice(font_list_ja) + ';'

    style = "<head><style>"
    style += "html{background-color: white;" + html_font + "}table{"

    # random border width
    border_table = random.randint(1, 3)

    # random cell padding width
    padding_border = random.randint(5, 8)
    padding_no_border = random.randint(10, 12)

    # random center align
    if random.randint(0, 1) == 1:
        style += "text-align:center;"

    if border_cat == 0:
        # full border of table
        style += "border:" + str(border_table) + "px solid black;"

    style += "border-collapse:collapse;}th{text-align:center;}"

    if border_cat == 0:
    # full border
        style += "td,th{padding:" + str(padding_border) + "px;border:" + str(border_cell) + "px solid black;}"

    elif border_cat == 1:
    # bottom border
        style += "td,th{padding-top:" + str(padding_border) + "px;padding-bottom:" + str(padding_border) + \
                 "px;padding-left:" + str(padding_no_border) + "px;padding-right:" + str(padding_no_border) + \
                 "px;border-bottom:" + str(border_cell) + "px solid black;}"

    elif border_cat == 2:
    # left border
        style += "td,th{padding-top:" + str(padding_no_border) + "px;padding-bottom:" + str(padding_no_border) + \
                 "px;padding-left:" + str(padding_border) + "px;padding-right:" + str(padding_border) + "px;" + \
                 "border-left: " + str(border_cell) + "px solid black;}"
        # randomly add border line to table header
        if random.randint(0, 1) == 1:
            style += "th{border-bottom: " + str(border_table) + "px solid black;}"
        else:
            style += "th{border-bottom: " + str(border_table) + "px solid black;border-top: " + str(border_table) + "px solid black;}"

        # random Background Colors of rows
        if random.randint(1, 100) <= 20:
            style += """tr:nth-child(even){background-color: LightGray;}tr:nth-child(odd){background-color: white;}"""

    elif border_cat == 3:
    # no border (or only bottom border of header)
        style += "td,th{padding:" + str(padding_no_border) + "px;}"
        # randomly add border to table header
        if random.randint(0, 1) == 1:
            if random.randint(0, 1) == 1:
                style += "th{border-bottom: " + str(border_table) + "px solid black;}"
            else:
                style += "th{border-bottom: " + str(border_table) + "px solid black;border-top: " + str(border_table) + "px solid black;}"

        # random Background Colors of rows
        if random.randint(1, 100) <= 20:
            style += """tr:nth-child(even){background-color: LightGray;}tr:nth-child(odd){background-color: white;}"""

    # Japanese: add style of diagonal cell: leftItem and rightItem
    #   div.leftItem {
    #   position:absolute;
    #   left: 4px;
    #   bottom: 3px;
    #   }
    # div.rightItem {
    #   position:absolute;
    #   right: 4px;
    #   top: 3px;
    #   }
    div_left = random.randint(3, 5)
    div_top = random.randint(3, 4)
    div_right = random.randint(3, 5)
    div_bottom = random.randint(3, 4)
    style += "div.leftItem {position:absolute; left: " + str(div_left) + "px; bottom: " + str(div_bottom) + "px;}" + \
             "div.rightItem {position:absolute; right: " + str(div_right) + "px; top: " + str(div_top) + "px;}"

    style += "</style></head>"
    return style


def draw_matrices(img, bboxes, output_file_name, save_path):
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
    img_name = os.path.join(save_path, output_file_name)
    cv2.imwrite(img_name, im)


def check_int_span(s, max_span):
    # check span col/row is between 2~max_span
    if not s.isdigit():
        return False
    if int(s) < 2 or int(s) > max_span:
        return False
    return True


import re
import regex
def change_style_inside_html_tag(style_str):
    # remove style that has # char inside.
    str = style_str
    while re.findall(";[^;]*#[^;]*;", str):
        str = re.sub(";[^;]*#[^;]*;", ";", str)

    while re.findall("^[^;]*#[^;]*;|;[^;]*#[^;]*$|^[^;]*#[^;]*$", str):
        str = re.sub("^[^;]*#[^;]*;|;[^;]*#[^;]*$|^[^;]*#[^;]*$", "", str)
    return str


def change_style_table(style_str):
    # remove style that defines width or height inside.
    str = style_str
    str = re.sub("width:[^;]*;", "", str)
    str = re.sub("height:[^;]*;", "", str)

    str = re.sub("width:[^;]*$", "", str)
    str = re.sub("height:[^;]*$", "", str)

    return str


def is_full_japanese_kanji(str_jp):
    # check text is full Japanese Kanji or not
    # reference: https://note.nkmk.me/python-re-regex-character-type/
    # https://github.com/nkmk/python-snippets/blob/743a86bf1c70d670bbe4e097b14cd3bc2184b6a9/notebook/re_character_type_pattern_example.py#L99-L101
    p = regex.compile(r'\p{Script=Han}+')
    if p.fullmatch(str_jp) is not None:
        return True
    else:
        return False


def is_consist_japanese_char(str):
    # check text consists of Japanese char or not
    pattern = regex.compile(r'.*[\p{IsHan}\p{IsBopo}\p{IsHira}\p{IsKatakana}]+', re.UNICODE)
    if pattern.match(str) is not None:
        return True
    else:
        return False


def get_diagonal_line_style(number_char, border_cell):
    # get style of diagonal line in the first th of header
    diagonal_line_style = """position: relative;
                             background: linear-gradient(
                                to top right,
                                rgba(0, 0, 0, 0) 0%,
                                rgba(0, 0, 0, 0) calc(50% - {}px),
                                rgba(0, 0, 0, 1) 50%,
                                rgba(0, 0, 0, 0) calc(50% + {}px),
                                rgba(0, 0, 0, 0) 100%
                             );
                             background-repeat:no-repeat;
                             background-position:center center;
                             background-size: 100% 100%, auto;
                             padding-left: {}px;
                             height: 30px;""".format(border_cell, border_cell, number_char * 70)

    return diagonal_line_style


def transform_html_id_text(html_input):
    """
    change all <th> tag inside <thead> to <td> tag
    add <span id=''> to content of <td> tag (generate location of cell content)
    """

    # random table margin width between (2, 10px)
    margin_top = random.randint(2, 10)
    margin_right = random.randint(2, 10)
    margin_bottom = random.randint(2, 10)
    margin_left = random.randint(2, 10)

    html = """<html>"""
    html += """<body><div id="screenshot_as_png_tables" 
                          style="padding: {}px {}px {}px {}px; display: inline-block;">
            """.format(margin_top, margin_right, margin_bottom, margin_left)
    html += html_input
    html += """</div></body></html>"""

    html = html.replace('> </td>', '></td>')
    html = html.replace('> </th>', '></th>')
    html = html.replace('\n', '')
    html = html.replace('border="1"', '')

    # print(html)

    idx_count = 0

    table_ = BeautifulSoup(html, "lxml")

    struc_tokens = []
    list_cell_contents = []

    # check if table has rowspan or colspan
    is_rowspan = False
    is_colspan = False
    # remove no border style
    except_noborder = False

    # randomly choice border cell
    border_cell = random.randint(1, 2)

    # if table has diagonal header cell?
    has_diagonal_header_cell = False

    # remove # char in style attributes of all table tags
    tag_has_style = table_.find_all(lambda tag:tag.has_attr('style'))
    for tag_idx in tag_has_style:
        style_str = change_style_inside_html_tag(tag_idx["style"])

        style_str = change_style_table(style_str)

        if style_str == '':
            del tag_idx["style"]
        else:
            tag_idx["style"] = style_str

    #remove all comments and its contents
    for comment_ in table_.find_all(text=lambda text:isinstance(text, Comment)):
        comment_.extract()

    # ############ Remove caption ##############
    # will be changed to remain the table title in a table image
    caption_ = table_.find_all('caption')
    if len(caption_) > 0:
        for cap_ in caption_:
            cap_.string = ''
            cap_.decompose()

    # #################get thead and tbody#################
    thead = table_.find_all('thead')
    if len(thead) > 1:
        return None, None, None, idx_count, has_diagonal_header_cell
    tbody = table_.find_all('tbody')
    if len(tbody) > 1:
        return None, None, None, idx_count, has_diagonal_header_cell

    thead_tbody = thead + tbody
    if len(thead_tbody) == 0:
        return None, None, None, idx_count, has_diagonal_header_cell

    for tag_ in thead_tbody:
        if tag_.name == 'thead':
            struc_tokens.append('<thead>')
        else:
            struc_tokens.append('<tbody>')
            # check if tbody has th tag, if yes then remove no border style
            if len(tag_.find_all('th')) != 0:
                except_noborder = True

        #  get tr and td
        if len(tag_.find_all('tr')) > MAX_ROWS:
        # if number row more than MAX_ROWS, ignore table
            return None, None, None, idx_count, has_diagonal_header_cell

        tr_list = tag_.find_all('tr')
        for tr in tr_list:
            if len(tr.find_all('td') + tr.find_all('th')) == 0:
                continue
            struc_tokens.append('<tr>')

            th_td_list = tr.find_all('td') + tr.find_all('th')
            for td in th_td_list:
                if td.find_all('table'):
                    # if there is a table inside the cell, then ignore this pattern
                    return None, None, None, idx_count, has_diagonal_header_cell
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

                # #################in Japanese: special text alignment in table header #################
                if td.name == 'th':
                    cell_content_ = ''.join(str(el) for el in td.contents)
                    # flag: this cell is diagonal_header_cell
                    diagonal_header_cell = False

                    # make diagonal line in the first th in the first tr
                    # if cell content don't has any html tags
                    # TODO: <br/> (or HTML tags) in cell content  OK
                    if len(th_td_list) > 1 and th_td_list.index(td) == 0 and tr_list.index(tr) == 0 \
                            and (re.search('<.*?>', cell_content_) is None) and len(cell_content_) < 11:

                        # if the cell content has the char '/', split content by '/' into diagonal cell
                        if len(re.findall('[^<]/[^>]', cell_content_)) == 1:
                            split_search = re.search('[^<]/[^>]', cell_content_)
                            left_content = cell_content_[0:split_search.start() + 1]
                            right_content = cell_content_[split_search.start() + 2:]
                            td.string = """<div class="rightItem">{}</div><div class="leftItem">{}</div>""".format(right_content, left_content)
                            len_max = len(left_content) if len(left_content) > len(right_content) else len(right_content)

                            td["style"] = get_diagonal_line_style(len_max, border_cell)
                            td["id"] = idx_count
                            idx_count = idx_count + 1
                            has_diagonal_header_cell = True
                            diagonal_header_cell = True

                        elif is_full_japanese_kanji(cell_content_) and len(cell_content_) < 5 and random.randint(0, 15) == 0:
                            # # randomly generate Japanese words (2~3 words) in the left item of the diagonal cell
                            # # reference: https://github.com/nabetama/gimei
                            name = Gimei().name
                            td.string = """<div class="rightItem">{}</div><div class="leftItem">{}</div>""".format(name.last.kanji, cell_content_)
                            len_max = len(name.last.kanji) if len(name.last.kanji) > len(cell_content_) else len(cell_content_)

                            td["style"] = get_diagonal_line_style(len_max, border_cell)
                            td["id"] = idx_count
                            idx_count = idx_count + 1
                            has_diagonal_header_cell = True
                            diagonal_header_cell = True

                    if not diagonal_header_cell:
                        style_str = ''
                        cell_padding = ''
                        padding_width = random.randint(8, 14)
                        # if text consists of Japanese char and cell is not full rowspan, randomly generate special text alignment
                        # TODO check if cell content has <br> then do not generate special text alignment (ex: 130.png) OK
                        # TODO: if text len is 1 then do not generate special text alignment  OK
                        if len(th_td_list) > 1 and is_consist_japanese_char(cell_content_) and len(cell_content_) > 1\
                                and cell_content_.find('<br>') == -1 and cell_content_.find('<br/>') == -1:
                            # TODO randomly special text alignment   OK
                            if random.randint(0, 1) == 1:
                                style_str = 'text-align:justify;text-align-last:justify;' # ';text-align:justify;text-align-last:justify;text-justify:inter-character;'
                                # TODO add padding to cell when special text alignment  OK
                                cell_padding = 'padding-left: {}px;padding-right: {}px;'.format(padding_width, padding_width)


                        # if this cell is a rowspanning cell and the cell content is full Japanese Kanji text, randomly vertical text
                        # TODO check if text has alphabet or number then donot vertical  OK
                        if td.has_attr('rowspan') and len(cell_content_) > 1 and is_full_japanese_kanji(cell_content_):
                            # TODO randomly vertical text  OK
                            # randomly generate vertical text line
                            # reference: https://www.w3.org/International/articles/vertical-text/
                            if random.randint(0, 1) == 1:
                                style_str = style_str + 'writing-mode:vertical-rl;'
                                if cell_padding == '':
                                    letter_spacing = random.randint(2, 10)
                                    cell_padding = 'padding-top: {}px;padding-bottom: {}px;letter-spacing: {}px;'.format(padding_width, padding_width, letter_spacing)
                                else:
                                    cell_padding = ''

                        style_str = style_str + cell_padding

                        if style_str != '':
                            if td.has_attr('style'):
                                td["style"] = style_str + td["style"]
                            else:
                                td["style"] = style_str

                # ######### end in Japanese #################

                # print(''.join(str(el) for el in td.contents))
                # print(html_string2list(''.join(str(el) for el in td.contents)))

                # store the content of this cell
                list_cell_contents.append(html_string2list(''.join(str(el) for el in td.contents)))

                # add <span id=''> to content of <td> tag to generate location of cell content
                if not td.has_attr('id'):
                    td.string = '<span id=' + str(idx_count) + '>' + ''.join(str(el).replace('#', '&num;') for el in td.contents) + '</span>'
                    idx_count = idx_count + 1

                if (not td.has_attr('colspan')) and (not td.has_attr('rowspan')):
                    struc_tokens.append('<td>')
                    struc_tokens.append('</td>')
                else:
                    struc_tokens.append('<td')
                    if td.has_attr('colspan'):
                        is_colspan = True
                        if not check_int_span(td['colspan'], MAX_COL_SPAN):
                            return None, None, None, idx_count, has_diagonal_header_cell

                        struc_tokens.append(' colspan="' + td['colspan'] + '"')
                    if td.has_attr('rowspan'):
                        is_rowspan = True
                        if not check_int_span(td['rowspan'], MAX_ROW_SPAN):
                            return None, None, None, idx_count, has_diagonal_header_cell

                        struc_tokens.append(' rowspan="' + td['rowspan'] + '"')

                    struc_tokens.append('>')
                    struc_tokens.append('</td>')

            struc_tokens.append('</tr>')

        if tag_.name == 'thead':
            struc_tokens.append('</thead>')
        else:
            struc_tokens.append('</tbody>')

    # create the style of table
    # 0: full border, 1: bottom border, 2: left border style, 3: no border
    style_list = [0, 1, 2, 3]
    if except_noborder:
        # remove no border style
        style_list.remove(3)

    if is_rowspan:
        # remove left border style and no border style
        style_list.remove(2)
        if 3 in style_list:
            style_list.remove(3)
    if is_colspan:
        # remove bottom border style and no border style
        style_list.remove(1)
        if 3 in style_list:
            style_list.remove(3)

    # change in Japanese
    table_style = create_style(0, border_cell) # random.choice(style_list))

    table_html = table_.prettify(formatter=None)
    tag_idx_ = table_html.find('<html>')
    table_html = table_html[:tag_idx_+6] + table_style + table_html[tag_idx_+6:]

    return struc_tokens, table_html, list_cell_contents, idx_count, has_diagonal_header_cell


class WikiTableParser(object):
    def __init__(self, jsonl_path, save_path='', start_id=0, end_id=-1, chunks_nums=1):
        self.jsonl_path = jsonl_path
        self.start_id = start_id
        self.end_id = end_id
        self.chunks_nums = chunks_nums
        self.save_path = save_path
        self.total_samples = 0

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
            if self.end_id != -1 and idx > self.end_id:
                break

            count += 1
            idx += 1

        self.total_samples = count

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
                table_chunks.append([s, counts])
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

        chunk_total_item = 0

        opts = Options()
        opts.add_argument("--headless")

        # driver = webdriver.Firefox(options=opts)

        # ##### START webdriver.Chrome ##########
        options = ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('window-size=1366x768');

        # サービスを起動
        serv = Service(ChromeDriverManager().install())

        # ブラウザーを起動
        driver = webdriver.Chrome(service=serv, options=options)
        driver.maximize_window()
        # ##### END webdriver.Chrome ##########

        if self.jsonl_path.endswith(".bz2"):
            jsonFile = bz2.BZ2File(self.jsonl_path)
        else:
            jsonFile = open(self.jsonl_path, "r")

        # skip samples which are not belong to this_chunk
        for i in range(this_chunk[0]):
            line = jsonFile.readline()
            if not line:
                break

        for i in tqdm(range(this_chunk[0], this_chunk[1])):
            line = jsonFile.readline()
            if not line:
                break

            if i < this_chunk[0] or i >= this_chunk[1]:
                continue

            table_obj = ujson.loads(line)

            # print(f"{chunks_idx} - {i}. Page " + table_obj["url"] + " - Index: " + str(table_obj["index"]))
            # print(table_obj)

            struc_tokens, html_with_id, list_cell_contents, idx_count, has_diagonal_header_cell = transform_html_id_text(table_obj["html"])

            if struc_tokens is None:
                # save error patterns to folder
                with open(self.save_path + 'errors/' + str(i) + 'transform_html_id_text.txt', 'w') as s_json:
                    s_json.write(str(table_obj))
                continue

            im, bboxes = html_to_img(driver, html_with_id, idx_count, i)

            if bboxes is None:
                # save error patterns to folder
                if im is not None:
                    with open(self.save_path + 'errors_big/' + str(i) + '.txt', 'w') as f:
                        f.write(html_with_id)

                    im.save(self.save_path + 'errors_big/' + str(i) + '.png', dpi=(600, 600))
                else:
                    with open(self.save_path + 'errors/' + str(i) + 'html_to_img.txt', 'w') as s_json:
                        s_json.write(str(table_obj))
                        s_json.write(html_with_id)

                continue

            # ##########
            # ignore table image with very big size
            if im.size[0] > MAX_WIDTH_IMAGE or im.size[1] > MAX_WIDTH_IMAGE * 1.5:
                # print(str(im.size) + str(i))
                with open(self.save_path + 'errors_big/' + str(i) + '.txt', 'w') as f:
                    f.write(html_with_id)

                img = np.asarray(im, np.int64)[:, :, 0]
                draw_matrices(img, np.array(bboxes), str(i) + '.jpg', self.save_path + 'errors_big/')

                continue
            # #########################

            im.save(self.save_path + 'table_images/' + str(i) + '.png', dpi=(600, 600))

            #
            cells = []
            idx_ = 0
            for cell_token_ in list_cell_contents:
                if len(cell_token_) == 0:
                    cell_ = {'tokens': cell_token_}
                else:
                    cell_ = {'tokens': norm_cell_content_tokens(cell_token_),
                             'bbox': bboxes[idx_][2:]}
                    idx_ += 1

                cells.append(cell_)

            html_json = {'structure': {'tokens': struc_tokens},
                         'cells': cells
                         }

            # save to folder
            if 'aspects' in table_obj:
                aspects = table_obj['aspects']
            else:
                aspects = ''
            table_sample = {'filename': str(i) + '.png',
                            'aspects': aspects,
                            'imgid': i,
                            'html': html_json}

            with open(self.save_path + 'table_images/' + str(i) + '.json', 'w') as s_json:
                json.dump(table_sample, s_json)

            # # ##########debug
            # with open(self.save_path + 'bboxes/' + str(i) + '.txt', 'w') as f:
            #     f.write(html_with_id)
            #     f.write(str(table_sample))
            #
            # img = np.asarray(im, np.int64)[:, :, 0]
            # draw_matrices(img, np.array(bboxes), str(i) + '.jpg', self.save_path + 'bboxes/')
            # # #########################

            # ######### debug has_diagonal_header_cell
            if has_diagonal_header_cell:
                with open(self.save_path + 'diagonal_header_cell/' + str(i) + '.txt', 'w') as f:
                    f.write(str(html_with_id))
                    f.write(str(table_sample))

                im.save(self.save_path + 'diagonal_header_cell/' + str(i) + '.png', dpi=(600, 600))

                # img = np.asarray(im, np.int64)[:, :, 0]
                # draw_matrices(img, np.array(bboxes), str(i) + '.jpg', self.save_path + 'diagonal_header_cell/')

            chunk_total_item += 1

        print("chunks_idx {} : {} / {} samples".format(chunks_idx, chunk_total_item, this_chunk[1] - this_chunk[0]))
        with open(self.save_path + '/' + str(chunks_idx) + '.txt', 'w') as f_txt:
            f_txt.write("chunks_idx {} : {} / {} samples".format(chunks_idx, chunk_total_item, this_chunk[1] - this_chunk[0]))

        driver.quit()


    def get_table_statistics(self):
        """
        get statistics of table aspects in an JsonLine file.
        return:
        """

        if self.jsonl_path.endswith(".bz2"):
            jsonFile = bz2.BZ2File(self.jsonl_path)
        else:
            jsonFile = open(self.jsonl_path, "r")

        count = 0
        table_statistics = dict()
        while True:
            line = jsonFile.readline()
            if not line:
                break

            count += 1
            table_obj = ujson.loads(line)
            if 'aspects' not in table_obj.keys():
                continue

            if table_obj['aspects'][0] in table_statistics:
                table_statistics[table_obj['aspects'][0]] += 1
            else:
                table_statistics[table_obj['aspects'][0]] = 1

        return count, table_statistics


if __name__ == "__main__":
    # number processes
    nproc = 64

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--start_id", "-s", default=1, help="First table id to be parsed",
    )
    parser.add_argument(
        "--end_id", "-e", default=-1, help="Last table id to be parsed",
    )
    args = parser.parse_args()

    # path of wiki table json file
    json_file = '../html_wiki_tables/ja.jsonl'

    save_path_ = '../wiki_jp_tables_full_border_v2/'
    os.makedirs(save_path_ + 'errors/', exist_ok=True)
    os.makedirs(save_path_ + 'table_images/', exist_ok=True)
    os.makedirs(save_path_ + 'errors_big/', exist_ok=True)
    os.makedirs(save_path_ + 'boxes/', exist_ok=True)

    parser = WikiTableParser(jsonl_path=json_file, save_path=save_path_, start_id=int(args.start_id), end_id=int(args.end_id), chunks_nums=nproc)
    count_ = parser.get_number_tables()

    print("Total samples: {}".format(count_))

    table_chunk_ = parser.divide_table_ids(counts=count_)
    parser.parse_wiki_tables_mp(table_chunks=table_chunk_)


