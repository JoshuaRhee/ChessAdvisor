
import chromedriver_autoinstaller
import io
from itertools import compress
import os
import pickle
from PIL import Image, ImageDraw, ImageEnhance
import PySimpleGUI as sg
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from time import sleep
import yaml

def update_db(do=False):
    if do or not os.path.exists('data/deck_list.pkl'):
        if not do:
            choice = sg.popup_ok_cancel('데이터 베이스가 존재하지 않아 다운로드 받아야합니다.', '수 분 정도 시간이 소요될 수 있습니다.','Cancel을 선택하면 프로그램이 종료됩니다.',title='경고')
            if choice != 'OK':
                return None

        chromedriver_autoinstaller.install()
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--window-size=945,520')
        chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
        driver = webdriver.Chrome(options=chrome_options)

        driver.get('https://lolchess.gg/meta')
        deck_boxes = driver.find_elements(By.CLASS_NAME, 'guide-meta__deck-box')
        deck_list = []
        for deck_num,deck_box in enumerate(deck_boxes, start=1):
            # print(f'Crawling a deck...({deck_num}/{len(deck_boxes)})')
            deck_list.append({})
            deck_list[-1]['name'] = deck_box.text.split("\n")[0]
            sleep(0.5)
            driver.find_elements(By.XPATH,f'//*[@id="content-container"]/div[2]/div/div[2]/div[{deck_num}]/div/div[5]/a')[0].click()
            driver.switch_to.window(driver.window_handles[-1])

            for phase_no,phase in enumerate(['ini','mid','fin']):
                driver.find_element(By.XPATH,f'//*[@id="content-container"]/div[2]/div[2]/div[1]/div[1]/div[2]/div/nav/div[{phase_no+1}]').click()
                sleep(0.5)
                phase_png = driver.find_element(By.CLASS_NAME,'css-olyd6o').screenshot_as_png
                deck_img_file_name = f'img/deck/deck{deck_num-1}_{phase}.png'
                with open(deck_img_file_name,'wb') as f:
                    f.write(phase_png)
                img = Image.open(deck_img_file_name)
                (w,h) = img.size
                cropped_img=img.crop((0+30,0,w-30,h-50))
                cropped_img.save(deck_img_file_name)
                deck_list[-1][f'{phase}'] = {}

                cell_list = driver.find_elements(By.CLASS_NAME,'css-jet0gc')
                for cell_num, cell in enumerate(cell_list):
                    if cell.text != '':
                        deck_list[-1][f'{phase}'][f'{cell.text}'] = cell_num
            driver.close()
            driver.switch_to.window(driver.window_handles[-1])
        pickle.dump(deck_list, open('data/deck_list.pkl', 'wb'))
    else:
        deck_list = pickle.load(open('data/deck_list.pkl', 'rb'))
    return deck_list

def update_champ_btn(window, champ, border=False, darker=False):
    if not darker and not border:
        window[champ].update(image_filename=f'img/champ/{champ}.png')
    else:
        champ_img = Image.open(f'img/champ/{champ}.png')

        if darker:
            enhancer = ImageEnhance.Brightness(champ_img)
            champ_img = enhancer.enhance(0.25)

        if border:
            drawer = ImageDraw.Draw(champ_img)
            drawer.rectangle((0,0,champ_img.size[0],champ_img.size[1]), outline=(246,213,92), width=5) # Custom yellow
        
        buf = io.BytesIO()
        champ_img.save(buf, format='PNG')
        window[champ].update(image_data=buf.getvalue())
    return window

def recommand_deck(deck_list, champ_dict, sel_list=[]):
    sel_champs = list(compress(list(champ_dict.keys()), sel_list))

    for deck_no,deck in enumerate(deck_list):
        deck['point'] = 0
        for sel_champ in sel_champs:
            if champ_dict[sel_champ]['kor'] in deck['fin']:
                deck['point'] += 3
            elif champ_dict[sel_champ]['kor'] in deck['mid']:
                deck['point'] += 2
            elif champ_dict[sel_champ]['kor'] in deck['ini']:
                deck['point'] += 1
    rec_list = sorted(deck_list, key=lambda d: d['point'], reverse=True)
    for i in range(len(rec_list),0,-1):
        if rec_list[i-1]['point'] == 0:
            del rec_list[i-1]           
    return rec_list

def select_deck(window, options, deck_list, rec_list=[], sel_rec='0'):
    # 추천덱 버튼 업데이트
    for rec_no in range(options['max_recommandation']):
        if rec_no<len(rec_list) and rec_no == int(sel_rec):
            window['rec'+str(rec_no)].update(rec_list[rec_no]['name'])
            window['rec'+str(rec_no)].update(button_color=('black','#F6D55C'))
            window['rec'+str(rec_no)].update(visible=True)
        elif rec_no<len(rec_list):
            window['rec'+str(rec_no)].update(rec_list[rec_no]['name'])
            window['rec'+str(rec_no)].update(button_color=('white','#283B5B'))
            window['rec'+str(rec_no)].update(visible=True)
        else:
            window['rec'+str(rec_no)].update('')
            window['rec'+str(rec_no)].update(visible=False)

    window = select_phase(window, deck_list, rec_list, sel_rec=sel_rec)
    return window

def select_phase(window, deck_list, rec_list=[], sel_rec='0', sel_phase='ini'):
    # 선택한 덱 디스플레이
    if len(rec_list) == 0:
        window['deck_viewer'].update(filename=f'img/deck/deck_void.png')
    else:
        for deck_no,deck in enumerate(deck_list):
            if deck['name'] == rec_list[int(sel_rec)]['name']:
                window['deck_viewer'].update(filename=f'img/deck/deck{deck_no}_{sel_phase}.png')
                # print('파일명:'+f'img/deck/deck{deck_no}_{sel_phase}.png')

    # Phase 버튼 업데이트
    if rec_list == []:
        window['phase_ini'].update(disabled=True)
        window['phase_ini'].update(button_color=('white','#283B5B'))
        window['phase_mid'].update(disabled=True)
        window['phase_fin'].update(disabled=True)
    else:
        window['phase_ini'].update(disabled=False)
        window['phase_ini'].update(button_color=('white','#283B5B'))
        window['phase_mid'].update(disabled=False)
        window['phase_mid'].update(button_color=('white','#283B5B'))
        window['phase_fin'].update(disabled=False)
        window['phase_fin'].update(button_color=('white','#283B5B'))
        window[f'phase_{sel_phase}'].update(button_color=('white','#3CAEA3'))
    return window

def run_gui():
    options = yaml.load(open('yaml/options.yaml'), Loader=yaml.FullLoader)
    deck_list = update_db(do=options['update_on_start'])
    if deck_list is None:
        return None

    champ_dict = yaml.load(open('yaml/champ_season9.yaml',encoding='UTF-8'), Loader=yaml.FullLoader)
    champ_keys = list(champ_dict.keys())
    sel_list = [False]*len(champ_keys)
    origin_list = []
    for champ in champ_dict:
        origin_list = origin_list + champ_dict[champ]['origin_kor'].split(',')
    origin_list = list(set(origin_list))

    ####### Layout Setting ######
    layout = []
    row = [[],[],[],[],[],[],[],[],[],[]]
    row[0].append(sg.Button(button_text='선택 초기화',key='Refresh'))
    row[0].append(sg.Text('',expand_x=True,background_color='#222222'))
    row[0].append(sg.Button(button_text='데이터베이스 업데이트',key='UpdateDB'))
    for i in range(1,6):
        row[i].append(sg.Image(filename=f'img/icon/coin{i}.png',background_color='#222222'))
    for champ in champ_keys:
        row[champ_dict[champ]['cost']].append(sg.Button(
                key=champ,
                image_filename=f"img/champ/{champ}.png",
                tooltip=champ_dict[champ]['kor'],
                right_click_menu=['', champ_dict[champ]['origin_kor'].split(',')]))
    
    rec_row = [sg.Text('',background_color=('#111111'))]
    for rec in range(options['max_recommandation']):
        rec_row.append(sg.Button(button_text='', key=f'rec{rec}', visible=False))
    row[6]=[sg.Column(
        [rec_row],
        key='rec_col',
        background_color='#111111',
        expand_x=True,
        pad=(None,20),
        scrollable=True,
        size=(None,35),
        sbar_trough_color = '#222222',
        sbar_background_color = '#111111',
        sbar_arrow_color = '#283B5B')]

    phase_row = [[sg.Button(button_text='초반', key=f'phase_ini', disabled=True, expand_y=True)],
                [sg.Button(button_text='중반', key=f'phase_mid', disabled=True, expand_y=True)],
                [sg.Button(button_text='최종', key=f'phase_fin', disabled=True, expand_y=True)]]
    origin_sum = [[sg.Text('wow')],[sg.Text('wow2')],]
    deck_row = [[sg.Image(
        key='deck_viewer',
        filename='img/deck/deck_void.png')]]
    
    row[7]=[sg.Column(phase_row, background_color='#222222', expand_y=True, expand_x=True, justification='left'),
            # sg.Column(origin_sum, background_color='#111111', expand_y=True),
            sg.Column(deck_row, background_color='#222222', expand_x=True)]
    row[8]=[sg.Text('Developed by JHR', expand_x=True, justification='right',background_color='#222222',text_color='#111111')]
    layout.append(row)
    
    ####### GUI Running ######
    window = sg.Window('Chess Advisor', layout, background_color='#222222', finalize=True)
    current_origin = None
    while True:
        event, values = window.Read()
        
        if event == sg.WIN_CLOSED:
            break

        print('Event was : ' + event)

        if event == 'Refresh':
            for idx, champ in enumerate(champ_keys):
                window = update_champ_btn(window, champ)
                sel_list[idx] = False
            window = select_deck(window, options, deck_list)
            current_origin = None
            window.refresh()

        elif event == 'UpdateDB':
            choice = sg.popup_ok_cancel('데이터 베이스를 지금 업데이트 하시겠습니까?', '수 분 정도 시간이 소요될 수 있습니다.',title='경고')
            if choice == 'OK':
                deck_list = update_db(do=True)

        elif event in champ_keys: # 챔피언 클릭 시
            champ = event
            idx = champ_keys.index(champ)
            if sel_list[idx]: # 선택된 챔피언 -> 챔피언 선택 해제
                # print(f"You deselected {champ_dict[champ]['kor']}.")
                if current_origin is None:# 선택된 특성 없음 -> 원본+테두리 출력
                    window = update_champ_btn(window, champ)
                elif current_origin in champ_dict[champ]['origin_kor'].split(','): # 선택된 특성 -> 원본 출력
                    window = update_champ_btn(window, champ)
                else: # 미선택된 특성 -> 어둡게 출력 ???
                    window = update_champ_btn(window, champ, darker=True)
                    
            else: # 미선택된 챔피언 -> 챔피언 선택
                # print(f"You selected {champ_dict[event]['kor']}.")
                if current_origin is None:# 선택된 특성 없음 -> 원본+테두리 출력
                    window = update_champ_btn(window, champ, border=True)
                elif current_origin in champ_dict[event]['origin_kor'].split(','): # 선택된 특성 -> 원본+테두리 출력
                    window = update_champ_btn(window, champ, border=True)
                else: # 미선택된 특성 -> 어둡게+테두리 출력
                    window = update_champ_btn(window, champ, darker=True, border=True)
            sel_list[idx] = not sel_list[idx]
            rec_list = recommand_deck(deck_list, champ_dict, sel_list)
            window = select_deck(window, options, deck_list, rec_list)
            window.refresh()
            window['rec_col'].contents_changed()

        elif event == current_origin: # 이미 선택되어 있는 특성 재클릭 시 -> 특성 선택 해제
            # print(f"You deselected {event}.")
            for idx, champ in enumerate(champ_keys):
                if sel_list[idx]: # 선택된 챔피언 -> 원본+테두리 출력
                    window = update_champ_btn(window, champ, border=True)
                else: # 미선택된 챔피언 -> 원본 출력
                    window = update_champ_btn(window, champ)
            current_origin = None
            window.refresh()
            
        elif event in origin_list: # 새로운 특성 클릭 시 -> 특성 선택
            # print(f"You selected {event}.")
            for idx, champ in enumerate(champ_keys):
                if event in champ_dict[champ]['origin_kor'].split(','): # 특성에 해당될 시
                    if sel_list[idx]: # 선택된 챔피언 -> 원본+테두리 출력
                        window = update_champ_btn(window, champ, border=True)
                    else: # 미선택된 챔피언 -> 원본 출력
                        window = update_champ_btn(window, champ)                    
                else: # 특성에 미해당될 시
                    if sel_list[idx]: # 선택된 챔피언 -> 어둡게+테두리 출력
                        window = update_champ_btn(window, champ, darker=True, border=True)
                    else: # 미선택된 챔피언 -> 어둡게 출력
                        window = update_champ_btn(window, champ, darker=True)
            current_origin = event
            window.refresh()

        elif 'rec' in event:
            window = select_deck(window, options, deck_list, rec_list, sel_rec=event[3:])
            window.refresh()
            window['rec_col'].contents_changed()

        elif 'phase' in event:
            window = select_phase(window, deck_list, rec_list, sel_phase=event[-3:])
            window.refresh()

        else:
            pass

    window.close()

### MAIN FUNCTION ###
if __name__ == "__main__":
    run_gui()