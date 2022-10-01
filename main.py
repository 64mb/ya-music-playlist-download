import re
import time

from os import getenv, listdir, rename, remove
from os.path import isfile, join
from multiprocessing.dummy import Pool as ThreadPool

from yandex_music import Client
from yandex_music.track_short import TrackShort

FOLDER = './playlist'
OAUTH_TOKEN = getenv('YA_MUSIC_OAUTH_TOKEN')
# https://oauth.yandex.ru/authorize?response_type=token&client_id=23cabbbdc6cd418abb4b39c32c41195d
USER = getenv('YA_MUSIC_USER')
PLAYLIST_ID = getenv('YA_MUSIC_PLAYLIST_ID', 3)
# 3 - favorites

THREAD_POOL = 16


def download_track(task):
    short_track: TrackShort = task["track"]
    number = task["number"]
    print_progress = task["print_progress"]

    track = short_track.track if short_track.track else short_track.fetchTrack()

    num = number['etalon_by_id'][str(short_track.id)]

    artists = ''
    if track.artists:
        artists = ' - ' + ', '.join(artist.name for artist in track.artists)

    track_text = f'{track.title}{artists}'

    track_text = re.sub('[^A-zА-яёЁ\- \,0-9\.\']', '', track_text)

    track_path = FOLDER+'/' + num + '. ' + track_text+'.mp3'

    if track_text in number['current_by_title']:
        if number['current_by_title'][track_text] != num:
            rename(
                FOLDER + '/'
                + number['current_by_title'][track_text]
                + '. '
                + track_text+'.mp3',
                track_path
            )
            print('reorder: ' + track_text)
        number['current_by_title'].pop(track_text, None)

        print_progress()
        return

    if not isfile(track_path):
        try:
            track.download(track_path)
        except:
            print('error: ' + num + '. ' + track_text)

    print_progress()


def main():
    client = Client(token=OAUTH_TOKEN)

    playlist = client.users_playlists(PLAYLIST_ID, USER)

    progress = 0
    track_count = playlist.track_count

    number = {
        'current_by_title': {},
        'etalon_by_id': {},
    }

    files_exist = [f for f in listdir(FOLDER+'/')
                   if isfile(join(FOLDER+'/', f))]

    # get exist file with order number
    for f in files_exist:
        f_seed = re.match('^(\d+)\. (.*)\.mp3$', f)
        num = f_seed.group(1)
        title = f_seed.group(2)

        number['current_by_title'][title] = num

    # get real number order from playlist by track id
    num = 1
    for short_track in playlist.tracks:
        number['etalon_by_id'][str(short_track.id)] = str(num)
        num += 1

    last_progress_time = time.time()
    progress_notify_period = 2  # in seconds

    def print_progress():
        nonlocal progress
        nonlocal last_progress_time

        progress += 1
        now = time.time()
        if now - last_progress_time < progress_notify_period and progress < track_count:
            return None
        last_progress_time = now

        p_seed = round(float(progress)/float(track_count)*100, 2)
        print('progress: '+str(p_seed)+'%')

    pool_tasks = [
        {
            'track': track,
            'number': number,
            'print_progress': print_progress
        }
        for track in playlist.tracks
    ]

    pool = ThreadPool(THREAD_POOL)

    pool.map(download_track, pool_tasks)

    pool.close()
    pool.join()

    # remove deleted playlist track
    for track_removed in number['current_by_title'].keys():
        print('remove: ' + track_removed)
        remove(
            FOLDER
            + '/'
            + number['current_by_title'][track_removed]
            + '. ' + track_removed+'.mp3'
        )


main()
