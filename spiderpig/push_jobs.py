import requests

listspiders = 'http://localhost:6800/listspiders.json?project=spidercrawl'
listjobs = 'http://localhost:6800/listjobs.json?project=spidercrawl'
schedule = 'http://localhost:6800/schedule.json'

spiders = requests.get(listspiders).json()
spiders = spiders.get('spiders', [])

jobs = requests.get(listjobs).json()
pending_spiders = map(lambda x: x['spider'], jobs.get('pending', []))

# Do only half the stores everytime to easen the load on the server
import datetime

crawl_group = datetime.datetime.today().day % 2

suspended_group = ['qvc','menlook','nastygal','nelly-no','wolfnbadger','my-wardrobe','aldo','belstaff','bjornborg',
                   'laurenb','monica-vinander','panos-emporio']
priority_q = ['eleven','nelly','luisaviaroma','mr-porter','room21-no','rum21-se','ssense',
              'the-outnet','confident-living','net-a-porter','boozt-no','boozt-se','asos']
cleaned_group = [spider for spider in spiders if spider not in priority_q]
spiders = cleaned_group

for spider in priority_q:
    spiders.insert(0, spider)

for i, spider in enumerate(spiders):
    if spider not in pending_spiders and spider not in suspended_group:
        result = requests.post(schedule, data={'project': 'spidercrawl', 'spider': spider})