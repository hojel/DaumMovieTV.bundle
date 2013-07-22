# -*- coding: utf-8 -*-
# TV from Daum Movie

import urllib, unicodedata, re

DAUM_TV_SRCH      = "http://movie.daum.net/search.do?type=tv&q=%s"
DAUM_TV_DETAIL    = "http://m.movie.daum.net/data/movie/tv/detail.json?tvProgramId=%s"
DAUM_TV_CAST      = "http://m.movie.daum.net/data/movie/tv/cast_crew.json?pageNo=1&pageSize=100&tvProgramId=%s"
DAUM_TV_PHOTO     = "http://m.movie.daum.net/data/movie/photo/tv/list.json?pageNo=1&pageSize=100&id=%s"
DAUM_TV_EPISODE   = "http://m.movie.daum.net/data/movie/tv/episode.json?pageNo=1&pageSize=1000&tvProgramId=%s"

####################################################################################################
def Start():
  HTTP.CacheTime = CACHE_1MONTH
  HTTP.Headers['Accept'] = 'text/html, application/json'

####################################################################################################
class DaumSiteTvAgent(Agent.TV_Shows):
  name = "Daum Movie"
  primary_provider = True
  languages = [Locale.Language.Korean]
  accepts_from = ['com.plexapp.agents.localmedia']

  def search(self, results, media, lang, manual=False):   
    media_name = unicodedata.normalize('NFKC', unicode(media.show)).strip()
  
    url = DAUM_TV_SRCH % (urllib.quote(media_name.encode('utf8')))
    html = HTML.ElementFromURL( url )

    items = html.xpath('//span[@class="fl srch"]')
    for item in items:
      try: year = re.search('\((\d+)\)', HTML.StringFromElement(item)).group(1)
      except: year = None
      node= item.xpath('a')[0]
      title = "".join(node.xpath('descendant-or-self::text()'))
      url = node.get('href')
      id = re.search("tvProgramId=(\d+)", url).group(1)

      if year == media.year:
        score = 95
      elif len(items) == 1:
        score = 80
      else:
        score = 10
      Log.Debug('ID=%s, media_name=%s, title=%s, year=%s' %(id, media_name, title, year))
      results.Append(MetadataSearchResult(id=id, name=title, year=year, lang=lang, score=score))

  def update(self, metadata, media, lang):
    Log.Info("in update ID = %s" % metadata.id)

    # (1) from main page
    data = JSON.ObjectFromURL(url=DAUM_TV_DETAIL % metadata.id)
    info = data['data']
    metadata.title = info['titleKo']
    metadata.summary = String.DecodeHTMLEntities(String.StripTags(info['introduce']).strip())
    metadata.rating = float(info['tvProgramPoint']['pointAvg'])
    metadata.content_rating = ""
    poster_url = info['photo']['fullname']

    metadata.genres.clear()
    metadata.genres.add(info['categoryHigh']['codeName'])

    metadata.studio = info['channel']['titleKo'] if info['channel'] else ''
    metadata.duration = 0
    metadata.originally_available_at = Datetime.ParseDate(info['startDate']).date()

    # (2) cast crew
    directors = list()
    writers = list()
    metadata.roles.clear()
    data = JSON.ObjectFromURL(url=DAUM_TV_CAST % metadata.id)
    for item in data['data']:
      cast = item['castcrew']
      if cast['castcrewCastName'] in [u'주연', u'출연', u'진행']:
        role = metadata.roles.new()
        role.role = cast['castcrewTitleKo']
        role.actor = item['nameKo']
        metadata.roles.add(role)
      elif cast['castcrewCastName'] == u'연출':
        directors.append(item['nameKo'])
      elif cast['castcrewCastName'] == u'극본':
        writers.append(item['nameKo'])
  
    # (3) from photo page
    data = JSON.ObjectFromURL(url=DAUM_TV_PHOTO % metadata.id)
    max_poster = int(Prefs['max_num_posters'])
    max_art = int(Prefs['max_num_arts'])
    idx_poster = 0
    idx_art = 0
    for item in data['data']:
      if item['photoCategory'] == '1' and idx_poster < max_poster:
        idx_poster += 1
        art_url = item['fullname']
        #art_url = re.sub("/C\d+x\d+/", "/image/", art_url)
        art = HTTP.Request( item['thumbnail'] )
        metadata.posters[art_url] = Proxy.Preview(art, sort_order = idx_poster)
      elif item['photoCategory'] in ['2', '50'] and idx_art < max_art:
        idx_art += 1
        art_url = item['fullname']
        #art_url = re.sub("/C\d+x\d+/", "/image/", art_url)
        art = HTTP.Request( item['thumbnail'] )
        metadata.art[art_url] = Proxy.Preview(art, sort_order = idx_art)
    Log.Debug('Total %d posters, %d artworks' %(idx_poster, idx_art))
    if idx_poster == 0:
      poster = HTTP.Request( poster_url )
      metadata.posters[poster_url] = Proxy.Media(poster)

    # (4) from episode page
    data = JSON.ObjectFromURL(url=DAUM_TV_EPISODE % metadata.id)
    for item in data['data']:
      episode_num = item['episodeSeq']
      episode = metadata.seasons['1'].episodes[episode_num]
      episode.title = item['episodeTitle']
      episode.summary = item['episodeIntroduce'].strip()
      episode.originally_available_at = Datetime.ParseDate(item['telecastDate']).date()
      try: episode.rating = float(item['rate'])
      except: pass
      episode.directors.clear()
      episode.writers.clear()
      for name in directors:
        episode.directors.add(name)
      for name in writers:
        episode.writers.add(name)
      #episode.thumbs[thumb_url] = Proxy.Preview(thumb_data)
