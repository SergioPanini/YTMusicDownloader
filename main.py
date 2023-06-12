from pytube import YouTube, Playlist
from models import ioPlaylist
import aiohttp
import asyncio

playlist_url = r"https://www.youtube.com/playlist?list=OLAK5uy_n1WRcJb5fLA8MJQPAG15vcBfBbO0QNPUM"

video_folder_path = r"./tmp"

# playlist_yt = Playlist(playlist_url)
# print("Count videos: ", playlist_yt.length)
# for video_index, video in enumerate(playlist_yt.videos):
#     video.streams.get_audio_only().download(output_path=video_folder_path, filename=f"{video.author} - {video.title}.mp3")

# print("Done")
base_headers = {"User-Agent": "Mozilla/5.0", "accept-language": "en-US,en"}

async def main():
    async with aiohttp.ClientSession(headers=base_headers) as session:
        playlist_yt = ioPlaylist(playlist_url, session=session)
        print(await playlist_yt.length)


if __name__ == '__main__':
    asyncio.run(main())
