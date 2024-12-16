import feedparser
import openai
import logging
import requests
import time
from datetime import datetime, timedelta
import os

# Configure OpenAI API Key
openai.api_key = os.getenv('OPENAI_API_KEY')

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

#test open ai connection
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
                logging.info(f'Processing entry: {entry.title}')
                published = datetime(*entry.published_parsed[:6])
                logging.info(f'Published date: {published}')
                if published > yesterday:
                    logging.info(f'Article is within the last 24 hours: {entry.title}')
                    articles.append({
                        'title': entry.title,
                        'link': entry.link,
                        'summary': entry.summary
                    })
        else:
            logging.warning(f'No entries found in feed: {feed_url}')
    logging.info(f'Fetched {len(articles)} new articles.')
    return articles

# Summarize multiple articles using ChatGPT in one API call
def summarize_articles_batch(articles):
    logging.info('Summarizing articles in batch.')

    # Prepare the batch prompt
    batch_prompt = "You are a helpful assistant preparing relevant information for your boss who is an investment analyst in the medical technology space. He needs well-summarized articles with relevant insights for investment decisions. Most importantly, skip the article if it is not relevant or if no specific company is mentioned. Summarize the articles as follows:\n\n"
    
    for i, article in enumerate(articles):
        batch_prompt += f"Article {i+1}: {article['summary']}\n"

    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": batch_prompt}
            ]
        )
        
        # Split the response back into individual article summaries
        summaries = response.choices[0].message.content.strip().split("\n\n")
        logging.info('Articles summarized in batch.')
        return summaries

    except Exception as e:
        logging.error(f'Error summarizing articles in batch: {e}')
        return ['Summary not available.'] * len(articles)

def create_blog_post(articles, summaries):
    logging.info('Creating blog post content.')

    # Initialize content strings
    title_list = ""
    detailed_summaries = ""

    for idx, (article, summary) in enumerate(zip(articles, summaries)):
        if summary != 'NA':
            # Create the title list with links
            title_list += f"1. [{article['title']}](#article-{idx+1})\n"
            
            # Create detailed summaries section
            detailed_summaries += (
                f"## <a name='article-{idx+1}'></a>{article['title']}\n\n"
                f"{summary}\n\n"
                f"[Read more]({article['link']})\n\n"
            )

    # Combine the title list and detailed summaries
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
        'publishStatus': 'draft'  # To create a draft
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 201:
        logging.info('Article successfully posted to Medium as a draft.')
        print('Article successfully posted to Medium as a draft.')
    else:
        logging.error(f'Failed to post article to Medium: {response.status_code} {response.text}')
        print(f'Failed to post article to Medium: {response.status_code} {response.text}')

# Automated job
def scheduled_job():
    rss_feed_urls = [
        "https://medcitynews.com/feed/",
        "https://endpts.com/feed/"
        "https://biopharmconsortium.com/blog/feed/"
        "https://www.biopharminternational.com/rss"
        "https://www.biopharmadive.com/feeds/news/",
        "https://www.fiercepharma.com/rss/xml",
        "https://www.fiercebiotech.com/rss/xml",
        "https://www.fiercehealthcare.com/rss/xml"
    ]
    articles = fetch_rss_feeds(rss_feed_urls)
    if articles:
        summaries = summarize_articles_batch(articles)
        blog_title = f"Daily MedTech and Pharma market highlights for {datetime.now().strftime('%Y-%m-%d')}"
        blog_content = create_blog_post(articles, summaries)
        post_to_medium(blog_title, blog_content)

# Call the job function directly for testing
scheduled_job()
