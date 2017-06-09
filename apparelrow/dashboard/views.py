import operator
import re

import simplejson
from django.contrib import messages
from django.contrib.sites.models import Site
from django.forms import ModelForm
from django.http import HttpResponseRedirect, HttpResponseNotFound, Http404, HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.translation import get_language
from django.views.generic import TemplateView

from apparelrow.apparel.models import Vendor, Product
from apparelrow.apparel.utils import get_location
from apparelrow.dashboard.models import Sale, Payment, Signup, AggregatedData, Group, Cut, ClickCost, StoreCommission, \
    UserEarning
from apparelrow.dashboard.stats import stats_admin, stats_publisher
from apparelrow.dashboard.stats.stats_cache import all_time, mrange, flush_stats_cache_by_month
from apparelrow.dashboard.tasks import send_email_task
from apparelrow.dashboard.utils import *
from apparelrow.profile.tasks import mail_managers_task

logger = logging.getLogger(__name__)

TOP_PRODUCTS_LIMIT = 100


def map_placement(placement):
    link = _('Unknown')
    if placement == 'Ext-Shop':
        link = _('Shop on your site')
    elif placement == 'Ext-Look':
        link = _('Look on your site')
    elif placement == 'Ext-Link':
        link = _('Product link on your site')
    elif placement == 'Ext-Store':
        link = _('Store link on your site')
    elif placement == 'Look':
        link = _('Look on Apprl.com')
    elif placement == 'Shop':
        link = _('Shop on Apprl.com')
    elif placement == 'Feed':
        link = _('Feed on Apprl.com')
    elif placement == 'Profile':
        link = _('Your profile on Apprl.com')
    elif placement == 'Product':
        link = _('Product page')
    elif placement == 'Ext-Banner':
        link = _('Banner on your site')
    return link


class SignupForm(ModelForm):
    def __init__(self, *args, **kwargs):
        is_store_form = False
        if 'is_store_form' in kwargs:
            is_store_form = True
            del kwargs['is_store_form']

        super(SignupForm, self).__init__(*args, **kwargs)

        if is_store_form:
            self.fields['blog'].label = 'Store URL'
        else:
            self.fields['blog'].label = 'URL'

    class Meta:
        model = Signup
        fields = ('name', 'email', 'blog', 'traffic')


def dashboard_group_admin(request, pk):
    if request.user.is_authenticated() and (request.user.is_superuser or request.user.pk == int(pk)):
        group = None
        try:
            group = Group.objects.get(owner=pk)
        except:
            raise Http404

        users = []
        for user in get_user_model().objects.filter(partner_group__owner=pk, is_partner=True):
            sales_total = decimal.Decimal('0')
            sales_pending = Sale.objects.filter(user_id=user.pk, status=Sale.PENDING,
                                                paid=Sale.PAID_PENDING).aggregate(total=Sum('commission'))['total']
            if sales_pending:
                sales_total += sales_pending
            else:
                sales_pending = decimal.Decimal('0')
            sales_confirmed = Sale.objects.filter(user_id=user.pk, status=Sale.CONFIRMED,
                                                  paid=Sale.PAID_PENDING).aggregate(total=Sum('commission'))['total']
            if sales_confirmed:
                sales_total += sales_confirmed
            else:
                sales_confirmed = decimal.Decimal('0')

            # Pending payment
            pending_payment = 0
            payments = Payment.objects.filter(cancelled=False, paid=False, user=user).order_by('-created')
            if payments:
                pending_payment = payments[0].amount

            users.append({
                'user': user,
                'total': sales_total,
                'confirmed': sales_confirmed,
                'pending_payment': pending_payment,
            })

        sum_total = sum(user['total'] for user in users)
        sum_confirmed = sum(user['confirmed'] for user in users)
        sum_pending_payment = sum(user['pending_payment'] for user in users)

        owner = get_user_model().objects.get(pk=pk)
        owner_total = sum_total * group.owner_cut
        owner_confirmed = sum_confirmed * group.owner_cut
        owner_pending_payment = sum_confirmed * group.owner_cut

        context = {
            'users': users,
            'owner': owner,
            'sum_total': sum_total,
            'sum_confirmed': sum_confirmed,
            'sum_pending_payment': sum_pending_payment,
            'owner_total': owner_total,
            'owner_confirmed': owner_confirmed,
            'owner_pending_payment': owner_pending_payment,
            'total_total': sum_total + owner_total,
            'total_confirmed': sum_confirmed + owner_confirmed,
            'total_pending_payment': sum_pending_payment + owner_pending_payment,
        }

        return render(request, 'dashboard/publisher_group.html', context)

    raise Http404


def dashboard_info(request):
    return render(request, 'dashboard/info.html')


#
# Referral
#
def referral_signup(request, code):
    user_id = None
    try:
        user = get_user_model().objects.get(referral_partner_code=code)
        user_id = user.pk
    except:
        pass
    response = redirect(reverse('publisher-contact'))
    if user_id:
        expires_datetime = timezone.now() + datetime.timedelta(days=15)
        response.set_signed_cookie(settings.APPAREL_DASHBOARD_REFERRAL_COOKIE_NAME, user_id, expires=expires_datetime,
                                   httponly=True)

    return response


class ReferralView(TemplateView):
    template_name = 'dashboard/referral.html'

    def get_context_data(self, **kwargs):
        context = super(ReferralView, self).get_context_data(**kwargs)
        context["referrals"] = get_user_model().objects.filter(referral_partner_parent=self.request.user,
                                                               is_partner=True)
        return context

    def get(self, request, *args, **kwargs):

        if request.user.is_authenticated() and all([request.user.is_partner, request.user.referral_partner]):
            context = self.get_context_data(**kwargs)
            return render(request, self.template_name, context)
        else:
            return HttpResponseRedirect(reverse('index-publisher'))

    def post(self, request, *args, **kwargs):
        emails = request.POST.get('emails')
        emails = re.split(r'[\s,]+', emails)

        referral_code = request.user.get_referral_domain_url()
        referral_name = request.user.display_name
        referral_email = request.user.email
        referral_language = get_language()

        template = 'dashboard/referral_mail_en.html'
        # TODO: fix when we have swedish email
        #if referral_language == 'sv':
            #template = 'dashboard/referral_mail_sv.html'

        # Get user avatar
        if request.user.image or request.user.facebook_user_id:
            profile_photo_url = request.user.avatar_circular_large
        else:
            profile_photo_url = staticfiles_storage.url(settings.APPAREL_DEFAULT_AVATAR_LARGE_CIRCULAR)

        for email in emails:
            send_email_task.delay(email, referral_name, referral_code, profile_photo_url)
        messages.add_message(request, messages.SUCCESS, u'Sent mail to %s' % (', '.join(emails),))
        return render(request, self.template_name)


#
# Commissions
#
def get_store_earnings(user, vendor_obj, publisher_cut, normal_cut, standard_from, store):
    """
    Return earnings for given store and user, and any other additional information. This is mainly used in Stores
    commissions page.
    """
    currency = ''
    amount_float = decimal.Decimal(0)
    amount = "%.2f" % amount_float
    earning_type = "is_cpo"  # Default is_cpo = True for vendors

    CPC_CODE = 0
    CPO_CODE = 1
    cut = None

    # Retrieve cut object
    try:
        cut = Cut.objects.get(group=user.partner_group, vendor=vendor_obj)
    except Cut.DoesNotExist:
        logger.warning("Cut for commission group %s and vendor %s does not exist." %
                       (user.partner_group, vendor_obj.name))

    type_code = CPC_CODE
    if cut:
        if user.partner_group.has_cpc_all_stores:
            # For Publishers who earns CPC for all stores, cut is 100% unless exceptions are defined
            normal_cut = 1
            type_code = CPC_CODE
            earning_type = "is_cpc"
            earning_amount = cut.locale_cpc_amount
            currency = cut.locale_cpc_currency
            # Get exceptions and if they are defined, replace current cuts
            if cut.rules_exceptions:
                cut_exception, publisher_cut_exception, click_cost = parse_rules_exception(cut.rules_exceptions,
                                                                                           user.id)
                if cut_exception:
                    normal_cut = cut_exception
                if publisher_cut_exception is not None and user.owner_network:
                    publisher_cut = publisher_cut_exception
            publisher_earning = decimal.Decimal(earning_amount * (normal_cut * publisher_cut))
            amount_float = decimal.Decimal(
                publisher_earning.quantize(decimal.Decimal('.01'), rounding=decimal.ROUND_HALF_UP))
            amount = "%.2f" % (amount_float)
        else:
            if vendor_obj.is_cpc:
                click_cost = ClickCost.objects.get(vendor=vendor_obj)
                earning_amount = click_cost.locale_price
                currency = click_cost.locale_currency
                earning_type = "is_cpc"

                # Get click cost from exceptions if defined
                _, _, click_cost_exception = parse_rules_exception(cut.rules_exceptions, user.id)
                exception_amount, exception_currency = parse_cost_amount(click_cost_exception)
                if exception_amount and exception_currency:
                    earning_amount = exception_amount
                    currency = exception_currency

                amount = "%.2f" % (earning_amount * publisher_cut * normal_cut)
                amount_float = earning_amount * publisher_cut * normal_cut
            elif vendor_obj.is_cpo:
                amount = store.commission
                amount_float = standard_from
            type_code = CPC_CODE if earning_type == "is_cpc" else CPO_CODE

    return amount, amount_float, currency, earning_type, type_code


def commissions(request):
    if not request.user.is_authenticated() or not request.user.is_partner:
        logger.error('Unauthorized user trying to access store commission page. Returning 404.')
        raise Http404

    if not request.user.partner_group:
        logger.error('User %s is partner but has no partner group. Disallowing viewing of store commissions page.'
                     % request.user)
        raise Http404

    cookie_value = get_location(request)
    vendors = get_available_stores(cookie_value)
    user_id = request.user.id
    stores = {}
    for vendor in vendors:
        try:
            temp = {}
            vendor_obj = Vendor.objects.get(name=vendor)
            store = StoreCommission.objects.get(vendor=vendor_obj)

            cuts_for_user_vendor = get_cuts_for_user_and_vendor(user_id, store.vendor)
            standard_from = 0 if not store else store.get_standard_from(store.commission, *cuts_for_user_vendor)
            store.calculated_commissions(store.commission, *cuts_for_user_vendor)
            temp['vendor_pk'] = vendor_obj.pk
            temp['vendor_name'] = vendor_obj.name
            temp['link'] = store.link
            temp['store_pk'] = store.pk

            # Get different cuts
            _, normal_cut, _, publisher_cut = get_cuts_for_user_and_vendor(user_id, vendor_obj)
            temp['amount'], temp['amount_float'], temp['currency'], temp['earning_type'], temp['type_code'] = \
                get_store_earnings(request.user, vendor_obj, publisher_cut, normal_cut, standard_from, store)

            stores[vendor] = temp
        except ClickCost.DoesNotExist:
            logger.warning("ClickCost for vendor %s does not exist" % vendor)
        except StoreCommission.DoesNotExist:
            logger.warning("StoreCommission for vendor %s does not exist" % vendor)
    stores = [x for x in sorted(stores.values(), key=lambda x: (x['type_code'], -x['amount_float'], x['vendor_name']))]

    sort_index = 0
    for row in stores:
        row['sort_index'] = sort_index
        sort_index += 1

    return render(request, 'dashboard/commissions.html', {'stores': stores})


def commissions_popup(request, pk):
    if not request.user.is_authenticated() or not request.user.is_partner:
        raise Http404

    store = get_object_or_404(StoreCommission, pk=pk)
    link = None
    if store.link:
        link = '{}{}/'.format(store.link, request.user.pk)

    return render(request, 'dashboard/commissions_popup.html', {'link': link, 'name': store.vendor.name})


#
# Publisher / Store signup
#
def index_complete(request, view):
    analytics_identifier = 'Publisher'
    if view == 'store':
        analytics_identifier = 'Store'

    return render(request, 'dashboard/publisher_complete.html', {'analytics_identifier': analytics_identifier})



def index(request):
    return render(request, 'dashboard/index.html')


def publisher_contact(request):
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            # Save name and blog URL on session, for Google Analytics
            request.session['index_complete_info'] = u"%s %s" % (form.cleaned_data['name'], form.cleaned_data['blog'])
            instance = form.save(commit=False)
            instance.referral_user = get_referral_user_from_cookie(request)
            instance.save()

            if instance.referral_user:
                site_object = Site.objects.get_current()
                referral_user_url = 'http://%s%s' % (site_object.domain, instance.referral_user.get_absolute_url())

                mail_managers_task.delay('New publisher signup by referral: %s' % (form.cleaned_data['name'],),
                        'Name: %s\nEmail: %s\nBlog: %s\nReferral User: %s - %s\n' % (form.cleaned_data['name'],
                                                           form.cleaned_data['email'],
                                                           form.cleaned_data['blog'],
                                                           instance.referral_user.display_name,
                                                           referral_user_url))
            else:
                mail_managers_task.delay('New publisher signup: %s' % (form.cleaned_data['name'],),
                        'Name: %s\nEmail: %s\nBlog: %s' % (form.cleaned_data['name'],
                                                           form.cleaned_data['email'],
                                                           form.cleaned_data['blog']))

            return HttpResponseRedirect(reverse('index-dashboard-complete'))
    else:
        form = SignupForm()

    referral_user = get_referral_user_from_cookie(request)

    return render(request, 'dashboard/publisher_contact.html', {'form': form, 'referral_user': referral_user})


def publisher_tools(request):
    return render(request, 'dashboard/publisher_tools.html')


def clicks_detail(request):
    """
    Return a list of click details given an user, vendor and date
    """
    if request.method == 'GET' and request.is_ajax():
        user_id = request.GET.get('user_id', None)
        vendor = request.GET.get('vendor', None)
        currency = request.GET.get('currency', 'EUR')
        is_store = request.GET.get('is_store', False)
        num_clicks = request.GET.get('clicks', 0)
        try:
            amount_for_clicks = request.GET.get('amount', "0").replace(',', '.')
        except:
            amount_for_clicks = "0"

        if num_clicks > 0:
            click_cost = decimal.Decimal(amount_for_clicks) / int(num_clicks)
            query_date = datetime.datetime.fromtimestamp(int(request.GET['date']))
            data = get_clicks_list(vendor, query_date, currency, click_cost, user_id, is_store)
            json_data = json.dumps(data)
            return HttpResponse(json_data)
        else:
            return HttpResponse(simplejson.dumps([]))
    else:
        return HttpResponseForbidden()
    # If therese nothing just return empty list
    return HttpResponse(simplejson.dumps([]))


#
# PUBLISHER DASHBOARD
#
class DashboardView(TemplateView):
    template_name = "dashboard/new_dashboard.html"

    def get(self, request, *args, **kwargs):
        currency = 'EUR'
        month = None if not 'month' in self.kwargs else self.kwargs['month']
        year = None if not 'year' in self.kwargs else self.kwargs['year']

        if not (request.user.is_authenticated() and request.user.is_partner):
            raise Http404()

        if 'stats' in request.GET:
            # quick hack to get the cli stats to web
            return HttpResponse('<html><pre>%s</pre></html>' % stats_publisher.publisher_stats_as_str(request.user.id))

        start_date, end_date = parse_date(month, year)
        year = start_date.year
        if month != "0":
            month = start_date.month

        flush_cache = 'flush_cache' in self.request.GET
        if flush_cache:
            flush_stats_cache_by_month(year, month)  # improve this so it only flushes cache for this publisher

        start_date_query = datetime.datetime.combine(start_date, datetime.time(0, 0, 0, 0))
        end_date_query = datetime.datetime.combine(end_date, datetime.time(23, 59, 59, 999999))
        month_display, month_choices, year_choices = enumerate_months(request.user, month)

        # Determine if the user is the owner of a publisher network
        is_owner = get_user_model().objects.filter(owner_network=request.user).exists()
        # Enable sales listing after 2013-06-01 00:00:00
        is_after_june = False if (year <= 2013 and month <= 5) and not request.GET.get('override') else True

        # Total summary for user
        payment_stats = self.payments_stats(request.user.id)

        # Get aggregated data per day
        values = ('created', 'sale_earnings', 'referral_earnings', 'click_earnings', 'total_clicks',
                  'network_sale_earnings', 'network_click_earnings')
        query_args = {'user_id': request.user.id, 'created__range': (start_date_query, end_date_query),
                      'data_type': 'aggregated_from_total'}

        data_per_day = aggregated_data_per_day(start_date, end_date, 'publisher', values, query_args)

        # Aggregate publishers per month
        top_publishers = get_aggregated_publishers(request.user.id, start_date_query, end_date_query,
                                                   include_all_network_influencers=True)

        # Aggregate products per month
        top_products = get_aggregated_products(request.user.id, start_date_query, end_date_query, TOP_PRODUCTS_LIMIT)

        month_stats = self.month_stats(year, month, request.user.id)

        show_cpo_earning = True
        if request.user.has_ppc_all_stores() and not month_stats['ppo_earnings']:
            show_cpo_earning = False

        # It doesn't make sense to show earnings to publishers that are ppc all stores
        show_latest_earnings = not request.user.has_ppc_all_stores()

        context_data = {'year_choices': year_choices, 'month_choices': month_choices,
                        'data_per_day': data_per_day, 'currency': currency,
                        'month_stats': month_stats,
                        'payment_stats': payment_stats,
                        'year': year,
                        'month': month, 'month_display': month_display,
                        'is_owner': is_owner, 'is_after_june': is_after_june,
                        'top_publishers': top_publishers,
                        'top_products': top_products,
                        'show_latest_earnings': show_latest_earnings,
                        'TOP_PRODUCTS_LIMIT': TOP_PRODUCTS_LIMIT,
                        'show_cpo_earning': show_cpo_earning,
                        'show_aggregated_data': True, # request.GET.get('show_aggregated_data')
                        }
        return render(request, 'dashboard/new_dashboard.html', context_data)

    def payments_stats(self, user_id):
        return {
            'pending_earnings': stats_publisher.pending_earnings(user_id),
            'confirmed_earnings': stats_publisher.confirmed_earnings(user_id),
            'pending_payments': stats_publisher.pending_payments(user_id),
            'total_paid': stats_publisher.total_paid(user_id)
        }

    def month_stats(self, year, month, user_id):
        tr = mrange(year, month)
        return {
            'total_earnings': stats_publisher.total_earnings(tr, user_id),
            'ppo_earnings': stats_publisher.ppo_earnings(tr, user_id),
            'ppo_sales': stats_publisher.ppo_sales(tr, user_id),
            'ppo_clicks': stats_publisher.ppo_clicks(tr, user_id),
            'ppo_conversion_rate': stats_publisher.ppo_conversion_rate(tr, user_id),
            'referral_earnings': stats_publisher.referral_earnings(tr, user_id),
            'referral_sales': stats_publisher.referral_sales(tr, user_id),
            'ppc_earnings': stats_publisher.ppc_earnings(tr, user_id),
            'ppc_clicks': stats_publisher.ppc_clicks(tr, user_id),
            'network_commission': stats_publisher.network_earnings(tr, user_id),
        }

#
# ADMIN DASHBOARD
#
class AdminDashboardView(TemplateView):
    template_name = "dashboard/new_admin.html"

    def get_admin_top_summary(self, year, month):
        top_stats = stats_admin.admin_top_stats(year, month, self.flush_cache)
        top_stats = [r[1:] for r in top_stats]  # get rid of headers

        clicks_stats = stats_admin.admin_clicks(year, month, self.flush_cache)
        clicks_stats = [r[1:] for r in clicks_stats]  # get rid of headers
        return top_stats, clicks_stats

    def get_admin_top_summary_old(self, start_date, end_date):
        """
            Returns matrix with Summary for the given period for Admin Dashboard
        """
        total_query = AggregatedData.objects.filter(created__range=(start_date, end_date),
                                                    data_type='aggregated_from_total')
        clicks_total = [0, 0, 0]
        clicks_ppc = [0, 0, 0]
        clicks_ppo = [0, 0, 0]

        # Get total summary
        total_top = [0, 0, 0, 0, 0, 0, 0, 0]
        apprl_top = [0, 0, 0, 0, 0, 0, 0, 0]
        publisher_top = [0, 0, 0, 0, 0, 0, 0, 0]

        if total_query.exists():
            total_data = total_query.aggregate(sale_earnings=Sum('sale_earnings'), click_earnings=Sum('click_earnings'),
                                               sale_clicks=Sum('sale_plus_click_earnings'),
                                               paid_clicks=Sum('paid_clicks'),
                                               total_clicks=Sum('total_clicks'),
                                               referral_earnings=Sum('referral_earnings'),
                                               network_sale_earnings=Sum('network_sale_earnings'),
                                               network_click_earnings=Sum('network_click_earnings'), sales=Sum('sales'))
            total_earnings = total_data['sale_clicks'] + total_data['referral_earnings'] + \
                             total_data['network_sale_earnings'] + total_data['network_click_earnings']
            total_commission = total_data['sale_earnings'] + total_data['network_sale_earnings']
            total_ppc = total_data['click_earnings'] + total_data['network_click_earnings']
            total_top[0] = total_earnings
            total_top[1] = total_data['referral_earnings']
            total_top[2] = total_commission
            total_top[3] = total_ppc
            total_top[4] = total_data['paid_clicks']
            cpo_clicks = total_data['total_clicks'] - total_data['paid_clicks']
            total_top[5] = cpo_clicks
            total_top[6] = total_data['sales']
            total_top[7] = get_raw_conversion_rate(total_data['sales'],
                                                   total_data['total_clicks'] - total_data['paid_clicks'])

            # Calculate average earning per click
            if total_data['total_clicks'] > 0:
                clicks_total[0] = total_earnings / decimal.Decimal(total_data['total_clicks'])
            if total_data['paid_clicks'] > 0:
                clicks_ppc[0] = total_ppc / decimal.Decimal(total_data['paid_clicks'])
            if cpo_clicks > 0:
                clicks_ppo[0] = total_commission / decimal.Decimal(cpo_clicks)

            clicks_total[1] = total_data['total_clicks']
            clicks_ppc[1] = total_data['paid_clicks']
            clicks_ppo[1] = cpo_clicks

            # Get invalid clicks
            invalid_clicks = get_invalid_clicks(start_date, end_date)
            clicks_total[2] = invalid_clicks[0]
            clicks_ppc[2] = invalid_clicks[1]
            clicks_ppo[2] = invalid_clicks[2]

        # Get APPRL summary
        apprl_query = AggregatedData.objects. \
            filter(created__range=(start_date, end_date), user_id=0, data_type='aggregated_from_total')

        if apprl_query.exists():
            apprl_data = apprl_query.aggregate(sale_earnings=Sum('sale_earnings'), click_earnings=Sum('click_earnings'),
                                               sale_clicks=Sum('sale_plus_click_earnings'),
                                               paid_clicks=Sum('paid_clicks'),
                                               total_clicks=Sum('total_clicks'), sales=Sum('sales'))
            apprl_top[0] = apprl_data['sale_clicks']
            apprl_top[1] = 0.0  # APPRL does not get cut from referral earnings
            apprl_top[2] = apprl_data['sale_earnings']
            apprl_top[3] = apprl_data['click_earnings']
            apprl_top[4] = apprl_data['paid_clicks']
            apprl_top[5] = apprl_data['total_clicks'] - apprl_data['paid_clicks']
            apprl_top[6] = apprl_data['sales']
            apprl_top[7] = get_raw_conversion_rate(apprl_data['sales'],
                                                   apprl_data['total_clicks'] - apprl_data['paid_clicks'])

        # Get publisher summary
        publisher_query = AggregatedData.objects. \
            filter(created__range=(start_date, end_date), user_id__gt=0, data_type='aggregated_from_total')
        if publisher_query.exists():
            publisher_data = publisher_query.aggregate(sale_earnings=Sum('sale_earnings'),
                                                       click_earnings=Sum('click_earnings'),
                                                       sale_clicks=Sum('sale_plus_click_earnings'),
                                                       paid_clicks=Sum('paid_clicks'),
                                                       total_clicks=Sum('total_clicks'),
                                                       referral_earnings=Sum('referral_earnings'),
                                                       network_sale_earnings=Sum('network_sale_earnings'),
                                                       network_click_earnings=Sum('network_click_earnings'),
                                                       sales=Sum('sales'))
            publisher_total = publisher_data['sale_clicks'] + total_data['referral_earnings'] \
                              + total_data['network_sale_earnings'] + total_data['network_click_earnings']
            publisher_commission = publisher_data['sale_earnings'] + total_data['referral_earnings'] \
                                   + total_data['network_sale_earnings']
            publisher_ppc = publisher_data['click_earnings'] + publisher_data['network_click_earnings']
            publisher_top[0] = publisher_total
            publisher_top[1] = publisher_data['referral_earnings']
            publisher_top[2] = publisher_commission
            publisher_top[3] = publisher_ppc
            publisher_top[4] = publisher_data['paid_clicks']
            publisher_top[5] = publisher_data['total_clicks'] - publisher_data['paid_clicks']
            publisher_top[6] = publisher_data['sales']
            publisher_top[7] = get_raw_conversion_rate(publisher_data['sales'],
                                                       publisher_data['total_clicks'] - publisher_data['paid_clicks'])

        monthly_array = zip(total_top, publisher_top, apprl_top)
        clicks_array = zip(clicks_total, clicks_ppc, clicks_ppo)
        return monthly_array, clicks_array

    def get_admin_top_summary_display(self, summary, is_bottom_summary=False):
        """
        Returns list of lists ready for display from the given matrix with Summary data
        """
        headings = ['Earnings', 'Referral Earnings', 'PPO commission', 'PPC earnings', 'PPC clicks', 'PPO clicks',
                    'PPO sales',
                    'Commission CR']
        if is_bottom_summary:
            headings = ['Average EPC', 'Valid Clicks', 'Invalid clicks', 'Commission sales']
        top_summary_array = []
        for row in zip(headings, summary):
            temp_list = []
            heading = row[0]
            temp_list.append(heading)
            if heading in ('PPC clicks', 'PPO clicks', 'Valid Clicks', 'Invalid clicks', 'PPO sales'):
                for value, percentage in map(None, row[1][0], row[1][1]):
                    if not percentage:
                        percentage = "-"
                    temp_list.append("%s (%s)" % (value, percentage))
            elif heading is "Commission CR":
                for value, percentage in map(None, row[1][0], row[1][1]):
                    temp_list.append("%.2f%% (%s)" % (value, percentage))
            else:
                for value, percentage in map(None, row[1][0], row[1][1]):
                    if not percentage:
                        percentage = "-"
                    temp_list.append("EUR %.2f (%s)" % (value, percentage))
            top_summary_array.append(temp_list)
        return top_summary_array

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated() and request.user.is_superuser:
            currency = 'EUR'
            month = None if not 'month' in self.kwargs else self.kwargs['month']
            year = None if not 'year' in self.kwargs else self.kwargs['year']

            self.use_old_stats = 'use_old_stats' in self.request.GET
            self.flush_cache = 'flush_cache' in self.request.GET

            start_date, end_date = parse_date(month, year)
            year = start_date.year
            month = start_date.month if month != "0" else "0"

            start_date_query = datetime.datetime.combine(start_date, datetime.time(0, 0, 0, 0))
            end_date_query = datetime.datetime.combine(end_date, datetime.time(23, 59, 59, 999999))

            month_display, month_choices, year_choices = enumerate_months(request.user, month, is_admin=True)

            # Aggregate data per day
            values = ('created', 'sale_earnings', 'referral_earnings', 'click_earnings', 'total_clicks',
                      'paid_clicks', 'network_sale_earnings', 'network_click_earnings', 'user_id')
            query_args = {'created__range': (start_date_query, end_date_query), 'data_type': 'aggregated_from_total'}
            data_per_day = aggregated_data_per_day(start_date, end_date, 'admin', values, query_args)

            # Top Publishers (influencers)
            top_publishers = get_admin_aggregated_publishers(start_date_query, end_date_query)

            # Top Products (links)
            top_products = get_aggregated_products(None, start_date_query, end_date_query, TOP_PRODUCTS_LIMIT)

            # Get summary for current period
            if self.use_old_stats:
                monthly_array, clicks_array = self.get_admin_top_summary_old(start_date_query, end_date_query)
            else:
                monthly_array, clicks_array = self.get_admin_top_summary(start_date.year, start_date.month)

            previous_start_date, previous_end_date = get_previous_period(start_date_query, end_date_query)

            # Get summary for previous period

            if self.use_old_stats:
                previous_monthly_array, previous_clicks_array = \
                    self.get_admin_top_summary_old(previous_start_date, previous_end_date)
            else:
                previous_monthly_array, previous_clicks_array = \
                    self.get_admin_top_summary(previous_start_date.year, previous_end_date.month)

            # Get difference between current period and previous previous
            relative_summary = get_relative_change_summary(previous_monthly_array, monthly_array)
            monthly_array = self.get_admin_top_summary_display(zip(monthly_array, relative_summary))
            relative_summary_clicks = get_relative_change_summary(previous_clicks_array, clicks_array)
            clicks_array = self.get_admin_top_summary_display(zip(clicks_array, relative_summary_clicks), True)

            admin_title = 'Admin Dashboard'
            if self.flush_cache:
                admin_title += ' (flush cache)'
            elif self.use_old_stats:
                admin_title += ' (old)'

            context_data = {'year_choices': year_choices, 'month_choices': month_choices, 'year': year, 'month': month,
                            'month_display': month_display, 'data_per_day': data_per_day, 'currency': currency,
                            'top_publishers': top_publishers, 'TOP_PRODUCTS_LIMIT': TOP_PRODUCTS_LIMIT,
                            'top_products': top_products,
                            'monthly_array': monthly_array, 'clicks_array': clicks_array,
                            'admin_title': admin_title}
            return render(request, 'dashboard/new_admin.html', context_data)
        return HttpResponseNotFound()




# Publisher / Store signup
#


class RetailerFormView(TemplateView):
    template_name = 'apparel/retailer_contact.html'

    def get(self, request, *args, **kwargs):
        form = SignupForm(is_store_form=True)
        return render(request, self.template_name, {'form': form})

    def post(self, request, *args, **kwargs):
        form = SignupForm(request.POST, is_store_form=True)
        if form.is_valid():
            # Save name and blog URL on session, for Google Analytics
            request.session['index_complete_info'] = u"{name} {blog}".format(**form.cleaned_data)
            instance = form.save(commit=False)
            instance.store = True
            instance.save()

            mail_managers_task.delay(u'New store signup: {name}'.format(**form.cleaned_data),
                    u'Name: {name}\nEmail: {email}\nURL: {blog}\nTraffic: {traffic}'.format(**form.cleaned_data))

            return HttpResponseRedirect(reverse('index-store-complete'))
        return render(request, self.template_name, {'form': form})


class RetailerPublicFormView(RetailerFormView):
    template_name = 'apparel/retailers.html'


class PublisherToolsView(TemplateView):
    template_name='dashboard/publisher_tools.html'


