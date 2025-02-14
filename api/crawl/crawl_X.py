import tweepy
import datetime

# Replace with your own Bearer Token from your Twitter Developer account.
BEARER_TOKEN = "AAAAAAAAAAAAAAAAAAAAANgoywEAAAAAMHguPwwk3fc%2BV%2BQ5m2jIAX3DwdE%3DPIajdkqhKXFzZVFcCdfasHWrsd8HT2r3bwMyabzjwq9a6EZp32"

# Initialize the Tweepy client.
client = tweepy.Client(bearer_token=BEARER_TOKEN, wait_on_rate_limit=True)

def get_thread_tweets(start_tweet_id):
    # Get the starting tweet to extract conversation_id and author_id.
    tweet_response = client.get_tweet(start_tweet_id, tweet_fields=["conversation_id", "author_id", "created_at"])
    if tweet_response.data is None:
        print("Tweet not found!")
        return []

    conversation_id = tweet_response.data.conversation_id
    author_id = tweet_response.data.author_id

    print(f"Conversation ID: {conversation_id}")
    print(f"Author ID: {author_id}")

    # Build a query: tweets that are part of this conversation, by this author.
    query = f"conversation_id:{conversation_id} from:{author_id}"

    tweets = []
    # Use recent search endpoint. (If the thread is older, you may need to use the full-archive search, if your access allows.)
    paginator = tweepy.Paginator(
        client.search_recent_tweets,
        query=query,
        tweet_fields=["created_at"],
        max_results=100
    )

    for response in paginator:
        if response.data:
            tweets.extend(response.data)

    # Sort tweets in ascending order by creation time.
    tweets.sort(key=lambda tweet: tweet.created_at)
    return tweets

def main():
    # Provide the tweet ID of the thread's starting tweet.
    start_tweet_id = "1757203881061405082"  # e.g., "1234567890123456789"
    thread_tweets = get_thread_tweets(start_tweet_id)

    if thread_tweets:
        print("Thread tweets by the author:")
        for tweet in thread_tweets:
            # You can format the tweet text as needed.
            timestamp = tweet.created_at.strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{timestamp}] {tweet.text}\n")
    else:
        print("No tweets found in this thread by the author.")

if __name__ == "__main__":
    main()
