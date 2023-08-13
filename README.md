# fedimage
A python script to check your mastodon/misskey follows, and download any media posted recently.

No dependencies required. I don't know what to write here, so here's the usage text:
```
positional arguments:
  feeds_file            A text file containing a newline-separated list RSS
                        feed URLs.

options:
  -h, --help            show this help message and exit
  -v {0,1,2}, --verbosity {0,1,2}
                        Specify how verbose fedimage is. By default, this is
                        1. A verbosity of 0 will completely silence fedimage.
  -m DIRECTORY, --media-dir DIRECTORY
                        The directory to save downloaded media. By default,
                        fedimage will create a 'media' directory wherever it
                        is located, and save any media there.
  -d DIRECTORY, --database DIRECTORY
                        The path for the database of downloaded media.
                        Fedimage uses this to ensure that files are only
                        downloaded once. By default, fedimage will create a
                        database in the directory where fedimage itself is
                        located.
  -c FILE, --csv-file FILE
                        Read follows from a CSV file exported from mastodon.
                        Fedimage will then write these exports to whatever you
                        specify as feeds_file, before downloading media as
                        usual.
  -r DIRECTORY, --rss-dir DIRECTORY
                        The directory to save downloaded RSS feeds. By
                        default, fedimage will create a temporary directory to
                        save feeds.
```
