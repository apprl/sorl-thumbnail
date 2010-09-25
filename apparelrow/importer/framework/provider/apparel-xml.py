import libxml2, logging
from xml.sax.saxutils import unescape

from importer.framework.provider import Provider as BaseProvider
from importer.framework.mapper import DataMapper


class ApparelMapper(DataMapper):
    def map_variations(self):
        for v in self.record['variations']:
            if 'color' in v:
                c = self.map_colors(v['color'])
                if len(c):
                    v['color'] = c[0]
                else:
                    logging.debug('Color %s not recogised' % v['color'])
                    del v['color']

class Provider(BaseProvider):
    def __init__(self, *args, **kwargs):
        super(Provider, self).__init__(*args, **kwargs)
        self.mapper=DataMapper


    def process(self):
        doc = libxml2.readFd(self.file.fileno(), None, 'utf8', libxml2.XML_PARSE_NOENT)
        ctx = doc.xpathNewContext()
        
        # FIXME: check version, date and vendor here
        
        for p in ctx.xpathEval('//product'):
            record = dict([
                (e.name, self.process_text(e.getContent())) 
                for e in p.xpathEval('./*')
            ])
            
            record['variations'] = []
            
            for v in p.xpathEval('./variations/*'):
                record['variations'].append(
                    dict([
                        (a.name, self.process_text( a.content )) 
                        for a in v.xpathEval('./@*')
                    ])
                )
            
            mapper = self.mapper(self, record)
            self.import_data( mapper.translate() )
    
    def process_text(self, text):
        return unicode( unescape( text ), 'utf-8')