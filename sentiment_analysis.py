import requests
from bs4 import BeautifulSoup
import os
import json
from openai import OpenAI

api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    api_key = "sk-proj-Y3C5MXr4YoTAM2CbvL8VT3BlbkFJ40l8EKuejRwGsSJsJmA3"  # Replace with your actual API key if not using environment variable

client = OpenAI(api_key=api_key)

def fetch_news_headlines(url):
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        headlines = []
        
        h3_tags = soup.find_all('h3')
        for h3 in h3_tags:
            a_tag = h3.find('a')
            if a_tag:
                headlines.append(a_tag.get_text().strip())
            else:
                headlines.append(h3.get_text().strip())
        
        return headlines
    except Exception as e:
        print(f"Error fetching news: {e}")
        return []

def analyze_sentiment(headlines):
    prompt = "Rate the sentiment of each news headline on a scale of 1 to 10, where 1 is very negative and 10 is very positive. Provide the ratings in a JSON list.\n\n"
    prompt += json.dumps(headlines) + "\n\nRatings:"
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150
        )
        
        ratings = eval(response.choices[0].message.content.strip())  # Use eval to safely parse the JSON list from the string
        sentiments = list(zip(headlines, ratings))
        return sentiments
    except Exception as e:
        print(f"Error analyzing sentiment: {e}")
        return [(headline, None) for headline in headlines]

def get_headlines_and_sentiments(url):
    headlines = fetch_news_headlines(url)
    if headlines:
        return analyze_sentiment(headlines)
    else:
        return []
