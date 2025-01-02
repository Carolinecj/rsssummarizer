import feedparser
import openai
import logging
import requests
import time
from datetime import datetime, timedelta
import os
import re

# Configure OpenAI API Key
openai.api_key = os.getenv('OPENAI_API_KEY')

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Test OpenAI connection
def test_openai_connection():
    try:
        response = requests.get('https://api.openai.com/v1/models', headers={
            'Authorization': f'Bearer {os.getenv("OPENAI_API_KEY")}'
        })
        if response.status_code == 200:
            logging.info("Successfully connected to OpenAI API.")
        else:
            logging.error(f"Failed to connect to OpenAI: {response.status_code} {response.text}")
    except requests.exceptions.RequestException as e:
        logging.error(f"Error connecting to OpenAI API: {e}")

test_openai_connection()

# Fetch articles from multiple RSS Feeds
def fetch_rss_feeds(feed_urls):
    logging.info('Fetching articles from RSS feeds.')
    articles = []
    now = datetime.now()
    yesterday = now - timedelta(days=1)
    for feed_url in feed_urls:
        logging.info(f'Parsing feed: {feed_url}')
        feed = feedparser.parse(feed_url)
        if 'entries' in feed:
            for entry in feed.entries:
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    published = datetime(*entry.published_parsed[:6])
                    if published > yesterday:
                        articles.append({
                            'title': entry.title,
                            'link': entry.link,
                            'summary': entry.summary
                        })
        else:
            logging.warning(f'No entries found in feed: {feed_url}')
    logging.info(f'Fetched {len(articles)} new articles.')
    return articles

# Summarize a single article using ChatGPT
def summarize_article(article, index):
    prompt = f"""You are a helpful assistant preparing a summary for an investment analyst in the medical technology space.
Summarize the following article concisely. Mention key companies and their activities.

Article {index}:
Title: {article['title']}
Content: {article['summary']}

Respond in the following format:
- Key Companies Mentioned: [List of companies or "None"]
- Summary: [Concise summary of the article]
"""

    try:
        response = openai.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an assistant summarizing articles for investment analysts."},
                {"role": "user", "content": prompt}
            ]
        )
        summary = response.choices[0].message.content.strip()
        return summary
    except Exception as e:
        logging.error(f"Error summarizing article {index}: {e}")
        return f"- Article Number: {index}\n- Status: 'Summary could not be processed.'"

# Summarize multiple articles
def summarize_articles(articles):
    summaries = []
    for index, article in enumerate(articles, start=1):
        summary = summarize_article(article, index)
        summaries.append(summary)
    return summaries

# Create blog post content
def create_blog_post(articles, summaries):
    logging.info('Creating blog post content.')

    title_list = ""
    detailed_summaries = ""

    for idx, (article, summary) in enumerate(zip(articles, summaries), start=1):
        title_list += f"{idx}. [{article['title']}](#article-{idx})\n"
        detailed_summaries += (
            f"## <a name='article-{idx}'></a>{article['title']}\n\n"
            f"{summary}\n\n"
            f"[Read more]({article['link']})\n\n"
        )

    blog_content = f"{title_list}\n\n{detailed_summaries}"
    logging.info('Blog post content created.')
    return blog_content

# Post to Medium
def post_to_medium(title, content):
    logging.info('Posting article to Medium.')
    url = 'https://api.medium.com/v1/users/1d18a388262a57818ce22bb52ea3126879e2d342372ef7662de5335a5c44035ef/posts'
    headers = {
        'Authorization': f'Bearer {os.getenv("MEDIUM_ACCESS_TOKEN")}',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    data = {
        'title': title,
        'contentFormat': 'markdown',
        'content': content,
        'publishStatus': 'draft'
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 201:
        logging.info('Article successfully posted to Medium as a draft.')
    else:
        logging.error(f'Failed to post article to Medium: {response.status_code} {response.text}')

# Automated job
def scheduled_job():
    rss_feed_urls = [
        "https://medcitynews.com/feed/",
        "https://endpts.com/feed/",
        "https://biopharmconsortium.com/blog/feed/",
        "https://www.biopharmadive.com/feeds/news/",
        "https://www.fiercepharma.com/rss/xml",
        "https://www.fiercebiotech.com/rss/xml",
        "https://www.fiercehealthcare.com/rss/xml"
    ]

    articles = fetch_rss_feeds(rss_feed_urls)
    if articles:
        summaries = summarize_articles(articles)
        blog_title = f"Daily MedTech and Pharma market highlights for {datetime.now().strftime('%Y-%m-%d')}"
        blog_content = create_blog_post(articles, summaries)
        post_to_medium(blog_title, blog_content)

# Run the job for testing
scheduled_job()
