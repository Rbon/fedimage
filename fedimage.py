# TODO: Refactor main() to iterate with an index.


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
    initDirs()
    args = getArgs()
    if args.file:
        generateFeedsFile(args)
    syncFeeds()
    CONN.close()


def getArgs():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'file',
        nargs='?',
        help="A csv file containing account names.")
    args = parser.parse_args()
    return args


def generateFeedsFile(args):
    with open(args.file) as usersFilename:
        next(usersFilename) # skip the header line
        output = []
        for username in usersFilename:
            username = username.strip()
            matches = re.search("(.*)@(.*),.*,.*,", username)
            output.append("https://{hostname}/@{username}.rss".format(
                hostname = matches.group(2),
                username = matches.group(1)))
    with open(FEEDS_FILE, 'w') as feeds_file:
        feeds_file.write("\n".join(output))


def syncFeeds():
    with open(FEEDS_FILE) as feedsFilename:
        for feedURL in feedsFilename:
            feedURL = feedURL.strip()
            matches = re.search(".*:\/\/(.*)\/@(.*)\.rss", feedURL)
            filename = "{user}@{hostname}.rss".format(
                user = matches.group(2),
                hostname = matches.group(1))

            downloadRSSFile(feedURL, FEED_DIR + "/" + filename)
            parseFeed(FEED_DIR + "/" + filename)

            print(80*"-")


def initDirs():
    for directory in [DL_DIR, FEED_DIR]:
        if not os.path.exists(directory):
            os.makedirs(directory)


def downloadRSSFile(feedURL, filename):
    print("FETCHING FEED FROM {feedURL}".format(feedURL=feedURL))
    feedFile = requests.get(feedURL).content
    with open(filename, 'wb') as handler:
        handler.write(feedFile)


def parseFeed(feedFilename):
    creator = os.path.basename(os.path.splitext(feedFilename)[0])
    print("CHECKING FOR MEDIA FROM {creator}\n".format(creator=creator))

    c = CONN.cursor()
    c.execute("""CREATE TABLE if not exists '{table}' (
            mediaURL text
            )""".format(
                table = creator))
    CONN.commit()

    with open(feedFilename) as feed:
        gotItem = False
        textItem = {}
        for line in feed:
            line = line.strip()
            # print(line)

            if line == "<item>":
                gotItem = True
                continue

            if gotItem:
                if line == "</item>":
                    if "mediaURL" in textItem:
                        item = Item(
                            creator = creator,
                            source = textItem["link"],
                            mediaURL = textItem["mediaURL"])
                        item.downloadMedia()
                        print()
                    gotItem = False
                    textItem = {}
                    
                    continue

                # print(line)
                textItem["creator"] = creator
                cdataMatch = re.search("<(.*)><!\[CDATA\[(.*)\]\]><\/.*>", line)
                normalMatch = re.search("<(.*)>(.*)<\/.*>", line)
                mediaMatch = re.search(
                    '<enclosure url="(.*)" length=".*" type=".*"/>',
                    line)
                mastodonMediaMatch = re.search(
                    '^<media:content url="(.*)" type=".*" fileSize=".*" medium=".*">$',
                    line)
                
                if cdataMatch:
                    textItem[cdataMatch.group(1)] = cdataMatch.group(2)
                elif normalMatch:
                    textItem[normalMatch.group(1)] = normalMatch.group(2)
                elif mediaMatch:
                    textItem["mediaURL"] = mediaMatch.group(1)
                elif mastodonMediaMatch:
                    textItem["mediaURL"] = mastodonMediaMatch.group(1)


class Item:
    def __init__(self, creator, source, mediaURL):
        self.creator = creator
        self.source = source
        self.mediaURL = mediaURL
        self._filename = None
        self._alreadyDownloaded = None


    @property
    def filename(self):
        if self._filename: return self._filename

        self._filename = DL_DIR + "/" + re.search(
            ".*\/([^\/].*)", self.mediaURL).group(1)
        
        return self._filename


    @property
    def alreadyDownloaded(self):
        c = CONN.cursor()
        c.execute("SELECT * FROM '{table}' WHERE mediaURL = '{mediaURL}'".format(
            table = self.creator,
            mediaURL = self.mediaURL))
        data=c.fetchone()
        
        if data is None:
            self._alreadyDownloaded = False
        else:
            self._alreadyDownloaded = True

        return self._alreadyDownloaded


    def addToDatabase(self):
        c = CONN.cursor()
        c.execute(
            "INSERT INTO '%s' VALUES ('%s')" % (self.creator, self.mediaURL))
        CONN.commit()


    def downloadMedia(self):
        print("DOWNLOADING {mediaURL}".format(mediaURL = self.mediaURL))

        if self.alreadyDownloaded:
            print("Already downloaded.")
            return

        print("SAVING AS {filename}".format(filename = self.filename))
        img_data = requests.get(self.mediaURL).content
        with open(self.filename, 'wb') as handler:
            handler.write(img_data)
        self.generateTagFile()
        self.addToDatabase()


    def generateTagFile(self):
        tagFileName = self.filename + ".txt"
        print("WRITING TAGS TO {tagFileName}".format(
            tagFileName=tagFileName))
        f = open(tagFileName, "w")
        f.write(
            "creator:{creator}\nsource:{source}".format(
                creator = self.creator,
                source = self.source)
        )
        f.close()


if __name__ == "__main__":
    main()
