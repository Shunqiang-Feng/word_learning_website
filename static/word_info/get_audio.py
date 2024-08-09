import pandas as pd
import urllib.request
import os

# 配置
EXCEL_DIR = 'xlsx'
AUDIO_DIR = 'audio'

# 创建存放音频的目录
os.makedirs(AUDIO_DIR, exist_ok=True)

# 下载音频函数
def word_2_url(word):
    word = str(word).replace(' ', '%20')
    word = 'http://dict.youdao.com/dictvoice?type=1&audio=' + word
    url = word.lower()
    return url

def download_url(word, pth):
    urllib.request.urlretrieve(word_2_url(word), filename=pth)

def download_audio(word, chapter, index):
    chapter_dir = os.path.join(AUDIO_DIR, chapter)
    os.makedirs(chapter_dir, exist_ok=True)
    audio_path = os.path.join(chapter_dir, f'{index}.mp3')
    download_url(word, audio_path)
    print(f'Downloaded: {word} to {audio_path}')

def process_file(file_path):
    chapter = os.path.basename(file_path).split('_')[0]  # Extract chapter from file name
    df = pd.read_excel(file_path,dtype=str, header = None)
    for index, row in df.iterrows():
        word = row[0]
        download_audio(word, chapter, index + 1)

# 遍历xlsx目录下的所有文件
for file_name in os.listdir(EXCEL_DIR):
    if file_name.endswith('.xlsx'):
        file_path = os.path.join(EXCEL_DIR, file_name)
        process_file(file_path)
