import requests

listspiders = 'http://localhost:6800/listspiders.json?project=spiderpig'
listjobs = 'http://localhost:6800/listjobs.json?project=spiderpig'
schedule = 'http://localhost:6800/schedule.json'

spiders = requests.get(listspiders).json()
spiders = spiders.get('spiders', [])

jobs = requests.get(listjobs).json()
pending_spiders = map(lambda x: x['spider'], jobs.get('pending', []))

for spider in spiders:
    if spider not in pending_spiders:
        result = requests.post(schedule, data={'project': 'spiderpig', 'spider': spider})
