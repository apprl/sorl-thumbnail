import datetime
import urllib
from decimal import Decimal as D
from random import randint

from dateutil.relativedelta import relativedelta
from django.contrib.auth import get_user_model
from django.core import management
from django.core.urlresolvers import reverse
from django.test import TransactionTestCase
from django.test.utils import override_settings
from freezegun import freeze_time
from model_mommy.mommy import make

from advertiser.models import Store
from apparelrow.dashboard.models import ClickCost, Sale
from apparelrow.dashboard.models import Cut
from apparelrow.dashboard.models import Payment
from apparelrow.dashboard.stats import stats_admin
from apparelrow.dashboard.stats import stats_publisher
from apparelrow.dashboard.stats.stats_cache import stats_cache, mrange, flush_stats_cache, \
    flush_stats_cache_by_month, flush_stats_cache_by_year, redis as stats_redis, cache_key
from apparelrow.statistics.models import ProductStat


@override_settings(CELERY_EAGER_PROPAGATES_EXCEPTIONS=True, CELERY_ALWAYS_EAGER=True, BROKER_BACKEND='memory')
class TestStats(TransactionTestCase):

    def setUp(self):
        flush_stats_cache()
        self.click_dates = set()
        self.order_id = 10000
        self.test_month = 2
        self.test_year = 2016

    def create_users(self, ppc_as=False, create_referral_partner=False):
        publisher = make(get_user_model(),
                         is_partner=True,
                         partner_group__has_cpc_all_stores=ppc_as,
                         )
        if create_referral_partner:
            with freeze_time(datetime.date(self.test_year, self.test_month, 1)):
                # Referral user - should get kickbacks on whatever publisher is making
                publisher.referral_partner_parent = make(get_user_model(),
                                                         is_partner=True,
                                                         referral_partner=True,
                                                         partner_group=publisher.partner_group)
                publisher.save()
        return publisher

    def click(self, store, publisher, order_value=0, invalidate_click=False, date_out_of_range=False):
        """
        Simulates a user click on a link created by publisher
        Gives unique order ids and saves the click date so we can run import on that later
        """

        if order_value and not store.vendor.is_cpo:
            raise Exception("Don't pass an order value with a non-cpo vendor")

        month = self.test_month
        if date_out_of_range:
            month += 1
        click_date = datetime.date(self.test_year, month, randint(1, 28))

        with freeze_time(click_date):
            self.click_dates.add(click_date)
            make(ProductStat, vendor=store.vendor.name, user_id=publisher.id if publisher else 0, is_valid=(not invalidate_click))
            if order_value and store.vendor.is_cpo:
                page = '%s-Shop' % ((publisher.pk,) if publisher else 0)
                response = self.client.get('%s?store_id=%s&url=%s&custom=%s' % (reverse('advertiser-link'),
                                                                                store.identifier,
                                                                                'http://www.mystore.com/myproduct/',
                                                                                page))
                self.assertEqual(response.status_code, 302)

                payload = dict(store_id=store.identifier, order_id=str(self.order_id), order_value=order_value, currency='EUR')
                response = self.client.get('%s?%s' % (reverse('advertiser-pixel'), urllib.urlencode(payload)))
                self.assertEqual(response.status_code, 200)
                self.order_id += 1
                return self.order_id - 1

    def get_click_dates(self):
        return [d.strftime('%Y-%m-%d') for d in self.click_dates]

    def collect_clicks(self):
        for day in self.get_click_dates():
            with freeze_time(day):
                management.call_command('clicks_summary', verbosity=0, date=day)
        # we run the import on the first of the month after our test month
        import_date = datetime.date(self.test_year, self.test_month+1, 1)
        with freeze_time(import_date):
            management.call_command('dashboard_import', 'aan', verbosity=0, interactive=False)


class TestStatsAdmin(TestStats):

    def test_top_stats_ppc_as_publisher(self):

        # Create users

        ppc_as_publisher = self.create_users(ppc_as=True, create_referral_partner=True)

        # Create stores / vendors. We only create AAN vendors because it allows us to control commission_percentage

        cpo_store = make(Store, vendor__is_cpo=True, vendor__is_cpc=False, vendor__name='cpo_v', commission_percentage='0.2')
        make(Cut, vendor=cpo_store.vendor, group=ppc_as_publisher.partner_group, cut=0, cpc_amount=3, referral_cut=0.1)

        cpc_store = make(Store, vendor__is_cpc=True, vendor__is_cpo=False, vendor__name='cpc_v')
        make(Cut, vendor=cpc_store.vendor, group=ppc_as_publisher.partner_group, cut=0, cpc_amount=3, referral_cut=0.1)
        make(ClickCost, vendor=cpc_store.vendor, amount=5)

        # Create clicks, both valid and invalid

        self.click(cpo_store, ppc_as_publisher, order_value=500)   # with 20% commission = 100. 3 to ppc_as publisher
        self.click(cpo_store, None, order_value=600)   # with 20% commission = 120 - all goes to Apprl
        self.click(cpo_store, ppc_as_publisher, invalidate_click=True)   # click shouldn't count
        self.click(cpo_store, ppc_as_publisher)    # no cpo conversion, but ppc_as publisher still gets 3

        self.click(cpc_store, ppc_as_publisher)    # 3 to ppc_as publisher. vendor pays 5
        self.click(cpc_store, ppc_as_publisher, invalidate_click=True)   # shouldn't count
        self.click(cpc_store, ppc_as_publisher, date_out_of_range=True)   # this one shouldn't count in stats since it's out of range

        # Collect clicks, generate sales & user earnings.

        self.collect_clicks()

        # Test it!

        tr = mrange(self.test_year, self.test_month)

        self.assertEqual(stats_admin.earnings_total(tr), 225)    # 100 + 120 commission from cpo sales + 5 cpc click cost
        self.assertEqual(stats_admin.earnings_publisher(tr), 9)  # 3 valid ppc_as clicks x 3 = 9
        self.assertEqual(stats_admin.earnings_apprl(tr), 225 - 9)  # defined as total - publisher
        self.assertEqual(stats_admin.referral_earnings_total(tr), 0)         # by definition
        self.assertEqual(stats_admin.referral_earnings_publisher(tr), D('50.9'))  # 50 (default signup bonus) + 10% (defined in Cuts) of 9 (publisher earnings)
        self.assertEqual(stats_admin.referral_earnings_apprl(tr), D('-50.9'))     # -publisher earnings by definition

        self.assertEqual(stats_admin.ppo_commission_total(tr), 220)
        self.assertEqual(stats_admin.ppo_commission_publisher(tr), 0)    # by definition
        self.assertEqual(stats_admin.ppo_commission_apprl(tr), 0)        # by definition

        self.assertEqual(stats_admin.ppc_commission_total(tr), 5)        # 1 click to ppc store
        self.assertEqual(stats_admin.ppc_commission_publisher(tr), 0)    # by defintion
        self.assertEqual(stats_admin.ppc_commission_apprl(tr), 0)        # by definition

        self.assertEqual(stats_admin.ppc_clicks_total(tr), 2)            # by definition
        self.assertEqual(stats_admin.ppc_clicks_publisher(tr), 2)        # incl. invalid
        self.assertEqual(stats_admin.ppc_clicks_apprl(tr), 0)

        self.assertEqual(stats_admin.ppo_clicks_total(tr), 4)            # by definition
        self.assertEqual(stats_admin.ppo_clicks_publisher(tr), 3)        # incl. invalid
        self.assertEqual(stats_admin.ppo_clicks_apprl(tr), 1)

        self.assertEqual(stats_admin.ppo_sales_total(tr), 2)
        self.assertEqual(stats_admin.ppo_sales_publisher(tr), 1)
        self.assertEqual(stats_admin.ppo_sales_apprl(tr), 1)

        self.assertEqual(stats_admin.commission_cr_total(tr), D(2) / D(4))         # 2/4 (ppo sales tot / ppo clicks tot)
        self.assertEqual(stats_admin.commission_cr_publisher(tr), D(1) / D(3))     # 1/3 (ppo sales pub / ppo clicks pub)
        self.assertEqual(stats_admin.commission_cr_apprl(tr), D(1) / D(1))         # 1/3 (ppo sales apprl / ppo clicks apprl)

        self.assertEqual(stats_admin.average_epc_total(tr), D(225) / 6)         # 5+100+120 (ppx commission) / 2+4 (ppx clicks incl. invalid)
        self.assertEqual(stats_admin.average_epc_ppc(tr), 2.5)               # 5/2 (ppc commission / ppc clicks)
        self.assertEqual(stats_admin.average_epc_ppo(tr), D(220) / 4)           # 100+120/3 (ppo commission / ppo clicks)

        self.assertEqual(stats_admin.valid_clicks_total(tr), 4)
        self.assertEqual(stats_admin.valid_clicks_ppc(tr), 1)
        self.assertEqual(stats_admin.valid_clicks_ppo(tr), 3)

        self.assertEqual(stats_admin.invalid_clicks_total(tr), 2)
        self.assertEqual(stats_admin.invalid_clicks_ppc(tr), 1)
        self.assertEqual(stats_admin.invalid_clicks_ppo(tr), 1)

        self.assertEqual(stats_admin.ppc_all_stores_publishers_income(tr), 100 + 5)
        self.assertEqual(stats_admin.ppc_all_stores_publishers_cost(tr), 6 + 3)
        self.assertEqual(stats_admin.ppc_all_stores_publishers_result(tr), 96)    # by definition

    def test_top_stats_normal_publisher(self):

        # Create users

        publisher = self.create_users(ppc_as=False, create_referral_partner=True)

        # Create stores / vendors. We only create AAN vendors because it allows us to control commission_percentage

        cpo_store = make(Store, vendor__is_cpo=True, vendor__is_cpc=False, vendor__name='cpo_v', commission_percentage='0.2')
        cpc_store = make(Store, vendor__is_cpc=True, vendor__is_cpo=False, vendor__name='cpc_v')
        make(ClickCost, vendor=cpc_store.vendor, amount=5)
        make(Cut, vendor=cpo_store.vendor, group=publisher.partner_group, cut=0.3, referral_cut=0.1)
        make(Cut, vendor=cpc_store.vendor, group=publisher.partner_group, cut=0.1, referral_cut=0.1)

        # Create clicks, both valid and invalid

        self.click(cpo_store, publisher, order_value=1000)   # with 20% commission = 200
        self.click(cpo_store, None, order_value=300)   # with 20% commission = 60 - all goes to Apprl
        self.click(cpo_store, publisher, invalidate_click=True, order_value=200)   # click shouldn't count, but sale goes through so we still get 20% commission - 40
        self.click(cpo_store, publisher)    # no cpo conversion

        self.click(cpc_store, publisher)    # vendor pays 5 - publisher gets 0.5 (10% cut)
        self.click(cpc_store, None)         # vendor pays 5 - apprl gets all of it
        self.click(cpc_store, publisher, invalidate_click=True)   # click shouldn't count it is invalid
        self.click(cpc_store, publisher=publisher, date_out_of_range=True)   # this one shouldn't count in stats since it's out of range

        # Collect clicks, generate sales & user earnings.

        self.collect_clicks()

        # Test it!

        tr = mrange(self.test_year, self.test_month)

        self.assertEqual(stats_admin.earnings_total(tr), 310)    # 200 + 60 + 40 commission from cpo sales + 5 + 5 cpc
        self.assertEqual(stats_admin.earnings_publisher(tr), 72 + 0.5)  # (200 + 40)*0.3 + 5*0.1
        self.assertEqual(stats_admin.earnings_apprl(tr), 310 - 72.5)  # defined as total - publisher

        # Referral cuts are wrongly calculated on sale commission, should be based on publisher
        # earnings. https://www.pivotaltracker.com/n/projects/243709
        self.assertEqual(stats_admin.referral_earnings_total(tr), 0)         # by definition
        self.assertEqual(stats_admin.referral_earnings_publisher(tr), 74.5)  # 50 (default signup bonus) + 10% (defined in Cuts) of 200+40+5.
        self.assertEqual(stats_admin.referral_earnings_apprl(tr), -74.5)     # -publisher earnings by definition

        self.assertEqual(stats_admin.ppo_commission_total(tr), 300)       # 200 + 60 + 40
        self.assertEqual(stats_admin.ppo_commission_publisher(tr), 0)    # by definition
        self.assertEqual(stats_admin.ppo_commission_apprl(tr), 0)        # by definition

        self.assertEqual(stats_admin.ppc_commission_total(tr), 10)        # 1 click to ppc store
        self.assertEqual(stats_admin.ppc_commission_publisher(tr), 0)    # by definition
        self.assertEqual(stats_admin.ppc_commission_apprl(tr), 0)        # by definition

        self.assertEqual(stats_admin.ppc_clicks_total(tr), 3)            # by definition
        self.assertEqual(stats_admin.ppc_clicks_publisher(tr), 2)        # incl. invalid
        self.assertEqual(stats_admin.ppc_clicks_apprl(tr), 1)

        self.assertEqual(stats_admin.ppo_clicks_total(tr), 4)            # by definition
        self.assertEqual(stats_admin.ppo_clicks_publisher(tr), 3)        # incl. invalid
        self.assertEqual(stats_admin.ppo_clicks_apprl(tr), 1)

        self.assertEqual(stats_admin.ppo_sales_total(tr), 3)
        self.assertEqual(stats_admin.ppo_sales_publisher(tr), 2)
        self.assertEqual(stats_admin.ppo_sales_apprl(tr), 1)

        self.assertEqual(stats_admin.commission_cr_total(tr), D(3) / D(4))         # 3/4 (ppo sales tot / ppo clicks tot)
        self.assertEqual(stats_admin.commission_cr_publisher(tr), D(2) / D(3))     # 2/3 (ppo sales pub / ppo clicks pub)
        self.assertEqual(stats_admin.commission_cr_apprl(tr), D(1) / D(1))         # 1/3 (ppo sales apprl / ppo clicks apprl)

        self.assertEqual(stats_admin.average_epc_total(tr), D(310) / 7)         # (ppx commission) / (ppx clicks incl. invalid)
        self.assertEqual(stats_admin.average_epc_ppc(tr), D(10) / 3)               # (ppc commission / ppc clicks)
        self.assertEqual(stats_admin.average_epc_ppo(tr), D(300) / 4)           # (ppo commission / ppo clicks)

        self.assertEqual(stats_admin.valid_clicks_ppc(tr), 2)
        self.assertEqual(stats_admin.valid_clicks_ppo(tr), 3)

        self.assertEqual(stats_admin.invalid_clicks_total(tr), 2)
        self.assertEqual(stats_admin.invalid_clicks_ppc(tr), 1)
        self.assertEqual(stats_admin.invalid_clicks_ppo(tr), 1)

        self.assertEqual(stats_admin.ppc_all_stores_publishers_income(tr), 0)
        self.assertEqual(stats_admin.ppc_all_stores_publishers_cost(tr), 0)
        self.assertEqual(stats_admin.ppc_all_stores_publishers_result(tr), 0)

    def test_all_stores_stats(self):

        # Create users

        ppc_as_publisher = self.create_users(ppc_as=True, create_referral_partner=True)
        normal_publisher = self.create_users(ppc_as=False, create_referral_partner=True)

        # Create stores / vendors. We only create AAN vendors because it allows us to control commission_percentage

        cpo_store = make(Store, vendor__is_cpo=True, vendor__is_cpc=False, vendor__name='cpo_v', commission_percentage='0.2')
        make(Cut, vendor=cpo_store.vendor, group=ppc_as_publisher.partner_group, cut=0, cpc_amount=3, referral_cut=0.1)

        cpo_store_2 = make(Store, vendor__is_cpo=True, vendor__is_cpc=False, vendor__name='cpo_v_2', commission_percentage='0.2')
        make(Cut, vendor=cpo_store_2.vendor, group=ppc_as_publisher.partner_group, cut=0, cpc_amount=5, referral_cut=0.1)

        cpc_store = make(Store, vendor__is_cpc=True, vendor__is_cpo=False, vendor__name='cpc_v')
        make(Cut, vendor=cpc_store.vendor, group=ppc_as_publisher.partner_group, cut=0, cpc_amount=3, referral_cut=0.1)
        make(ClickCost, vendor=cpc_store.vendor, amount=5)

        # Create clicks, both valid and invalid

        self.click(cpo_store, ppc_as_publisher, order_value=500)   # with 20% commission = 100. 3 to ppc_as publisher
        self.click(cpo_store, None, order_value=600)   # with 20% commission = 120 - all goes to Apprl
        self.click(cpo_store, ppc_as_publisher, invalidate_click=True)   # click shouldn't count
        self.click(cpo_store, ppc_as_publisher)    # no cpo conversion, but ppc_as publisher still gets 3

        self.click(cpo_store_2, ppc_as_publisher, order_value=1000)   # with 20% commission = 200. 5 to ppc_as publisher

        self.click(cpc_store, ppc_as_publisher)    # 3 to ppc_as publisher. vendor pays 5
        self.click(cpc_store, ppc_as_publisher, invalidate_click=True)   # shouldn't count
        self.click(cpc_store, ppc_as_publisher, date_out_of_range=True)   # this one shouldn't count in stats since it's out of range

        self.click(cpo_store, normal_publisher, order_value=300)   # this shouldn't count for these stats

        # Collect clicks, generate sales & user earnings.

        self.collect_clicks()

        # Test it!

        tr = mrange(self.test_year, self.test_month)

        vendor_stats = stats_admin.ppc_all_stores_publishers_by_vendor(tr)
        self.assertEqual(set(vendor_stats.keys()), set(['cpo_v', 'cpo_v_2', 'cpc_v']))
        self.assertEqual(vendor_stats['cpo_v']['income'], 100)          # the vendor pays us 100 commission
        self.assertEqual(vendor_stats['cpo_v']['cost'], 3+3)            # two payouts with 3
        self.assertEqual(vendor_stats['cpo_v']['result'], 94)           # income - cost

        self.assertEqual(vendor_stats['cpc_v']['income'], 5)            # the vendor pays us 5 for the click
        self.assertEqual(vendor_stats['cpc_v']['cost'], 3)              # we pay ppc as publisher 3
        self.assertEqual(vendor_stats['cpc_v']['result'], 2)            # income - cost

        self.assertEqual(stats_admin.ppc_all_stores_publishers_income(tr), 100 + 200 + 5)
        self.assertEqual(stats_admin.ppc_all_stores_publishers_cost(tr), 3 + 3 + 5 + 3)
        self.assertEqual(stats_admin.ppc_all_stores_publishers_result(tr), 305 - 14)


class TestStatsPublisher(TestStats):

    def test_top_stats_ppc_as_publisher(self):

        # Create users

        publisher = self.create_users(ppc_as=True)

        # Create stores / vendors. We only create AAN vendors because it allows us to control commission_percentage

        cpo_store = make(Store, vendor__is_cpo=True, vendor__is_cpc=False, vendor__name='cpo_v', commission_percentage='0.2')
        make(Cut, vendor=cpo_store.vendor, group=publisher.partner_group, cut=0, cpc_amount=40, referral_cut=0.1)

        cpc_store = make(Store, vendor__is_cpc=True, vendor__is_cpo=False, vendor__name='cpc_v')
        # Note the high cpc_amount, we want to get up to APPAREL_DASHBOARD_MINIMUM_PAYOUT with just a few clicks
        make(Cut, vendor=cpc_store.vendor, group=publisher.partner_group, cut=0, cpc_amount=40, referral_cut=0.1)
        make(ClickCost, vendor=cpc_store.vendor, amount=5)

        # Create clicks, both valid and invalid

        self.click(cpc_store, publisher)    # 40 to ppc_as publisher. vendor pays 5
        self.click(cpc_store, publisher)    # 40 to ppc_as publisher. vendor pays 5
        self.click(cpo_store, publisher)    # 40 to ppc_as publisher. vendor pays 5

        self.collect_clicks()

        # Test it!

        tr = mrange(self.test_year, self.test_month)
        self.assertEqual(stats_publisher.ppc_earnings(tr, publisher.id), 120)
        self.assertEqual(stats_publisher.ppo_earnings(tr, publisher.id), 0)
        self.assertEqual(stats_publisher.total_earnings(tr, publisher.id), 120)

        self.assertEqual(stats_publisher.pending_earnings(publisher.id), 120)
        # At this point, we don't have any confirmed earnings
        self.assertEqual(stats_publisher.confirmed_earnings(publisher.id), 0)

        # We won't create any payments for this publisher at this point because the clicks
        # haven't been confirmed. This happens automatically by update_clicks_earnings_status at a later point
        management.call_command('dashboard_payment', verbosity=0, interactive=False)
        self.assertEqual(stats_publisher.total_paid(publisher.id), 0)

        two_months_later = datetime.date(self.test_year, self.test_month, 1) + relativedelta(months=2)
        with freeze_time(two_months_later):
            management.call_command('update_clicks_earnings_status', verbosity=0, interactive=False)

            # now that sufficiently long time has passed, the earnings should be confirmed
            self.assertEqual(stats_publisher.confirmed_earnings(publisher.id), 120)

            # but we haven't paid the publisher yet
            self.assertEqual(stats_publisher.total_paid(publisher.id), 0)

            # we generate a payment for the user
            management.call_command('dashboard_payment', verbosity=0, interactive=False)

            self.assertEqual(stats_publisher.pending_payments(publisher.id), 120)

            # since the earnings have payment status PAID_PENDING, this should be 0
            self.assertEqual(stats_publisher.pending_earnings(publisher.id), 0)
            self.assertEqual(stats_publisher.confirmed_earnings(publisher.id), 0)

            # this will be 0 until somebody marks it as paid
            self.assertEqual(stats_publisher.total_paid(publisher.id), 0)

            # pay the publisher
            payment = Payment.objects.get(user_id=publisher.id)
            self.assertFalse(payment.paid)
            self.assertFalse(payment.cancelled)
            payment.mark_as_paid()

            # this should cause user to be paid, confirmed earnings & pending earnings should be back to 0
            self.assertEqual(stats_publisher.total_paid(publisher.id), 120)
            self.assertEqual(stats_publisher.pending_payments(publisher.id), 0)


@override_settings(CELERY_EAGER_PROPAGATES_EXCEPTIONS=True, CELERY_ALWAYS_EAGER=True, BROKER_BACKEND='memory')
class TestStatsCache(TransactionTestCase):

    def setUp(self):
        stats_redis.flushall()

    def test_stats_caching(self):
        @stats_cache
        def foo(time_range):
            return testval

        testval = 1
        self.assertEqual(foo(mrange(2016, 8)), 1)

        self.assertEqual(
            set(stats_redis.keys('*')),
            set([cache_key(mrange(2016, 8), 'foo'), 'stats_ranges_right', 'stats_ranges_left'])
        )

        testval = 2
        self.assertEqual(foo(mrange(2016, 8)), 1)   # old value should be returned

        flush_stats_cache()
        testval = 3
        self.assertEqual(foo(mrange(2016, 8)), 3)   # cache flushed so function returns new value

        flush_stats_cache_by_year(2016)
        testval = 4
        self.assertEqual(foo(mrange(2016, 8)), 4)   # cache flushed so function returns new value

        flush_stats_cache_by_year(2017)
        testval = 5
        self.assertEqual(foo(mrange(2016, 8)), 4)   # cache flushed outside range so function retains previous value

        flush_stats_cache_by_month(2016, 8)
        testval = 6
        self.assertEqual(foo(mrange(2016, 8)), 6)   # cache flushed - new value

        flush_stats_cache_by_month(2016, 9)
        testval = 7
        self.assertEqual(foo(mrange(2016, 8)), 6)   # cache flushed outside range - function retains previous value

    def test_different_functions_caching(self):
        @stats_cache
        def foo(time_range):
            return testval

        @stats_cache
        def bar(time_range):
            return testval

        testval = 1
        self.assertEqual(foo(mrange(2016, 8)), 1)
        testval = 2
        self.assertEqual(bar(mrange(2016, 8)), 2)

        testval = 3
        self.assertEqual(foo(mrange(2016, 8)), 1)   # should retain cached value
        self.assertEqual(bar(mrange(2016, 8)), 2)   # should retain cached value

        self.assertEqual(
            set(stats_redis.keys('*')),
            {
                cache_key(mrange(2016, 8), 'foo'),
                cache_key(mrange(2016, 8), 'bar'),
                'stats_ranges_right',
                'stats_ranges_left'
            }
        )

    def test_different_arguments_caching(self):
        @stats_cache
        def foo(time_range, param):
            return testval

        testval = 1
        self.assertEqual(foo(mrange(2016, 8), 666), 1)
        testval = 2
        self.assertEqual(foo(mrange(2016, 8), 777), 2)

        testval = 3
        self.assertEqual(foo(mrange(2016, 8), 666), 1)   # should retain cached value
        self.assertEqual(foo(mrange(2016, 8), 777), 2)   # should retain cached value

        self.assertEqual(
            set(stats_redis.keys('*')),
            {
                cache_key(mrange(2016, 8), 'foo', (666)),
                cache_key(mrange(2016, 8), 'foo', (777)),
                'stats_ranges_right',
                'stats_ranges_left'
            }
        )

    def test_sales_changes_should_flush_cache(self):
        publisher = make(get_user_model(), is_partner=True, partner_group__has_cpc_all_stores=False)
        cpo_store = make(Store, vendor__is_cpo=True, vendor__is_cpc=False, vendor__name='cpo_v')
        make(Cut, vendor=cpo_store.vendor, group=publisher.partner_group)

        sale = make(Sale, sale_date=datetime.date(2016, 8, 1), user_id=publisher.pk, vendor=cpo_store.vendor, converted_commission=100, status=Sale.PENDING)
        self.assertEqual(stats_admin.ppo_commission_total(mrange(2016, 8)), 100)

        sale.converted_commission = 200
        sale.save()
        self.assertEqual(stats_admin.ppo_commission_total(mrange(2016, 8)), 200)

    def test_time_range_validations(self):
        @stats_cache
        def foo(time_range, param):
            pass

        with self.assertRaises(ValueError):
            foo(666)

        with self.assertRaises(ValueError):
            foo([datetime.datetime(2012, 11, 11)], 666)     # only one val

        with self.assertRaises(ValueError):
            foo([datetime.datetime(1888, 11, 11), datetime.datetime(2011, 11, 12)], 666)    # too low

        with self.assertRaises(ValueError):
            foo([datetime.datetime(3111, 11, 11), datetime.datetime(3111, 11, 12)], 666)    # too high
