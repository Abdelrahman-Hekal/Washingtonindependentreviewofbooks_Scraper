from selenium import webdriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait as wait
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service as ChromeService 
import pandas as pd
import time
import csv
import sys
import numpy as np
import calendar

def initialize_bot():

    # Setting up chrome driver for the bot
    chrome_options  = webdriver.ChromeOptions()
    # suppressing output messages from the driver
    chrome_options.add_argument('--log-level=3')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--disable-extensions')
    chrome_options.add_argument('--window-size=1920,1080')
    # adding user agents
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36")
    chrome_options.add_argument("--incognito")
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
    # running the driver with no browser window
    chrome_options.add_argument('--headless')
    # disabling images rendering 
    prefs = {"profile.managed_default_content_settings.images": 2}
    chrome_options.add_experimental_option("prefs", prefs)
    chrome_options.page_load_strategy = 'normal'
    # installing the chrome driver
    driver_path = ChromeDriverManager().install()
    chrome_service = ChromeService(driver_path)
    # configuring the driver
    driver = webdriver.Chrome(options=chrome_options, service=chrome_service)
    driver.set_page_load_timeout(10000)
    driver.maximize_window()

    return driver

def scrape_washingtonindependentreviewofbooks(path):

    start = time.time()
    print('-'*75)
    print('Scraping washingtonindependentreviewofbooks.com ...')
    print('-'*75)
    # initialize the web driver
    driver = initialize_bot()

    # initializing the dataframe
    data = pd.DataFrame()

    # if no books links provided then get the links
    if path == '':
        name = 'washingtonindependentreviewofbooks_data.xlsx'
        # getting the books under each category
        links, pages = [], {}   
        homepage = "https://www.washingtonindependentreviewofbooks.com/bookreview"

        skip = ["Art & Architecture", "Computers & Technology", "Cooking & Food", "Performing Arts & Entertainment", "Sports & Games"]
        nbooks = 0
        driver.get(homepage)
        p = wait(driver, 2).until(EC.presence_of_element_located((By.CSS_SELECTOR, "p.categories")))
        tags = wait(p, 2).until(EC.presence_of_all_elements_located((By.TAG_NAME, "a")))
        for tag in tags:
            cat = tag.get_attribute('textContent')
            if cat in skip: 
                continue
            url = tag.get_attribute('href')
            #print(f'Getting the link for category: {cat}')
            pages[cat] = url

        for cat in pages:
            driver.get(pages[cat])
            print('-'*75)
            print(f'Getting the full titles list under category: {cat}')

            #handling lazy loading
            while True:
                try:
                    button = wait(driver, 2).until(EC.presence_of_element_located((By.CSS_SELECTOR, "a.load-button")))
                    driver.execute_script("arguments[0].click();", button)
                    time.sleep(2)
                except:
                    break

            # scraping books urls
            titles = wait(driver, 20).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "section[class='media-item is-one-column']")))

            for title in titles:
                try:                                  
                    div = wait(title, 2).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.media-description-title")))
                    link = wait(div, 2).until(EC.presence_of_element_located((By.TAG_NAME, "a"))).get_attribute('href')
                    links.append(link)
                    nbooks += 1 
                    print(f'Scraping the url for title  {nbooks}')
                except Exception as err:
                    pass
                    
        # saving the links to a csv file
        print('-'*75)
        print('Exporting links to a csv file ....')
        with open('washingtonindependentreviewofbooks_links.csv', 'w', newline='\n', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Link'])
            for row in links:
                writer.writerow([row])

    scraped = []
    if path != '':
        df_links = pd.read_csv(path)
        name = path.split('\\')[-1][:-4]
        name = name + '_data.xlsx'
    else:
        df_links = pd.read_csv('washingtonindependentreviewofbooks_links.csv')

    links = df_links['Link'].values.tolist()

    try:
        data = pd.read_excel(name)
        scraped = data['Title Link'].values.tolist()
    except:
        pass

    # scraping books details
    print('-'*75)
    print('Scraping Books Info...')
    print('-'*75)
    n = len(links)
    for i, link in enumerate(links):
        try:
            if link in scraped: continue
            driver.get(link)           
            details = {}
            print(f'Scraping the info for book {i+1}\{n}')            
            # title and title link
            title_link, title = '', ''              
            try:
                title_link = link
                title = wait(driver, 2).until(EC.presence_of_element_located((By.TAG_NAME, "h1"))).get_attribute('textContent').replace('\n', '').strip().title() 
            except:
                print(f'Warning: failed to scrape the title for book: {link}')               
                
            details['Title'] = title
            details['Title Link'] = title_link                          
            # Author, publisher and pages count
            details['Author'] = ''
            details['Publisher'] = ''
            details['Page Count'] = ''
            try:
                ul = wait(driver, 2).until(EC.presence_of_element_located((By.CSS_SELECTOR, "ul.book-info")))
                lis = wait(ul, 2).until(EC.presence_of_all_elements_located((By.TAG_NAME, "li")))
                m = len(lis)
                if m > 0:
                    details['Author'] = lis[0].get_attribute('textContent').replace('By ', '').strip()   
                if m > 1:
                    details['Publisher'] = lis[1].get_attribute('textContent').strip()  
                if m > 2:
                    details['Page Count'] = lis[2].get_attribute('textContent').strip().split(' ')[0]        
            except:
                pass
             
            # reviewer
            reviewer = ''
            try:
                reviewer = wait(driver, 2).until(EC.presence_of_element_located((By.CSS_SELECTOR, "li.reviewed-by"))).get_attribute('textContent').replace('\n', '').replace('Reviewed by', '').strip()
            except:
                 div = wait(driver, 2).until(EC.presence_of_element_located((By.XPATH, "//div[@id='single-page-full-content']")))
                 tags = wait(div, 2).until(EC.presence_of_all_elements_located((By.TAG_NAME, "p")))
                 for tag in tags:
                     text = tag.get_attribute('textContent')
                     if 'Reviewed by' in text:
                        reviewer = text.replace('\n', '').replace('Reviewed by', '').strip()
                        break

            details['Reviewer'] = reviewer         
         
            # reviewing date
            date = ''
            try:
                ul = wait(driver, 2).until(EC.presence_of_element_located((By.CSS_SELECTOR, "ul.reviewer")))
                lis = wait(ul, 2).until(EC.presence_of_all_elements_located((By.TAG_NAME, "li")))
                if len(lis) > 1:
                    date = lis[1].get_attribute('textContent').replace('\n', '').strip()
                else:
                    text = lis[0].get_attribute('textContent').replace('\n', '').strip()
                    for month in calendar.month_name:
                        if month in text:
                            date = text
                            break
            except:
                 pass
             
            details['Reviewe Date'] = date
            
            # Amazon link
            Amazon = ''
            try:
                div = wait(driver, 2).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.entry-affiliate-links")))
                Amazon = wait(div, 2).until(EC.presence_of_element_located((By.TAG_NAME, "a"))).get_attribute('href')
                if 'www.amazon' not in Amazon:
                    Amazon = ''
                details['Amazon Link'] = Amazon
            except:
                pass

            details['Amazon Link'] = Amazon

            # appending the output to the datafame       
            data = data.append([details.copy()])
            # saving data to csv file each 100 links
            if np.mod(i+1, 100) == 0:
                print('Outputting scraped data ...')
                data.to_excel(name, index=False)
        except Exception as err:
            print(str(err))
            driver.quit()
            driver = initialize_bot()

    # optional output to excel
    data.to_excel(name, index=False)
    elapsed = round((time.time() - start)/60, 2)
    print('-'*75)
    print(f'washingtonindependentreviewofbooks.com scraping process completed successfully! Elapsed time {elapsed} mins')
    print('-'*75)
    driver.quit()

    return data

if __name__ == "__main__":
    
    path = ''
    if len(sys.argv) == 2:
        path = sys.argv[1]
    data = scrape_washingtonindependentreviewofbooks(path)

