from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from PIL import Image
from io import BytesIO
import warnings

def warn(*args, **kwargs):
    pass

warnings.warn = warn



def html_to_img(driver,html_content,id_count):
    '''converts html to image and bounding boxes of each cell'''
    counter=1                #This counter is to keep track of the exceptions and stop execution after 10 exceptions have occurred
    add_border = 2
    while(True):
        try:
            driver.get("data:text/html;charset=utf-8," + html_content)

            el = driver.find_element_by_tag_name('table')
            png = el.screenshot_as_png

            im = Image.open(BytesIO(png))

            table_loc = el.location

            bboxes=[]
            for id in range(id_count):
                # print(id)
                e = WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.ID, str(id))))
                txt=e.text.strip()
                lentext=len(txt)
                loc = e.location
                size_ = e.size
                xmin = loc['x'] - table_loc['x'] - add_border
                ymin = loc['y'] - table_loc['y'] - add_border
                xmax = int(size_['width'] + xmin) + add_border * 2
                ymax = int(size_['height'] + ymin) + add_border * 2
                bboxes.append([lentext,txt,xmin,ymin,xmax,ymax])

            return im, bboxes
        except Exception as e:
            counter+=1
            return None, None
            # if counter==10:
            #     return im,None

            # continue