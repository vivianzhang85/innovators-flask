import random, json, os, fcntl
from flask import current_app

lyrics_data = []
lyric_list = [
    "Think of me, think of me fondly when we've said goodbye - The Phantom of the Opera",
    "Do you hear the people sing? Singing the song of angry men - Les Misérables",
    "He had it coming, he had it coming, he only had himself to blame - Chicago",
    "Memory, all alone in the moonlight, I can smile at the old days - Cats",
    "Defying gravity, I'm flying high, defying gravity - Wicked",
    "Can you feel the love tonight? The peace the evening brings - The Lion King",
    "Let it go, let it go, can't hold it back anymore - Frozen",
    "A whole new world, a new fantastic point of view - Aladdin",
    "Come what may, I will love you until my dying day - Moulin Rouge!",
    "I don't have to be sorry for anything, I'm just a girl who's had enough - Six",
    "You will be found, even when the dark comes crashing through - Dear Evan Hansen",
    "I am not throwing away my shot, I am not throwing away my shot - Hamilton",
    "Hello! My name is Elder Price, and I would like to share with you - Book of Mormon",
    "You are here, that's how it's become so clear - Come From Away",
    "Wait for me, I'm coming, wait I'm coming with you - Hadestown",
    "All I ask of you is one thing, please don't be sorry - Mean Girls",
    "Music of the night, close your eyes and surrender to your darkest dreams - The Phantom of the Opera",
    "On my own, pretending he's beside me, all alone I walk with him - Les Misérables"
]

def get_lyrics_file():
    # Always use Flask app.config['DATA_FOLDER'] for shared data
    data_folder = current_app.config['DATA_FOLDER']
    return os.path.join(data_folder, 'lyrics.json')

def _read_lyrics_file():
    LYRICS_FILE = get_lyrics_file()
    if not os.path.exists(LYRICS_FILE):
        return []
    with open(LYRICS_FILE, 'r') as f:
        fcntl.flock(f, fcntl.LOCK_SH)
        try:
            data = json.load(f)
        except Exception:
            data = []
        fcntl.flock(f, fcntl.LOCK_UN)
    return data

def _write_lyrics_file(data):
    LYRICS_FILE = get_lyrics_file()
    with open(LYRICS_FILE, 'w') as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        json.dump(data, f)
        fcntl.flock(f, fcntl.LOCK_UN)

def initLyrics():
    LYRICS_FILE = get_lyrics_file()
    # Only initialize if file does not exist
    if os.path.exists(LYRICS_FILE):
        return
    lyrics_data = []
    item_id = 0
    for item in lyric_list:
        lyrics_data.append({"id": item_id, "lyric": item, "love": 0, "dislike": 0})
        item_id += 1
    # prime some love responses
    for i in range(10):
        id = random.choice(lyrics_data)['id']
        lyrics_data[id]['love'] += 1
    for i in range(5):
        id = random.choice(lyrics_data)['id']
        lyrics_data[id]['dislike'] += 1
    _write_lyrics_file(lyrics_data)
        
def getLyrics():
    return _read_lyrics_file()

def getLyric(id):
    lyrics = _read_lyrics_file()
    return lyrics[id]

def getRandomLyric():
    lyrics = _read_lyrics_file()
    return random.choice(lyrics)

def favoriteLyric():
    lyrics = _read_lyrics_file()
    best = 0
    bestID = -1
    for lyric in lyrics:
        if lyric['love'] > best:
            best = lyric['love']
            bestID = lyric['id']
    return lyrics[bestID] if bestID != -1 else None
    
def dislikedLyric():
    lyrics = _read_lyrics_file()
    worst = 0
    worstID = -1
    for lyric in lyrics:
        if lyric['dislike'] > worst:
            worst = lyric['dislike']
            worstID = lyric['id']
    return lyrics[worstID] if worstID != -1 else None


# Atomic vote update with exclusive lock
def _vote_lyric(id, field):
    LYRICS_FILE = get_lyrics_file()
    with open(LYRICS_FILE, 'r+') as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        lyrics = json.load(f)
        lyrics[id][field] += 1
        # Move file pointer to start before writing updated JSON
        f.seek(0)
        json.dump(lyrics, f)
        # Truncate file to remove any leftover data from previous content
        f.truncate()
        fcntl.flock(f, fcntl.LOCK_UN)
    return lyrics[id][field]

def addLyricLove(id):
    return _vote_lyric(id, 'love')

def addLyricDislike(id):
    return _vote_lyric(id, 'dislike')

def printLyric(lyric):
    print(lyric['id'], lyric['lyric'], "\n", "love:", lyric['love'], "\n", "dislike:", lyric['dislike'], "\n")

def countLyrics():
    lyrics = _read_lyrics_file()
    return len(lyrics)

if __name__ == "__main__": 
    initLyrics()  # initialize lyrics
    
    # Most likes and most disliked
    best = favoriteLyric()
    if best:
        print("Most loved", best['love'])
        printLyric(best)
    worst = dislikedLyric()
    if worst:
        print("Most disliked", worst['dislike'])
        printLyric(worst)
    
    # Random lyric
    print("Random lyric")
    printLyric(getRandomLyric())
    
    # Count of Lyrics
    print("Lyrics Count: " + str(countLyrics()))