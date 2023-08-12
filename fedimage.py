"""
Check your mastodon/misskey follows, and download any media posted recently.
"""


# TODO: Refactor sync_feeds() to iterate with an index.


import os
import re
import argparse
import sqlite3
import requests


SCRIPT_PATH = os.path.dirname(os.path.realpath(__file__))
# CONN = sqlite3.connect(':memory:')
CONN = sqlite3.connect('fedimage.db')
DL_DIR = SCRIPT_PATH + "/downloads"
FEED_DIR = SCRIPT_PATH + "/feeds"
FEEDS_FILE = SCRIPT_PATH + "/feeds.txt"
DRY_RUN = True


def main():
    """Main function."""
    init_dirs()
    args = get_args()
    if args.file:
        generate_feeds_file(args)
    # syncFeeds()
    CONN.close()


def get_args():
    """Get the command-line arguments, and return an argparse namespace."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'file',
        nargs='?',
        help="A csv file containing account names.")
    args = parser.parse_args()
    return args


def generate_feeds_file(args):
    """Generate feeds.txt from the kind of csv mastondon lets you export."""
    print("Generating feeds file from CSV...")
    with open(args.file, encoding="utf-8") as users_filename:
        next(users_filename) # skip the header line
        output = []
        for username in users_filename:
            username = username.strip()
            matches = re.search(r"(.*)@(.*),.*,.*,", username)
            output.append(f"https://{matches.group(2)}/@{matches.group(1)}.rss")
    with open(FEEDS_FILE, 'w', encoding="utf-8") as feeds_file:
        feeds_file.write("\n".join(output))


def sync_feeds():
    """Read feeds.txt and sync each feed, one by one."""
    with open(FEEDS_FILE, encoding="utf-8") as feeds_filename:
        for feed_url in feeds_filename:
            feed_url = feed_url.strip()
            matches = re.search(r".*:\/\/(.*)\/@(.*)\.rss", feed_url)
            filename = f"{matches.group(2)}@{matches.group(1)}.rss"

            download_rss_file(feed_url, FEED_DIR + "/" + filename)
            parse_feed(FEED_DIR + "/" + filename)

            print(80*"-")


def init_dirs():
    "Create directories for feeds and downloads, if they don't already exist."
    for directory in [DL_DIR, FEED_DIR]:
        if not os.path.exists(directory):
            os.makedirs(directory)


def download_rss_file(feed_url, filename):
    """Fetch an rss file from a URL, and save it as the specified filename."""
    print(f"FETCHING FEED FROM {feed_url}")
    feed_file = requests.get(feed_url, timeout=30).content
    with open(filename, 'wb') as handler:
        handler.write(feed_file)


def parse_feed(feed_filename):
    "Parse an RSS feed file, and run the media downloader on any media found."
    creator = os.path.basename(os.path.splitext(feed_filename)[0])
    print(f"CHECKING FOR MEDIA FROM {creator}\n")

    cursor = CONN.cursor()
    cursor.execute(f"""CREATE TABLE if not exists '{creator}' (
            mediaURL text
            )""")
    CONN.commit()

    with open(feed_filename, encoding="utf-8") as feed:
        got_item = False
        text_item = {}
        for line in feed:
            line = line.strip()
            # print(line)

            if line == "<item>":
                got_item = True
                continue

            if got_item:
                if line == "</item>":
                    if "mediaURL" in text_item:
                        item = Item(
                            creator = creator,
                            source = text_item["link"],
                            media_url = text_item["mediaURL"])
                        item.download_media()
                        print()
                    got_item = False
                    text_item = {}
                    continue

                text_item["creator"] = creator
                cdata_match = re.search(
                    r"<(.*)><!\[CDATA\[(.*)\]\]><\/.*>",
                    line)
                normal_match = re.search(r"<(.*)>(.*)<\/.*>", line)
                media_match = re.search(
                    r'<enclosure url="(.*)" length=".*" type=".*"/>',
                    line)
                mastodon_media_match = re.search(
                    r'^<media:content url="(.*)" type=".*" fileSize=".*" medium=".*">$',
                    line)

                if cdata_match:
                    text_item[cdata_match.group(1)] = cdata_match.group(2)
                elif normal_match:
                    text_item[normal_match.group(1)] = normal_match.group(2)
                elif media_match:
                    text_item["mediaURL"] = media_match.group(1)
                elif mastodon_media_match:
                    text_item["mediaURL"] = mastodon_media_match.group(1)


class Item:
    """Represents each media items found in the RSS fields."""


    def __init__(self, creator, source, media_url):
        self.creator = creator
        self.source = source
        self.media_url = media_url
        self._filename = None
        self._already_downloaded = None


    @property
    def filename(self):
        """The basename of the media file on the server."""
        if self._filename:
            return self._filename

        self._filename = DL_DIR + "/" + re.search(
            r".*\/([^\/].*)", self.media_url).group(1)
        return self._filename


    @property
    def already_downloaded(self):
        "Returns a boolean representing if the item has been downloaded or not."
        cursor = CONN.cursor()
        cursor.execute(f"""
            SELECT * FROM '{self.creator}'
            WHERE mediaURL = '{self.media_url}'
            """)
        data=cursor.fetchone()

        if data is None:
            self._already_downloaded = False
        else:
            self._already_downloaded = True

        return self._already_downloaded


    def add_to_database(self):
        """Add to the database a record of this item."""
        cursor = CONN.cursor()
        cursor.execute(f"""
            INSERT INTO '{self.creator}
            'VALUES ('{self.media_url}')
            """)
        CONN.commit()


    def download_media(self):
        """Download this media item, and save it to the downloads directory."""
        print(f"DOWNLOADING {self.media_url}")

        if self.already_downloaded:
            print("Already downloaded.")
            return

        print(f"SAVING AS {self.filename}")
        img_data = requests.get(self.media_url, timeout=30).content
        with open(self.filename, 'wb') as handler:
            handler.write(img_data)
        self.generate_tag_file()
        self.add_to_database()


    def generate_tag_file(self):
        """Write the accompanying tag text file for this item."""
        tag_filename = self.filename + ".txt"
        print(f"WRITING TAGS TO {tag_filename}")
        with open(tag_filename, "w", encoding="utf-8") as tag_file:
            tag_file.write(
                f"creator:{self.creator}\nsource:{self.source}")



if __name__ == "__main__":
    main()
