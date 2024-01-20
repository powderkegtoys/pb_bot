from selenium import webdriver
from time import sleep
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.keys import Keys
import datetime
import requests
from bs4 import BeautifulSoup
from requests.structures import CaseInsensitiveDict
import json
from cryptography.fernet import Fernet
import sys
import os

class Tamashii:
    def __init__(self, driver, key_file = 'tamashii.key', setting = 'tamashii.json', path = ''):
        self.__runable = True
        self.__header = CaseInsensitiveDict()
        self.set_file_path(path)
        self.get_key(key_file)
        self.load_setting(setting)
        self.load_driver(driver)
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        self.__driver.quit()

    def set_file_path(self, path):
        self.__path = path

    def get_key(self, key_file):
        if os.path.exists(self.__path + key_file):
            with open(key_file, 'rb') as f:
                key = f.read()
            self.__fernet = Fernet(key)
        else:
            self.__runable = False
            print('Key Not Found!!')

    def load_setting(self, setting):
        if os.path.exists(self.__path + setting):
            with open(setting, 'r') as f:
                tamashii = json.load(f)
            self.__name = tamashii['name']
            self.__pwd = self.__fernet.decrypt(tamashii['pwd'].encode()).decode()
            self.__cart_url = 'https://p-bandai.com/tw/cart/add'
            self.__goods = tamashii['goods']
            self.__sale_mon = int(tamashii['mon'])
            self.__sale_day = int(tamashii['day'])
            self.__sale_hour = int(tamashii['hour'])
            self.__sale_min = int(tamashii['min'])
            self.__sale_sec = int(tamashii['sec'])
            self.__period = float(tamashii['period'])
            self.__countdown_hour = int(tamashii['countdown_hour'])
            self.__countdown_min = int(tamashii['countdown_min'])
            self.__countdown_sec = int(tamashii['countdown_sec'])
            self.__refresh_min = int(tamashii['refresh_min'])
            self.__end_min = int(tamashii['end_min'])
            self.__end_sec = int(tamashii['end_sec'])
            self.__times = int(tamashii['times'])
            self.__csrf = None
        else:
            self.__runable = False
            print('Setting Not Found!!')

    def load_driver(self, driver):
        self.__driver = driver

    def is_runable(self):
        return self.__runable

    def go_shopping(self):
        now = datetime.datetime.now()
        before15min = now.replace(month=self.__sale_mon, day=self.__sale_day, hour=self.__countdown_hour , minute=self.__countdown_min - 15, second=0, microsecond=0)
        while True:
            now = datetime.datetime.now()
            print(now)
            if now > before15min:
                break
            else:
                sleep(60)
        self.login()
        self.get_header()
        for i in range(self.__times):
            self.add_cart_by_post()
            #超商付款
            self.confirm_order()
            self.place_order()
            #信用卡付款
            #self.confirm_order_by_card()
            #self.place_order_by_card()
            try:
                WebDriverWait(self.__driver, 15).until(EC.text_to_be_present_in_element((By.ID, "o-content"), '感謝您的訂購。'))
                print(self.__driver.find_element_by_css_selector('#o-content > div > main > section > div.a-box.o-complete.o-complete__type2 > h2 > span').text)
            except TimeoutException:
                print('訂購尚未完成')
                self.__driver.refresh()
                sleep(20)

            self.__driver.execute_script("window.open('https://p-bandai.com/tw/mypage')")
            self.__driver.switch_to.window(self.__driver.window_handles[-1])
        print('購物完成! 視窗1分後關閉')
        sleep(60)

    def login(self):
        while True:
            self.__driver.get('https://p-bandai.com/tw')
            try:
                cookie_btn = WebDriverWait(self.__driver, 3).until(
                    EC.element_to_be_clickable((By.ID, "onetrust-pc-btn-handler"))
                )
                cookie_btn.click()
                confirm_btn = self.__driver.find_element_by_css_selector('#onetrust-pc-sdk > div.ot-pc-footer > div.ot-btn-container > button')
                confirm_btn.click()
                print('Close Cookie Windows')
                break
            except Exception as e:
                print(e)
        #login
        print('進行登入')
        while True:
            try:
                self.__driver.get('https://p-bandai.com/tw/login')
                headers = {
                    'accept': 'text/html,application/xhtml+xml,application/xml',
                    'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36'
                }
                s = requests.session()
                s.headers.update(headers)
                for cookie in self.__driver.get_cookies():
                    s.cookies.set(cookie['name'], cookie['value'])
                response = s.get('https://p-bandai.com/tw/login')
                elements = BeautifulSoup(response.text, 'html.parser')
                for i in elements.find_all('input'):
                    if i['name'] == 'CSRFToken':
                        self.__csrf = i['value']
                        print('Retrieve CSRF_Token:', self.__csrf)
                        break
                username = self.__driver.find_element_by_css_selector('#j_username')
                username.send_keys(self.__name)
                passwd = self.__driver.find_element_by_css_selector('#j_password')
                passwd.send_keys(self.__pwd)
                self.__driver.find_element_by_css_selector('#login > a').click()
                WebDriverWait(self.__driver, 5).until(EC.url_contains('https://p-bandai.com/tw'))
                break;
            except TimeoutException:
                    print('Login Timeout: Retry...')
                    self.__driver.refresh()
            except Exception as e:
                pass

    def search_list(self, cookies, name):
        return next((item for item in cookies if item['name'] == name))

    def get_header(self):
        #reference: https://reqbin.com/req/python/c-1n4ljxb9/curl-get-request-example
        headers = CaseInsensitiveDict()
        headers["Connection"] = "keep-alive"
        headers["sec-ch-ua"] = "\"Chromium\";v=\"96\", \"Google Chrome\";v=\"96\", \";Not A Brand\";v=\"99\""
        headers["Accept"] = "*/*"
        headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"
        headers["X-Requested-With"] = "XMLHttpRequest"
        headers["sec-ch-ua-mobile"] = "?0"
        headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.54 Safari/537.36"
        headers["sec-ch-ua-platform"] = "\"Windows\""
        headers["Origin"] = "https://p-bandai.com"
        headers["Sec-Fetch-Site"] = "same-origin"
        headers["Sec-Fetch-Mode"] = "cors"
        headers["Sec-Fetch-Dest"] = "empty"
        headers["Accept-Language"] = "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7"
        my_cookies = self.__driver.get_cookies()
        #print(my_cookies)
        template = "OptanonAlertBoxClosed=2021-12-01T06:07:39.512Z; OptanonConsent=123; JSESSIONID=90702EF77EA604373112A61983D2E65C; defaultSite=tw; recommendUser=36ZK1xLFyR54ndh6iwL1balchlLsetewo1sxw0LfPEsyWXnzcN; _gcl_au=1.1.1667031027.1632533397; _gid=GA1.2.971753289.1632533398; __lt__cid=52f8c033-6f0f-4f4c-abb5-4dc760ecc882; __lt__sid=36ba54e3-1b26f710; __BWfp=c1632533398502x92af309ed; FPLC=BMZj%2FKUSgZj5QOVH6wtAtoLl2bwsh5b9vIRU8A%2FTk5yJzGCJYESJNIiTQp9o42GPUj6E9VLjE%2Fo5vA2n46APhwMB30fAqKMirMvxvreaTKkDE3w7wFCvb0qeGUB36w%3D%3D; FPID=FPID2.2.wSFcER7NPaz8axcOgcYoazCO1NJ%2FGrp%2BX%2BEd0YipOIk%3D.1632533398; __ulfpc=202109250929587450; _fbp=fb.1.1632533398930.320807006; krt.vis=ca361080-0fc0-48e7-984d-909e75848e20; acceleratorSecureGUID=33fca52db86579a319012dc1702a32f532daa587; krt.context=session%3Acd9e4216-e33a-4b56-8d57-f87eca3d712b%3Bcontext_mode%3Afocusing; krt.v=message%3A5f2cfc26ead48f00112632ec%7C602099d8560ede00111f5f2e%7C5cca92b6ea3713097207ff26; AWSALB=wZpWetEy+/r3HRfRX05rvpMOBMc7fSQpLPmcgXFNgxTPztLCkCwiiUGtCrkFGRDZ9iX5fqXXRDzmnIq4BgqQH7FZXbzE4UD7cAsWeWL4NbJ+Q2ZuGOZ8mnzExAhC; AWSALBCORS=wZpWetEy+/r3HRfRX05rvpMOBMc7fSQpLPmcgXFNgxTPztLCkCwiiUGtCrkFGRDZ9iX5fqXXRDzmnIq4BgqQH7FZXbzE4UD7cAsWeWL4NbJ+Q2ZuGOZ8mnzExAhC; _ga=GA1.2.2130423123.1632533398; _uetsid=19d3b7801da011ec814d6379c879047f; _uetvid=19d3f8401da011ec986eab0df9af9e34; _ga_67MWHF65HK=GS1.1.1632533396.1.1.1632534272.55"
        my_list = template.split('; ')
        for i,item in enumerate(my_list):
            try:
                d = self.search_list(my_cookies, item[:item.index('=')])
                if not d:
                    print('%s is not found in the my_cookies' % item[:item.index('=')])
                my_list[i] = item[:item.index('=')] + '=' + d['value']
            except Exception as e:
                print('Exception Occurs:', e)
                exit()
        custom_cookies = '; '.join(my_list)
        headers["Cookie"] = custom_cookies
        self.__header = headers

    def add_cart_by_post(self):
        now = datetime.datetime.now()
        before_xx_min = now.replace(month=self.__sale_mon, day=self.__sale_day, hour=self.__countdown_hour, minute=self.__refresh_min, second=0, microsecond=0)
        before_xx_sec = now.replace(month=self.__sale_mon, day=self.__sale_day, hour=self.__countdown_hour, minute=self.__countdown_min, second=self.__countdown_sec, microsecond=0)
        after_xx_sec = now.replace(month=self.__sale_mon, day=self.__sale_day, hour=self.__sale_hour , minute=self.__sale_min + self.__end_min, second=self.__end_sec, microsecond=0)
        while True:
            now = datetime.datetime.now()
            print('現在時間 ', now.time())
            if now < before_xx_min:
                print('5分後刷新網頁...')
                sleep(300)
                self.__driver.refresh()
            elif now > before_xx_sec:
                print('開賣時間倒數，開始放商品進購物車')
                break
            sleep(2)
        for i in self.__goods:
            target = i['item']
            prod_code = target.split('/')[-1][:-6] + target.split('/')[-1][-3:]
            qty = i['qty']
            self.__header["Referer"] = target
            data = "productCodePost={}&qty={}&CSRFToken={}".format(prod_code, qty, self.__csrf)
            while True:
                resp = requests.post(self.__cart_url, headers=self.__header, data=data)
                if resp.status_code == 200:
                    try:
                        d = json.loads(resp.text)
                        if d['cartAnalyticsData']['cartCode']:
                            print(resp.text)
                            print('添加購物車成功!!')
                            break
                        else:
                            #print(resp.text)
                            print(now)
                            print('還無法放入購物車', resp.status_code)
                    except:
                        print('json load fail!!', resp.text)
                else:
                    print(resp.text)
                    print(now)
                    print('還無法放入購物車', resp.status_code)
                sleep(self.__period)
                now = datetime.datetime.now()
                if now > after_xx_sec:
                    print('Add cart Expired')
                    exit()
    #速度太慢，搶不贏其它bot
    def add_cart_by_click(self):
        self.__driver.get(target)
        while True:
            try:
                select = Select(self.__driver.find_element_by_id('sc_p07_01_purchaseNumber'))
                select.select_by_value(qty)

                self.__driver.find_element_by_id('addToCartButton').click()
                print('button is clickable!')
                break
            except Exception as e:
                now = time.strftime('%H:%M:%S')
                print('%s: wait button' % now)
                self.__driver.refresh()

    def confirm_order(self):
        while True:
            try:
                print('開始進入「輸入訂購資訊」頁面')
                self.__driver.get('https://p-bandai.com/tw/checkout/orderinformation')
                WebDriverWait(self.__driver, 3).until(
                    EC.element_to_be_clickable((By.ID, "confirmOrderInfo"))
                )
                break
            except TimeoutException:
                try:
                    print('Timeout: handle preconfirm')
                    self.__driver.get('https://p-bandai.com/tw/cart')
                    preconfirm_btn = self.__driver.find_element_by_css_selector('#o-content > div > main > section > section.o-section.u-sm-mb48 > div > div.o-cart__item.o-cart__foot.o-cart--xs-3 > div > div.m-cart--foot__fee__btn > a > span')
                    if preconfirm_btn:
                        preconfirm_btn.click()
                        break
                except:
                    pass
                continue
            except Exception as e:
                print(repr(e))
                self.__driver.refresh()
                print('Exception: handle preconfirm')
                try:
                    preconfirm_btn = self.__driver.find_element_by_css_selector('#o-content > div > main > section > section.o-section.u-sm-mb48 > div > div.o-cart__item.o-cart__foot.o-cart--xs-3 > div > div.m-cart--foot__fee__btn > a > span')
                    if preconfirm_btn:
                        preconfirm_btn.click()
                        break
                except:
                    pass

        while True:
            try:
                print('進行勾選並點選確認')
                self.__driver.find_element_by_css_selector('#pBOrderInfoForm > section.u-sm-mb48.u-xs-mb16 > div > div > section > div:nth-child(12) > div > div.m-table__td.js-radio-group > div:nth-child(3) > label').click()
                self.__driver.find_element_by_css_selector('#pBOrderInfoForm > section.u-sm-mb48.u-xs-mb16 > div > div > section > section.o-section.o-section--order.o-section--uniform > div > div:nth-child(1) > div.m-table__td > div.js-radio-group > div > label:nth-child(1)').click()
                self.__driver.find_element_by_css_selector('#pBOrderInfoForm > section.u-sm-mb48.u-xs-mb16 > div > div > section > section.o-section.o-section--order.o-section--uniform > div > div:nth-child(1) > div.m-table__td > div.a-xs-text-14.u-sm-mt20.u-xs-mt16 > label').click()
                self.__driver.find_element_by_css_selector('#confirmOrderInfo').click()
                WebDriverWait(self.__driver, 5).until(
                    EC.element_to_be_clickable((By.ID, "orderInfoConfirmBtn"))
                )
                break
            except TimeoutException:
                continue
            except Exception as e:
                print(repr(e))
                self.__driver.refresh()

    def confirm_order_by_card(self):
        while True:
            try:
                print('開始進入「輸入訂購資訊」頁面')
                self.__driver.get('https://p-bandai.com/tw/checkout/orderinformation')
                WebDriverWait(self.__driver, 3).until(
                    EC.element_to_be_clickable((By.ID, "confirmOrderInfo"))
                )
                break
            except TimeoutException:
                try:
                    print('Timeout: handle preconfirm')
                    self.__driver.get('https://p-bandai.com/tw/cart')
                    preconfirm_btn = self.__driver.find_element_by_css_selector('#o-content > div > main > section > section.o-section.u-sm-mb48 > div > div.o-cart__item.o-cart__foot.o-cart--xs-3 > div > div.m-cart--foot__fee__btn > a > span')
                    if preconfirm_btn:
                        preconfirm_btn.click()
                        break
                except:
                    pass
                continue
            except Exception as e:
                print(repr(e))
                self.__driver.refresh()
                print('Exception: handle preconfirm')
                try:
                    preconfirm_btn = self.__driver.find_element_by_css_selector('#o-content > div > main > section > section.o-section.u-sm-mb48 > div > div.o-cart__item.o-cart__foot.o-cart--xs-3 > div > div.m-cart--foot__fee__btn > a > span')
                    if preconfirm_btn:
                        preconfirm_btn.click()
                        break
                except:
                    pass
        while True:
            try:
                print('進行勾選並點選確認')
                self.__driver.find_element_by_css_selector('#pBOrderInfoForm > section.u-sm-mb48.u-xs-mb16 > div > div > section > div:nth-child(12) > div > div.m-table__td.js-radio-group > div:nth-child(1) > label > span.a-input-radio__label').click()
                self.__driver.find_element_by_css_selector('#pBOrderInfoForm > section.u-sm-mb48.u-xs-mb16 > div > div > section > section.o-section.o-section--order.o-section--uniform > div > div:nth-child(1) > div.m-table__td > div.js-radio-group > div > label:nth-child(1)').click()
                self.__driver.find_element_by_css_selector('#pBOrderInfoForm > section.u-sm-mb48.u-xs-mb16 > div > div > section > section.o-section.o-section--order.o-section--uniform > div > div:nth-child(1) > div.m-table__td > div.a-xs-text-14.u-sm-mt20.u-xs-mt16 > label').click()
                self.__driver.find_element_by_css_selector('#confirmOrderInfo').click()
                WebDriverWait(self.__driver, 5).until(
                    EC.element_to_be_clickable((By.ID, "orderInfoConfirmBtn"))
                )
                break
            except TimeoutException:
                continue
            except Exception as e:
                print(repr(e))
                self.__driver.refresh()
    def place_order(self):
        while True:
            try:
                print('進行「確認訂單詳情」')
                self.__driver.find_element_by_css_selector('#placeOrderForm > section.o-section.a-box.o-agree.u-sm-mb80.u-xs-mb60 > div > label').click()
                self.__driver.find_element_by_css_selector('#orderInfoConfirmBtn').click()
                email = WebDriverWait(self.__driver, 10).until(
                    EC.element_to_be_clickable((By.ID, "payer_mail"))
                )
                break
            except TimeoutException:
                self.__driver.refresh()
                sleep(5)
                continue
            except Exception as e:
                print(repr(e))
                self.__driver.refresh()
                sleep(5)

        email.send_keys(self.__name)
        self.__driver.find_element_by_css_selector('#show_pay_footer_m > div > div.nomal_text.qwareOpt > label > input[type=checkbox]').click()
        while True:
            try:
                print('從藍新金流結帳')
                self.__driver.find_element_by_css_selector('#confirm_send_order').click()
                break
            except TimeoutException:
                self.__driver.refresh()
                sleep(8)
            except Exception as e:
                print(repr(e))
                self.__driver.refresh()
                sleep(8)

    def place_order_by_card(self):
        while True:
            try:
                print('進行「確認訂單詳情」')
                self.__driver.find_element_by_css_selector('#placeOrderForm > section.o-section.a-box.o-agree.u-sm-mb80.u-xs-mb60 > div > label').click()
                self.__driver.find_element_by_css_selector('#orderInfoConfirmBtn').click()
                email = WebDriverWait(self.__driver, 10).until(
                    EC.element_to_be_clickable((By.ID, "payer_mail"))
                )
                break
            except TimeoutException:
                continue
            except Exception as e:
                print(repr(e))
                self.__driver.refresh()
        self.__driver.find_element_by_id("card_1").send_keys('')
        self.__driver.find_element_by_id("card_2").send_keys('')
        self.__driver.find_element_by_id("card_3").send_keys('')
        self.__driver.find_element_by_id("card_4").send_keys('')
        self.__driver.find_element_by_xpath("//select[@name='LimitM']/option[text()='']").click()
        self.__driver.find_element_by_xpath("//select[@name='LimitY']/option[text()='']").click()
        self.__driver.find_element_by_name("cvc").send_keys('')
        email.send_keys(self.__name)
        self.__driver.find_element_by_css_selector('#show_pay_footer_m > div > div.nomal_text.qwareOpt > label > input[type=checkbox]').click()
        while True:
            try:
                print('從藍新金流結帳')
                self.__driver.find_element_by_css_selector('#confirm_send_order').click()
                break
            except TimeoutException:
                self.__driver.refresh()
            except Exception as e:
                print(repr(e))
                self.__driver.refresh()
        WebDriverWait(self.__driver, 20).until(
            EC.presence_of_element_located((By.ID, "otpReqForm"))
        )
        self.__driver.find_element_by_css_selector('#otpReqForm > button').click()
def main():
    s = 'tamashii.json'
    if len(sys.argv) == 2 and os.path.isfile(sys.argv[1]):
        s = sys.argv[1]
    option = webdriver.ChromeOptions()
    option.add_argument('--disable-gpu') 
    option.add_argument('--blink-settings=imagesEnabled=false')
    #option.add_argument('--disable-javascript')
    #option.add_argument('--headless') 
    option.add_argument('--log-level=3')
    driver = webdriver.Chrome(chrome_options = option)
    robo = Tamashii(driver, setting = s)
    if robo.is_runable():
        robo.go_shopping()
    else:
        print('cannot run robo')

if __name__ == '__main__':
    main()