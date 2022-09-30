import time
import requests
import pandas as pd
from selenium import webdriver
from bs4 import BeautifulSoup
from selenium.webdriver.firefox.service import Service as FirefoxService
from webdriver_manager.firefox import GeckoDriverManager
import nltk
from nltk import sent_tokenize, word_tokenize


class ScrapeData:

    def __init__(self, driver):
        self.driver = driver

    """
    input is url of graduation_data
    returns a Pandas df
    """
    def get_graduation_data(self, url):
        print(url)
        response = requests.get(url)
        graduation_data = response.json()["data"]
        return pd.DataFrame(graduation_data)

    """
    input is university name, and url to get enrollment data
    returns a Pandas df

    Since the dataset also contains average data of all universities,
    have to check if university name matches to only return university 
    data
    """
    def get_enrollment_data(self, university_name, url):
        response = requests.get(url)
        enrollment_data = response.json()["data"]
        enrollment_data_full = pd.DataFrame(enrollment_data)
        return enrollment_data_full[enrollment_data_full["University"] == university_name]

    """
    input: university name in url form of DataUSA format
    returns the state of the university in ZIP Code abbreviation
    State information is in the about paragraph, first sentence, last word.
    """
    def get_university_state(self, university_url):
        self.driver.get(f'https://datausa.io/profile/university/{university_url}')
        html = self.driver.page_source
        soup = BeautifulSoup(html, features="html.parser")
        all_paragraphs = soup.find_all("p")
        about_paragraph = all_paragraphs[2].text.strip()
        sentences_about_paragraph = sent_tokenize(about_paragraph)
        words_in_first_sentence = word_tokenize(sentences_about_paragraph[0])
        #-2 because the last character is a period
        return words_in_first_sentence[len(words_in_first_sentence) - 2]

    """
    returns a set with all of the university ids. 
    It is a set because all_university_data contains duplicates of the universities
    """
    def get_university_ids(self):
        ids = set()
        response = requests.get("https://datausa.io/api/data?Geography=04000US00&measures=Completions&drilldowns=Sector,University")
        all_universities_data = response.json()["data"]
        for university_data in all_universities_data:
            ids.add(university_data["ID University"])
        return ids

    """
    Main logic of scraping and combining data
    Creates two csv files in same directory
    """
    def get_data(self):
        university_ids = self.get_university_ids()
        combined_enrollment_df = None
        combined_graduation_df = None
        for id in university_ids:
            time.sleep(0.25)
            graduation_data_df = self.get_graduation_data(f"https://preview.datausa.io/api/data?University={id}&measures=Graduation Rate,Number Of Finishers&drilldowns=Gender,IPEDS Race&Number Of Finishers>=5")
            try:
                university_url = graduation_data_df.iloc[0]['Slug University']
                state = self.get_university_state(university_url)
                university_name = graduation_data_df.iloc[0]['University']
                state_array = [state]*len(graduation_data_df)
                graduation_data_df["Location"] = state_array

                enrollment_data_df = self.get_enrollment_data(university_name, f"https://preview.datausa.io/api/data?University={id},{id}:parents&measures=Enrollment&drilldowns=IPEDS%20Race")
                state_array = [state]*len(enrollment_data_df)
                enrollment_data_df["Location"] = state_array

                if graduation_data_df is None:
                    combined_graduation_df = graduation_data_df
                else:
                    combined_graduation_df = pd.concat([combined_graduation_df, graduation_data_df], axis=0)
                
                if combined_enrollment_df is None:
                    combined_enrollment_df = enrollment_data_df
                else:
                    combined_enrollment_df = pd.concat([combined_enrollment_df, enrollment_data_df], axis=0)
            except:
                print("No Information Found")
        
        combined_enrollment_df.to_csv("enrollment_data.csv")
        combined_graduation_df.to_csv("graduation_data.csv")




if __name__ == "__main__":
    driver = webdriver.Firefox(executable_path="geckodriver.exe")
    data_scraping = ScrapeData(driver)
    data_scraping.get_data()

