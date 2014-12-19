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

suspended_group = ['qvc']

for i, spider in enumerate(spiders):
    if spider not in pending_spiders and spider not in suspended_group:
        result = requests.post(schedule, data={'project': 'spidercrawl', 'spider': spider})
