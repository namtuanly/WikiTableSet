from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from PIL import Image
from io import BytesIO
import warnings

def warn(*args, **kwargs):
    pass

warnings.warn = warn



def html_to_img(driver, html_content, id_count, table_id):
    '''converts html to image and bounding boxes of each cell'''
    counter=1                #This counter is to keep track of the exceptions and stop execution after 10 exceptions have occurred
    add_border_init = 5
    while(True):
        try:
            driver.get("data:text/html;charset=utf-8," + html_content)

            # get window size
            # old_h = driver.get_window_size()['height']
            old_w = driver.get_window_size()['width']

            # ##### START webdriver.Chrome ##########
            driver.implicitly_wait(30)

            # obtain browser height and width
            # w = driver.execute_script('return document.body.parentNode.scrollWidth')
            h = driver.execute_script('return document.body.parentNode.scrollHeight')
            # set to new window size
            driver.set_window_size(old_w, h)

            driver.implicitly_wait(30)
            # get window size
            # print(str(old_w) + " : " + str(old_h) + " : " + str(w) + " : " + str(h) + " : " + str(table_id))
            # ##### END webdriver.Chrome ##########

            # el = driver.find_element_by_tag_name('table')
            el = driver.find_element_by_id('screenshot_as_png_tables')
            png = el.screenshot_as_png

            im = Image.open(BytesIO(png))

            table_loc = el.location

            bboxes=[]
            for id in range(id_count):
                # print(id)
                e = WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.ID, str(id))))

                if e.tag_name == 'th':
                    add_border = -3
                else:
                    add_border = add_border_init

                txt=e.text.strip()
                lentext=len(txt)
                loc = e.location
                size_ = e.size
                xmin = loc['x'] - table_loc['x'] - add_border
                ymin = loc['y'] - table_loc['y'] - add_border
                xmax = int(size_['width'] + xmin) + add_border * 2
                ymax = int(size_['height'] + ymin) + add_border * 2
                bboxes.append([lentext,txt,xmin,ymin,xmax,ymax])

                if xmax > im.size[0] or ymax > im.size[1]:
                    # print(str(im.size) + ":" + str([lentext,txt,xmin,ymin,xmax,ymax]) + " : " + str(table_id))
                    return im, None

            return im, bboxes
        except Exception as e:
            counter+=1
            return None, None
            # if counter==10:
            #     return im,None

            # continue