import os
import json
import csv
import time
import googleapiclient.discovery
import googleapiclient.errors
from urllib.parse import urlparse, parse_qs
import config

API_KEY = config.API_KEY

# ==========================
# YOUTUBE API CLIENT SETUP
# ==========================
def get_youtube_client():
    """Initialize and return a YouTube API client."""
    return googleapiclient.discovery.build("youtube", "v3", developerKey=API_KEY)

# ==========================
# COMMENT SCRAPING FUNCTION
# ==========================
def get_youtube_comments(youtube, video_id, keywords, channel_name, video_title, video_owner_id, raw_mode=False):
    """Fetches comments from a YouTube video, optionally filtering by keywords unless in raw mode."""
    comments = []
    next_page_token = None

    while True:
        try:
            request = youtube.commentThreads().list(
                part="snippet,replies",
                videoId=video_id,
                maxResults=100,
                pageToken=next_page_token
            )
            response = request.execute()

            for item in response.get("items", []):
                comment_data = item["snippet"]["topLevelComment"]["snippet"]
                comment_text = comment_data["textDisplay"]
                comment_id = item["id"]
                comment_date = comment_data["publishedAt"]
                like_count = comment_data.get("likeCount", 0)
                reply_count = item["snippet"].get("totalReplyCount", 0)

                if raw_mode:
                    # In raw mode, we don't filter out any comments.
                    matched_keyword = "RAW"
                else:
                    matched_keyword = next((kw for kw in keywords if kw.lower() in comment_text.lower()), None)

                # Only add the comment if raw_mode is True or if a keyword matched.
                if raw_mode or matched_keyword:
                    comment_url = f"https://www.youtube.com/watch?v={video_id}&lc={comment_id}"
                    influencer_responded = "No"
                    influencer_response = ""
                    influencer_reply_date = ""

                    if "replies" in item and reply_count > 0:
                        for reply in item["replies"]["comments"]:
                            reply_author_id = reply["snippet"]["authorChannelId"]["value"]
                            if reply_author_id == video_owner_id:
                                influencer_responded = "Yes"
                                influencer_response = reply["snippet"]["textDisplay"]
                                influencer_reply_date = reply["snippet"]["publishedAt"]
                                break  # Stop checking once we confirm a response

                    comments.append({
                        'Channel': channel_name,
                        'Video Title': video_title,
                        'Search Result': comment_text,
                        'Matched Keyword': matched_keyword,
                        'Comment Date': comment_date,
                        'Like Count': like_count,
                        'Reply Count': reply_count,
                        'Comment URL': comment_url,
                        'Did Influencer Respond': influencer_responded,
                        'Influencer Response': influencer_response,
                        'Influencer Reply Date': influencer_reply_date
                    })

            next_page_token = response.get("nextPageToken")
            if not next_page_token:
                break

            time.sleep(1)  # Respect API rate limits

        except googleapiclient.errors.HttpError as e:
            error_message = str(e)
            if "commentsDisabled" in error_message:
                print(f"⚠️ Logging '{video_title}' (Comments Disabled)")
                comments.append({
                    'Channel': channel_name,
                    'Video Title': video_title,
                    'Search Result': "Comments Disabled",
                    'Matched Keyword': "N/A",
                    'Comment Date': "N/A",
                    'Like Count': "N/A",
                    'Reply Count': "N/A",
                    'Comment URL': f"https://www.youtube.com/watch?v={video_id}",
                    'Did Influencer Respond': "N/A",
                    'Influencer Response': "N/A",
                    'Influencer Reply Date': "N/A"
                })
            else:
                print(f"❌ Error fetching comments for '{video_title}': {error_message}")
            break

    return comments

# ==========================
# FUNCTION TO RUN SEARCH (SINGLE VIDEO)
# ==========================
def run_youtube_search(video_id, keywords, raw_mode=False):
    """Runs YouTube comment search on a single video."""
    youtube = get_youtube_client()

    # Fetch video metadata
    request = youtube.videos().list(
        part="snippet",
        id=video_id
    )
    response = request.execute()

    if not response.get("items"):
        print(f"❌ Error: No video found with ID {video_id}.")
        return

    snippet = response["items"][0]["snippet"]
    channel_name = snippet["channelTitle"]
    video_title = snippet["title"]
    video_owner_id = snippet["channelId"]

    print(f"🔍 Scraping comments for: {video_title} ({video_id})")

    comments = get_youtube_comments(youtube, video_id, keywords, channel_name, video_title, video_owner_id, raw_mode)
    if not comments:
        print(f"No comments found for video: {video_title}.")
        return

    if raw_mode:
        output_file = f"output/youtube_all_comments_{video_id}.csv"
    else:
        output_file = f"output/youtube_comments_{video_id}.csv"

    with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
        fieldnames = ["Channel", "Video Title", "Search Result", "Matched Keyword", "Comment Date", "Like Count",
                      "Reply Count", "Comment URL", "Did Influencer Respond", "Influencer Response", "Influencer Reply Date"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(comments)

    print(f"✅ Comments saved to {output_file}")

# ==========================
# FUNCTION TO RUN CHANNEL-WIDE SEARCH
# ==========================
def extract_channel_id(youtube, channel_url_or_id):
    """Extracts a YouTube Channel ID from a URL, username, or direct ID."""
    
    # If already a channel ID (starts with UC), return it
    if channel_url_or_id.startswith("UC"):
        return channel_url_or_id

    # Handle different URL structures
    if "youtube.com" in channel_url_or_id:
        if "/channel/" in channel_url_or_id:  
            return channel_url_or_id.split("/channel/")[-1]
        elif "/c/" in channel_url_or_id or "/user/" in channel_url_or_id:
            username = channel_url_or_id.split("/")[-1]
        elif "/@" in channel_url_or_id:
            username = channel_url_or_id.split("/@")[-1]
        else:
            print("Error: Could not extract a valid channel identifier from URL.")
            return None
    else:
        username = channel_url_or_id.lstrip("@") 

    # Use API to get the Channel ID from the username
    request = youtube.channels().list(
        part="id",
        forHandle=username
    )
    response = request.execute()

    if "items" in response and len(response["items"]) > 0:
        return response["items"][0]["id"]
    
    print("Error: Could not retrieve channel ID. Please check the URL or username.")
    return None

def get_channel_videos(youtube, channel_id):
    """Retrieve all video IDs from a given YouTube channel."""
    video_ids = []
    next_page_token = None

    while True:
        request = youtube.search().list(
            part="id",
            channelId=channel_id,
            maxResults=50,
            pageToken=next_page_token,
            type="video"
        )
        response = request.execute()

        for item in response.get("items", []):
            video_ids.append(item["id"]["videoId"])

        next_page_token = response.get("nextPageToken")

        if not next_page_token:
            break  

    return video_ids

def run_channel_wide_search(channel_url_or_id, keywords, raw_mode=False):
    """Fetches all videos from a channel, scrapes their comments, and writes them to one CSV file."""
    youtube = get_youtube_client()
    channel_id = extract_channel_id(youtube, channel_url_or_id)

    if not channel_id:
        return

    print(f"Fetching videos from channel {channel_id}...")
    video_ids = get_channel_videos(youtube, channel_id)

    if not video_ids:
        print("Error: No videos found for this channel.")
        return

    all_comments = []
    
    for video_id in video_ids:
        # Fetch video metadata
        request = youtube.videos().list(
            part="snippet",
            id=video_id
        )
        response = request.execute()

        if not response.get("items"):
            print(f"❌ Error: No video found with ID {video_id}.")
            continue

        snippet = response["items"][0]["snippet"]
        channel_name = snippet["channelTitle"]
        video_title = snippet["title"]
        video_owner_id = snippet["channelId"]

        print(f"🔍 Scraping comments for: {video_title} ({video_id})")
        comments = get_youtube_comments(youtube, video_id, keywords, channel_name, video_title, video_owner_id, raw_mode)
        
        if comments:
            all_comments.extend(comments)
        else:
            print(f"No comments found for video: {video_title}.")

    if not all_comments:
        print("No comments found for the channel.")
        return

    if raw_mode:
        output_file = f"output/youtube_all_comments_{channel_id}.csv"
    else:
        output_file = f"output/youtube_channel_comments_{channel_id}.csv"

    with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
        fieldnames = ["Channel", "Video Title", "Search Result", "Matched Keyword", "Comment Date", "Like Count",
                      "Reply Count", "Comment URL", "Did Influencer Respond", "Influencer Response", "Influencer Reply Date"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_comments)

    print(f"✅ Channel-wide comments saved to {output_file}")
