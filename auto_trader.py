from selenium import webdriver
from selenium.webdriver.support.wait import WebDriverWait
from bs4 import BeautifulSoup
import time
from datetime import datetime
import pandas as pd
import re
import json

enter_path_of_config_file = r"D:\\python\\lambda\\lambda\\autotrader\\autotrader_config.csv"
json_file_path = r'D:\\python\\lambda\\lambda\\autotrader\\make.json'
fuel_types_list = [
    "Bi Fuel",
    "Diesel",
    "Diesel Hybrid",
    "Diesel Plug-in Hybrid",
    "Electric",
    "Petrol",
    "Petrol Hybrid",
    "Petrol Plug-in Hybrid",
    "Unlisted"
]

def get_total_pages(postcode,make,fuel,year_from,year_to,file,page_start=1):
    # driver = webdriver.Firefox()
    try:
        url="https://www.autotrader.co.uk/car-search"
        page_url = f"{url}?postcode={postcode}&make={make}&fuel-type={fuel}&year-from={year_from}&year-to={year_to}"
        print(page_url)
        driver.get(page_url)
        time.sleep(5)
        page_html = driver.page_source
        soup = BeautifulSoup(page_html, 'html.parser')
        pagination_element = soup.find('p', {'data-testid': 'pagination-show'})
        pagination_text = pagination_element.text.strip()
        match = re.search(r'Page \d+ of (\d+)', pagination_text)
        total_pages=101
        if match:
            total_pages = int(match.group(1))
            total_pages = min(101, total_pages)
        print(f'Total Pages: {total_pages}')    
        
        for page_number in range(page_start, total_pages+1):
            try:
                cars_date=[]
                page_url = f"{url}?page={page_number}&postcode={postcode}&make={make}&fuel-type={fuel}&year-from={year_from}&year-to={year_to}"
                print('Getting data from page:', page_number)
                driver.get(page_url)
                wait.until(lambda driver: "https://www.autotrader.co.uk" in driver.current_url)
                time.sleep(1)
                page_html = driver.page_source
                soup = BeautifulSoup(page_html, 'html.parser') 
                li_elements = soup.select('ul[data-testid="desktop-search"] > li')[1:12]
                for li_element in li_elements:
                   title = get_title(li_element)
                   price_text = get_price(li_element)
                   year, miles, fuel_type = get_other_car_data(li_element)     
                   cars_date.append({"Title":title,"Price":price_text,"Year":year,"Miles":miles,"Fuel_Type":fuel_type})
                save_data(file, cars_date)
            except Exception as e:
                    with open('error_log.txt', 'a') as file:
                        file.write(f"An error occurred: {str(e)}\n")
                        file.write(f"{page_url}\n")              
    except Exception as e:
        print('No data associated with this make and fuel type combination!')
    print('-'*40, '\n')
    return []

def get_make_data(error_make=None):
    
    with open(json_file_path, 'r') as file:
        json_list = json.load(file)
    make_index = next((index for index, entry in enumerate(json_list) if entry['displayName'].lower() == error_make.lower()), None)
    if make_index is not None and make_index < len(json_list) - 1:
        makes_after = [entry['displayName'] for entry in json_list[make_index+1:]]
        return makes_after
    else:    
        return [entry['displayName'] for entry in json_list]
    
def get_other_car_data(li_element):
    ul_ele = li_element.select('ul[data-testid="search-listing-specs"]')
    year=miles=fuel_type="NA"
    if ul_ele:
         for li_ele in ul_ele:
             li_items_sub = li_ele.select('li')
             li_text_combined = ' '.join(li.text for li in li_items_sub)
             pattern = r'(\d+(?:,\d{3})?\s*mile(?:s)?)\s*.*?(\b' + r'\b|\b'.join(map(re.escape, fuel_types_list)) + r'\b)'
             match = re.search(pattern, li_text_combined)
             year=li_items_sub[0].text
             if match:
                miles = match.group(1)
                fuel_type = match.group(2) 
    return year,miles,fuel_type

def get_title(li_element):
    anchor_with_tag_id = li_element.select_one('a[data-testid="search-listing-title"]')
    if anchor_with_tag_id:
         first_h3_child = anchor_with_tag_id.select_one('h3')
         if first_h3_child:
             return first_h3_child.text

def get_price(li_element):
    price = li_element.select_one('span.sc-eulNck')
    if price:
         price_text=price.text
         return price_text.replace("£","")
def get_config(filename):
    df = pd.read_csv(filename)
    file=get_file_name()
    for index, row in df.iterrows():
        postal_code = row['PostalCode']
        page_number = row['PageNumber']
        year_from = int(row['year-from'])
        year_to = int(row['year-to'])
        error_make = row['error_make']
        error_year =row['error_year']
        error_file =row['error_file']
        if pd.notna(error_make) and pd.notna(error_year) and pd.notna(error_file):
            print(f"Both 'error_make' ({error_make}) and 'error_year' ({error_year}) are present.")
            file=error_file
            for fuel_type in fuel_types_list:
                error_year=int(error_year)
                for year in range(error_year, year_to):
                    print(f"{index+1} Processing postcode {postal_code} from page {page_number} with make: {error_make} | fuel type: {fuel_type}")
                    get_total_pages(postal_code,error_make,fuel_type,year,year+1,file,page_number)
            
        
        for make in get_make_data(str(error_make)):
            for fuel_type in fuel_types_list:
                for year in range(year_from, year_to):
                    print(f"Processing postcode {postal_code} from page {page_number} with make: {make} | fuel type: {fuel_type}")
                    get_total_pages(postal_code,make,fuel_type,year,year+1,file,page_number)
    print(f"Excel file '{file}' created successfully.") 

def save_data(file, cars_date):
    try:
     older = pd.read_excel(file)
    except FileNotFoundError:
     older = pd.DataFrame()
    df = pd.DataFrame(cars_date)
    combined_df = pd.concat([older, df])
    df_no_duplicates = combined_df.drop_duplicates(subset=['Title', 'Price', 'Year', 'Miles', 'Fuel_Type'])
    df_no_duplicates.to_excel(file, index=False) 

def get_file_name():
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"autotrader_info_{timestamp}.xlsx"
    return filename
if __name__ == "__main__":
    driver = webdriver.Firefox()
    driver.maximize_window()
    wait = WebDriverWait(driver, 360)
    get_config(enter_path_of_config_file)
    print("DONE!!!!")