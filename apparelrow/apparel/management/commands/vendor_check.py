import itertools

from django.core.mail import mail_managers
from django.core.urlresolvers import reverse
from django.core.management.base import BaseCommand
from django.contrib.sites.models import Site
from django.template import Context, Template
from django.utils import timezone

from apparelrow.apparel.models import Vendor, VendorCategory, VendorBrand


class Command(BaseCommand):
    args = ''
    help = ''

    def handle(self, *args, **options):
        one_day_ago = timezone.now() - timezone.timedelta(hours=24)

        for vendor in Vendor.objects.order_by('-name').iterator():
            vendor_categories = VendorCategory.objects.filter(created__gte=one_day_ago, vendor=vendor)
            vendor_brands = VendorBrand.objects.filter(created__gte=one_day_ago, vendor=vendor)

            if vendor_categories or vendor_brands:
                brands = []
                for vb in vendor_brands:
                    brands.append('%s - http://%s%s' % (vb.name, Site.objects.get_current().domain, reverse('admin:%s_%s_change' % ('apparel', 'vendorbrand'), args=(vb.pk,))))

                categories = []
                for vc in vendor_categories:
                    categories.append('%s - http://%s%s' % (vc.name, Site.objects.get_current().domain, reverse('admin:%s_%s_change' % ('apparel', 'vendorcategory'), args=(vc.pk,))))

                template = Template("""Brand\n{% for brand in brands %}{{ brand }}\n{% empty %}No brand updates{% endfor %}\n\nCategory\n{% for category in categories %}{{ category }}{% empty %}No category updates{% endfor %}""")
                subject = 'Updates for %s' % (vendor,)
                message = template.render(Context({'brands': brands}))

                mail_managers(subject, message)
