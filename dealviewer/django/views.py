# Copyright 2006-2008 Kevin Dwyer

import cStringIO
from xml.sax import saxutils
from django.template import Context, loader
from django.http import HttpResponse, Http404, HttpResponseNotFound
import Deal
import models

MAX_DEALS = 100
NUM_DEFAULT = 20

class HttpResponseBadRequest(HttpResponse):
    def __init__(self, *args, **kwargs):
        HttpResponse.__init__(self, *args, **kwargs)
        self.status_code = 400

def index(request):
    num_deals = int(request.GET.get('num_deals', NUM_DEFAULT))
    ### TEMP
    show_filters = bool(request.GET.get('filters',False))
    err_msg = None
    show_minus = show_plus = True
    response = HttpResponse

    if num_deals < 1:
        num_deals = NUM_DEFAULT
        err_msg = 'Too few deals specified!  Defaulting to %s.' % num_deals
        response = HttpResponseBadRequest
    elif num_deals - 5 < 1:
        show_minus = False
    #elif num_deals + 5 > MAX_DEALS:
    #    show_plus = False
    elif num_deals > MAX_DEALS:
        num_deals = MAX_DEALS
        err_msg = 'Too many deals specified!  Defaulting to %s.  To see more, contact kevin-at-pheared-dot-net' % MAX_DEALS
        response = HttpResponseBadRequest

    latest_deals = Deal.getDeals(num=num_deals)

    feed_list = models.getFeeds()

    t = loader.get_template('dealviewer/index.html')
    c = Context({
        'page_title': 'Deals!',
        'deal_list': latest_deals,
        'num_deals': num_deals,
        'err': err_msg,
        'show_minus': show_minus,
        'show_plus': show_plus,
        'show_filters': show_filters,
        'feed_list': feed_list
        })

    return response(t.render(c))

def deal(request, deal_id):
    deal = Deal.getDealByID(deal_id)

    t = loader.get_template('dealviewer/deal.html')
    c = Context({
        'deal': deal
        })
    if not deal:
        return HttpResponseNotFound(t.render(c))
    return HttpResponse(t.render(c))

class XMLDealer(saxutils.XMLGenerator):
    def addDeals(self, deals):
        self.startElement(u'deals', {})

        # Dirty HTML as CDATA way
        t = loader.get_template('dealviewer/since.html')
        c = Context({'deal_list': deals})
        self.characters(t.render(c))

        # Nice XML way
        #for deal in deals:
            #attrs = {u'description': deal.description,
            #         u'feed': deal.feed,
            #         u'url': deal.url,
            #         u'id': str(deal.deal_id),
            #         u'received_on': str(deal.received_on)}
            #self.startElement(u'deal', attrs)
            #self.endElement(u'deal')
        self.endElement(u'deals')

def since_xml(request, deal_id):
    latest_deals = [d for d in Deal.getDeals(since=deal_id)]

    sio = cStringIO.StringIO()
    if len(latest_deals):
        dealer = XMLDealer(out=sio)
        dealer.startDocument()
        dealer.addDeals(latest_deals)
        dealer.endDocument()

    t = loader.get_template('dealviewer/since.xml')
    c = Context({
        'latest_deals': sio.getvalue()
        })
    if not latest_deals:
        return HttpResponseNotFound(t.render(c))
    return HttpResponse(t.render(c), mimetype='text/xml')

def search(request):
    terms = request.GET.get('q')

    found_deals = []
    if terms:
        found_deals = Deal.getDeals(num=MAX_DEALS, terms=terms)

    t = loader.get_template('dealviewer/search.html')
    c = Context({
        'page_title': 'Deal Search',
        'terms': terms,
        'deal_list': [d for d in found_deals],
        'MAX_DEALS': MAX_DEALS
        })
    if not found_deals:
        return HttpResponseNotFound(t.render(c))
    return HttpResponse(t.render(c))

def save_search(request):
    terms = request.GET.get('q')

    t = loader.get_template('dealviewer/save_search.html')
    c = Context({
        'page_title': 'Saved Search',
        'terms': terms,
        })

    return HttpResponse(t.render(c))
