from typing import Optional, Dict, Iterable, List
import json

from pytube import YouTube, Playlist
from pytube.helpers import cache, DeferredGeneratorList, install_proxy, uniqueify
from pytube import extract
import aiohttp


class Client:

    base_headers = {"User-Agent": "Mozilla/5.0", "accept-language": "en-US,en"}

    async def __init__(self, url: str) -> None:
        async with aiohttp.ClientSession(url, headers=self.base_headers) as client:
            return client

class ioPlaylist(Playlist):

    def __init__(self, url: str, session: aiohttp.ClientSession, proxies: Optional[Dict[str, str]] = None):
        super().__init__(url=url, proxies=proxies)

        self._session = session

    @property
    async def html(self):
        """Get the playlist page html.

        :rtype: str
        """
        if self._html:
            return self._html

        async with self._session.get(self.playlist_url) as response:
            self._html = await response.text()
        return self._html

    @property
    async def ytcfg(self):
        """Extract the ytcfg from the playlist page html.

        :rtype: dict
        """
        if self._ytcfg:
            return self._ytcfg
        self._ytcfg = extract.get_ytcfg(await self.html)
        return self._ytcfg

    @property
    async def initial_data(self):
        """Extract the initial data from the playlist page html.

        :rtype: dict
        """
        if self._initial_data:
            return self._initial_data
        else:
            self._initial_data = extract.initial_data(await self.html)
            return self._initial_data
    
    @property
    async def yt_api_key(self):
        """Extract the INNERTUBE_API_KEY from the playlist ytcfg.

        :rtype: str
        """
        return await self.ytcfg['INNERTUBE_API_KEY']
    
    async def _paginate(
        self, until_watch_id: Optional[str] = None
    ) -> Iterable[List[str]]:
        """Parse the video links from the page source, yields the /watch?v=
        part from video link

        :param until_watch_id Optional[str]: YouTube Video watch id until
            which the playlist should be read.

        :rtype: Iterable[List[str]]
        :returns: Iterable of lists of YouTube watch ids
        """
        videos_urls, continuation = self._extract_videos(
            json.dumps(extract.initial_data(await self.html))
        )
        if until_watch_id:
            try:
                trim_index = videos_urls.index(f"/watch?v={until_watch_id}")
                yield videos_urls[:trim_index]
                return
            except ValueError:
                pass
        yield videos_urls

        # Extraction from a playlist only returns 100 videos at a time
        # if self._extract_videos returns a continuation there are more
        # than 100 songs inside a playlist, so we need to add further requests
        # to gather all of them
        if continuation:
            load_more_url, headers, data = self._build_continuation_url(continuation)
        else:
            load_more_url, headers, data = None, None, None

        while load_more_url and headers and data:  # there is an url found
            # logger.debug("load more url: %s", load_more_url)
            # requesting the next page of videos with the url generated from the
            # previous page, needs to be a post
            async with self._session.post(load_more_url, data=data) as response:
                req = await response.json()
            # extract up to 100 songs from the page loaded
            # returns another continuation if more videos are available
            videos_urls, continuation = self._extract_videos(req)
            if until_watch_id:
                try:
                    trim_index = videos_urls.index(f"/watch?v={until_watch_id}")
                    yield videos_urls[:trim_index]
                    return
                except ValueError:
                    pass
            yield videos_urls

            if continuation:
                load_more_url, headers, data = self._build_continuation_url(
                    continuation
                )
            else:
                load_more_url, headers, data = None, None, None

    @property
    async def sidebar_info(self):
        """Extract the sidebar info from the playlist page html.

        :rtype: dict
        """
        if self._sidebar_info:
            return self._sidebar_info
        else:
            self._sidebar_info = (await self.initial_data)['sidebar'][
                'playlistSidebarRenderer']['items']
            return self._sidebar_info
    
    @property
    @cache
    async def title(self) -> Optional[str]:
        """Extract playlist title

        :return: playlist title (name)
        :rtype: Optional[str]
        """
        return (await self.sidebar_info)[0]['playlistSidebarPrimaryInfoRenderer'][
            'title']['runs'][0]['text']

    @property
    async def description(self) -> str:
        return (await self.sidebar_info)[0]['playlistSidebarPrimaryInfoRenderer'][
            'description']['simpleText']

    @property
    async def length(self):
        """Extract the number of videos in the playlist.

        :return: Playlist video count
        :rtype: int
        """
        count_text = (await self.sidebar_info)[0]['playlistSidebarPrimaryInfoRenderer'][
            'stats'][0]['runs'][0]['text']
        count_text = count_text.replace(',','')
        return int(count_text)

    @property
    async def views(self):
        """Extract view count for playlist.

        :return: Playlist view count
        :rtype: int
        """
        # "1,234,567 views"
        views_text = (await self.sidebar_info)[0]['playlistSidebarPrimaryInfoRenderer'][
            'stats'][1]['simpleText']
        # "1,234,567"
        count_text = views_text.split()[0]
        # "1234567"
        count_text = count_text.replace(',', '')
        return int(count_text)