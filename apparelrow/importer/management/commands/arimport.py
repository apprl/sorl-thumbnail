import re, datetime
#from datetime import date
from optparse import make_option

from django.core.management.base import BaseCommand, CommandError
from importer.models import VendorFeed, ImportLog

class Command(BaseCommand):
    args = "<name>"
    help = "Run import for specified vendor"
    option_list = BaseCommand.option_list + (
        make_option('--warehouse',
            action='store_true',
            dest='warehouse',
            default=False,
            help='Fetch feed from warehouse rather than the Internet',
        ),
        make_option('--date',
            action='store',
            dest='date',
            help='Import data for specified date, in format YYYY-MM-DD',
            default=None,
        ),
        make_option('--list',
            action='store_true',
            dest='list',
            help='List all available feeds',
            default=False,
        ),
        make_option('--all',
            action='store_true',
            dest='all',
            help='Import all configured feeds',
            default=False
        ),
    )
    
    def handle(self, *args, **options):
        
        if options['list']:
            return self.list_feeds()
        
        if options['all']:
            return self.import_all_feeds(**options)
        
        if len(args) > 0:
            self.import_feed(args[0], **options)
        else:
            raise CommandError('Missing feed argument')
    
    def list_feeds(self):
        format = "%-17s%-22s%s"
        
        # FIXME: When upgrading from Django 1.2, replaces these print statements
        # with self.stdout.write (and add a line break to the format variable)
        if VendorFeed.objects.count():
            print format % ('Name', 'Vendor', 'URL')
            
            for feed in VendorFeed.objects.all():
                print format % (
                        feed.name,
                        feed.vendor.name,
                        feed.url
                    )
        else:
            print "There are no feeds installed"
    
    def import_feed(self, name, **options):                
        if options['date']:
            m = re.match(r'^(\d{4})-(\d{2})-(\d{2})', options['date'])
            if not m:
                raise CommandError('Date not recognized')
            
            options['date'] = datetime.date(*[int(i) for i in m.groups(0)])
        
        try:
            feed = VendorFeed.objects.get(name=name)
        except VendorFeed.DoesNotExist:
            raise CommandError('Feed named %s does not exist' % name)
        
        try:
            feed.run_import(
                from_warehouse=options['warehouse'], 
                for_date=options['date']
            )
        except KeyboardInterrupt:
            print "\nInterrupt - Aborting import"
            # NOTE: When accessing the log through feed.latest_import_log.pk it 
            # doesn't return a new object, hence this workaround
            # FIXME: Should we move this fix to the accessor instead?
            log = ImportLog.objects.get(pk=feed.latest_import_log.pk)
            log.messages.create(status='info', message='Processes halted by user')
            log.status = 'failed' 
            log.save()
        
        print "Import finished: %s\n" % feed.latest_import_log.status
    
    def import_all_feeds(self, **options):
        for feed in VendorFeed.objects.all():
            print "Importing %s" % feed.name
            try:
                self.import_feed(feed.name, **options)
            except Exception, e:
                print "Error importing feed %s: %s" % (feed.name, e)

