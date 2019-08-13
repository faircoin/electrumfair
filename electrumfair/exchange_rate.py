import asyncio
from datetime import datetime
import inspect
import sys
import os
import json
import time
import csv
import decimal
from decimal import Decimal
import traceback
from typing import Sequence, Optional

from aiorpcx.curio import timeout_after, TaskTimeout, TaskGroup

from .bitcoin import COIN
from .i18n import _
from .util import (PrintError, ThreadJob, make_dir, log_exceptions,
                   make_aiohttp_session, resource_path)
from .network import Network
from .simple_config import SimpleConfig


DEFAULT_ENABLED = False
DEFAULT_CURRENCY = "EUR"
DEFAULT_EXCHANGE = "FreeVision"  # default exchange should ideally provide historical rates


# See https://en.wikipedia.org/wiki/ISO_4217
CCY_PRECISIONS = {
'AED': 2,'ARS': 2,'AUD': 2,
'BCH': 8,'BDT': 2,'BHD': 3,'BMD': 2,'BNB': 4,'BRL': 2,'BTC': 8,
'CAD': 2,'CHF': 2,'CLP': 2,'CNY': 2,'CZK': 2,
'DKK': 2,
'EOS': 4,'ETH': 8,'EUR': 2,
'FAIRO': 2,
'GBP': 2,
'HKD': 2,'HUF': 2,
'IDR': 0,'ILS': 2,'INR': 2,
'JPY': 2,
'KRW': 0,'KWD': 4,
'LKR': 2,'LTC': 8,
'MMK': 0,'MXN': 2,'MYR': 2,
'NOK': 2,'NZD': 2,
'PHP': 2,'PKR': 2,'PLN': 2,
'RUB': 2,
'SAR': 2,'SEK': 2,'SGD': 2,
'THB': 2,'TRY': 2,'TWD': 2,
'USD': 2,
'VND': 0,'VEF': 0,
'XAG': 4,'XAU': 8,'XDR': 2,'XLM': 2,'XRP': 2,
'ZAR': 2
}


class ExchangeBase(PrintError):

    def __init__(self, on_quotes, on_history):
        self.history = {}
        self.quotes = {}
        self.on_quotes = on_quotes
        self.on_history = on_history

    async def get_raw(self, site, get_string):
        # APIs must have https
        url = ''.join(['https://', site, get_string])
        network = Network.get_instance()
        proxy = network.proxy if network else None
        async with make_aiohttp_session(proxy) as session:
            async with session.get(url) as response:
                response.raise_for_status()
                return await response.text()

    async def get_json(self, site, get_string):
        # APIs must have https
        url = ''.join(['https://', site, get_string])
        network = Network.get_instance()
        proxy = network.proxy if network else None
        async with make_aiohttp_session(proxy) as session:
            async with session.get(url) as response:
                response.raise_for_status()
                # set content_type to None to disable checking MIME type
                return await response.json(content_type=None)

    async def get_csv(self, site, get_string):
        raw = await self.get_raw(site, get_string)
        reader = csv.DictReader(raw.split('\n'))
        return list(reader)

    def name(self):
        return self.__class__.__name__

    async def update_safe(self, ccy):
        try:
            self.print_error("getting fx quotes for", ccy)
            self.quotes = await self.get_rates(ccy)
            self.print_error("received fx quotes")
        except BaseException as e:
            self.print_error("failed fx quotes:", repr(e))
            # traceback.print_exc()
            self.quotes = {}
        self.on_quotes()

    def read_historical_rates(self, ccy, cache_dir) -> Optional[dict]:
        filename = os.path.join(cache_dir, self.name() + '_'+ ccy)
        if not os.path.exists(filename):
            return None
        timestamp = os.stat(filename).st_mtime
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                h = json.loads(f.read())
        except:
            return None
        if not h:  # e.g. empty dict
            return None
        h['timestamp'] = timestamp
        self.history[ccy] = h
        self.on_history()
        return h

    @log_exceptions
    async def get_historical_rates_safe(self, ccy, cache_dir):
        try:
            self.print_error(f"requesting fx history for {ccy}")
            h = await self.request_history(ccy)
            self.print_error(f"received fx history for {ccy}")
        except BaseException as e:
            self.print_error(f"failed fx history: {repr(e)}")
            #traceback.print_exc()
            return
        filename = os.path.join(cache_dir, self.name() + '_' + ccy)
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(json.dumps(h))
        h['timestamp'] = time.time()
        self.history[ccy] = h
        self.on_history()

    def get_historical_rates(self, ccy, cache_dir):
        if ccy not in self.history_ccys():
            return
        h = self.history.get(ccy)
        if h is None:
            h = self.read_historical_rates(ccy, cache_dir)
        if h is None or h['timestamp'] < time.time() - 24*3600:
            asyncio.get_event_loop().create_task(self.get_historical_rates_safe(ccy, cache_dir))

    def history_ccys(self):
        return []

    def historical_rate(self, ccy, d_t):
        return self.history.get(ccy, {}).get(d_t.strftime('%Y-%m-%d'), 'NaN')

    async def request_history(self, ccy):
        raise NotImplementedError()  # implemented by subclasses

    async def get_rates(self, ccy):
        raise NotImplementedError()  # implemented by subclasses

    async def get_currencies(self):
        rates = await self.get_rates('')
        return sorted([str(a) for (a, b) in rates.items() if b is not None and len(a)==3])

class FairCoop_ChainFaircoin(ExchangeBase):

    async def get_rates(self,ccy):
        json = await self.get_json('chain.fair-coin.org', '/download/ticker')
        return dict([(r, Decimal(json[r]['last']))
                     for r in json])

    def history_ccys(self):
        return ['BTC','ETH','LTC','BCH','BNB','EOS','XRP','XLM','USD','AED','ARS','AUD','BDT','BHD','BMD','BRL','CAD','CHF','CLP','CNY','CZK','DKK','EUR','GBP','HKD','HUF','IDR','ILS','INR','JPY','KRW','KWD','LKR','MMK','MXN','MYR','NOK','NZD','PHP','PKR','PLN','RUB','SAR','SEK','SGD','THB','TRY','TWD','VEF','VND','ZAR','XDR','XAG','XAU']

    async def request_history(self, ccy):
        json = await self.get_json('exchange.faircoin.co', '/data/history_faircoop_'+ccy+'.json')
        return json

class FairCoop_GetFaircoin(ExchangeBase):

    async def get_rates(self,ccy):
        json = await self.get_json('getfaircoin.net', '/api/ticker')
        return dict([(r, Decimal(json[r]['last']))
                     for r in json])

    def history_ccys(self):
        return ['BTC','ETH','LTC','BCH','BNB','EOS','XRP','XLM','USD','AED','ARS','AUD','BDT','BHD','BMD','BRL','CAD','CHF','CLP','CNY','CZK','DKK','EUR','GBP','HKD','HUF','IDR','ILS','INR','JPY','KRW','KWD','LKR','MMK','MXN','MYR','NOK','NZD','PHP','PKR','PLN','RUB','SAR','SEK','SGD','THB','TRY','TWD','VEF','VND','ZAR','XDR','XAG','XAU']

    async def request_history(self, ccy):
        json = await self.get_json('exchange.faircoin.co', '/data/history_faircoop_'+ccy+'.json')
        return json

class FreeVision(ExchangeBase):

    async def get_rates(self,ccy):
        json = await self.get_json('exchange.faircoin.co', '/data/ticker')
        return dict([(r, Decimal(json[r]['last']))
                     for r in json])

    def history_ccys(self):
        return ['BTC','ETH','LTC','BCH','BNB','EOS','XRP','XLM','USD','AED','ARS','AUD','BDT','BHD','BMD','BRL','CAD','CHF','CLP','CNY','CZK','DKK','EUR','GBP','HKD','HUF','IDR','ILS','INR','JPY','KRW','KWD','LKR','MMK','MXN','MYR','NOK','NZD','PHP','PKR','PLN','RUB','SAR','SEK','SGD','THB','TRY','TWD','VEF','VND','ZAR','XDR','XAG','XAU']

    async def request_history(self, ccy):
        json = await self.get_json('exchange.faircoin.co', '/data/history_'+ccy+'.json')
        return json


class FreeVision_mid(ExchangeBase):

    async def get_rates(self,ccy):
        json = await self.get_json('exchange.faircoin.co', '/data/ticker_mid')
        return dict([(r, Decimal(json[r]['last']))
                     for r in json])

    def history_ccys(self):
        return ['BTC','ETH','LTC','BCH','BNB','EOS','XRP','XLM','USD','AED','ARS','AUD','BDT','BHD','BMD','BRL','CAD','CHF','CLP','CNY','CZK','DKK','EUR','GBP','HKD','HUF','IDR','ILS','INR','JPY','KRW','KWD','LKR','MMK','MXN','MYR','NOK','NZD','PHP','PKR','PLN','RUB','SAR','SEK','SGD','THB','TRY','TWD','VEF','VND','ZAR','XDR','XAG','XAU']

    async def request_history(self, ccy):
        json = await self.get_json('exchange.faircoin.co', '/data/history_mid_'+ccy+'.json')
        return json


class FreeMarket(ExchangeBase):

    async def get_rates(self,ccy):
        json = await self.get_json('exchange.faircoin.co', '/data/ticker_freemarket')
        return dict([(r, Decimal(json[r]['last']))
                     for r in json])

    def history_ccys(self):
        return ['BTC','ETH','LTC','BCH','BNB','EOS','XRP','XLM','USD','AED','ARS','AUD','BDT','BHD','BMD','BRL','CAD','CHF','CLP','CNY','CZK','DKK','EUR','GBP','HKD','HUF','IDR','ILS','INR','JPY','KRW','KWD','LKR','MMK','MXN','MYR','NOK','NZD','PHP','PKR','PLN','RUB','SAR','SEK','SGD','THB','TRY','TWD','VEF','VND','ZAR','XDR','XAG','XAU']

    async def request_history(self, ccy):
        json = await self.get_json('exchange.faircoin.co', '/data/history_freemarket_'+ccy+'.json')
        return json


def dictinvert(d):
    inv = {}
    for k, vlist in d.items():
        for v in vlist:
            keys = inv.setdefault(v, [])
            keys.append(k)
    return inv

def get_exchanges_and_currencies():
    # load currencies.json from disk
    path = resource_path('currencies.json')
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.loads(f.read())
    except:
        pass
    # or if not present, generate it now.
    print("cannot find currencies.json. will regenerate it now.")
    d = {}
    is_exchange = lambda obj: (inspect.isclass(obj)
                               and issubclass(obj, ExchangeBase)
                               and obj != ExchangeBase)
    exchanges = dict(inspect.getmembers(sys.modules[__name__], is_exchange))

    async def get_currencies_safe(name, exchange):
        try:
            d[name] = await exchange.get_currencies()
            print(name, "ok")
        except:
            print(name, "error")

    async def query_all_exchanges_for_their_ccys_over_network():
        async with timeout_after(10):
            async with TaskGroup() as group:
                for name, klass in exchanges.items():
                    exchange = klass(None, None)
                    await group.spawn(get_currencies_safe(name, exchange))
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(query_all_exchanges_for_their_ccys_over_network())
    except Exception as e:
        pass
    with open(path, 'w', encoding='utf-8') as f:
        f.write(json.dumps(d, indent=4, sort_keys=True))
    return d


CURRENCIES = get_exchanges_and_currencies()


def get_exchanges_by_ccy(history=True):
    if not history:
        return dictinvert(CURRENCIES)
    d = {}
    exchanges = CURRENCIES.keys()
    for name in exchanges:
        klass = globals()[name]
        exchange = klass(None, None)
        d[name] = exchange.history_ccys()
    return dictinvert(d)


class FxThread(ThreadJob):

    def __init__(self, config: SimpleConfig, network: Network):
        self.config = config
        self.network = network
        if self.network:
            self.network.register_callback(self.set_proxy, ['proxy_set'])
        self.ccy = self.get_currency()
        self.history_used_spot = False
        self.ccy_combo = None
        self.hist_checkbox = None
        self.cache_dir = os.path.join(config.path, 'cache')
        self._trigger = asyncio.Event()
        self._trigger.set()
        self.set_exchange(self.config_exchange())
        make_dir(self.cache_dir)

    def set_proxy(self, trigger_name, *args):
        self._trigger.set()

    @staticmethod
    def get_currencies(history: bool) -> Sequence[str]:
        d = get_exchanges_by_ccy(history)
        return sorted(d.keys())

    @staticmethod
    def get_exchanges_by_ccy(ccy: str, history: bool) -> Sequence[str]:
        d = get_exchanges_by_ccy(history)
        return d.get(ccy, [])

    @staticmethod
    def remove_thousands_separator(text):
        return text.replace(',', '') # FIXME use THOUSAND_SEPARATOR in util

    def ccy_amount_str(self, amount, commas):
        prec = CCY_PRECISIONS.get(self.ccy, 2)
        fmt_str = "{:%s.%df}" % ("," if commas else "", max(0, prec)) # FIXME use util.THOUSAND_SEPARATOR and util.DECIMAL_POINT
        try:
            rounded_amount = round(amount, prec)
        except decimal.InvalidOperation:
            rounded_amount = amount
        return fmt_str.format(rounded_amount)

    async def run(self):
        while True:
            # approx. every 2.5 minutes, refresh spot price
            try:
                async with timeout_after(150):
                    await self._trigger.wait()
                    self._trigger.clear()
                # we were manually triggered, so get historical rates
                if self.is_enabled() and self.show_history():
                    self.exchange.get_historical_rates(self.ccy, self.cache_dir)
            except TaskTimeout:
                pass
            if self.is_enabled():
                await self.exchange.update_safe(self.ccy)

    def is_enabled(self):
        return bool(self.config.get('use_exchange_rate', DEFAULT_ENABLED))

    def set_enabled(self, b):
        self.config.set_key('use_exchange_rate', bool(b))
        self.trigger_update()

    def get_history_config(self, *, default=False):
        return bool(self.config.get('history_rates', default))

    def set_history_config(self, b):
        self.config.set_key('history_rates', bool(b))

    def get_history_capital_gains_config(self):
        return bool(self.config.get('history_rates_capital_gains', False))

    def set_history_capital_gains_config(self, b):
        self.config.set_key('history_rates_capital_gains', bool(b))

    def get_fiat_address_config(self):
        return bool(self.config.get('fiat_address'))

    def set_fiat_address_config(self, b):
        self.config.set_key('fiat_address', bool(b))

    def get_currency(self):
        '''Use when dynamic fetching is needed'''
        return self.config.get("currency", DEFAULT_CURRENCY)

    def config_exchange(self):
        return self.config.get('use_exchange', DEFAULT_EXCHANGE)

    def show_history(self):
        return self.is_enabled() and self.get_history_config() and self.ccy in self.exchange.history_ccys()

    def set_currency(self, ccy):
        self.ccy = ccy
        self.config.set_key('currency', ccy, True)
        self.trigger_update()
        self.on_quotes()

    def trigger_update(self):
        if self.network:
            self.network.asyncio_loop.call_soon_threadsafe(self._trigger.set)

    def set_exchange(self, name):
        class_ = globals().get(name) or globals().get(DEFAULT_EXCHANGE)
        self.print_error("using exchange", name)
        if self.config_exchange() != name:
            self.config.set_key('use_exchange', name, True)
        self.exchange = class_(self.on_quotes, self.on_history)
        # A new exchange means new fx quotes, initially empty.  Force
        # a quote refresh
        self.trigger_update()
        self.exchange.read_historical_rates(self.ccy, self.cache_dir)

    def on_quotes(self):
        if self.network:
            self.network.trigger_callback('on_quotes')

    def on_history(self):
        if self.network:
            self.network.trigger_callback('on_history')

    def exchange_rate(self) -> Decimal:
        """Returns the exchange rate as a Decimal"""
        rate = self.exchange.quotes.get(self.ccy)
        if rate is None:
            return Decimal('NaN')
        return Decimal(rate)

    def format_amount(self, btc_balance):
        rate = self.exchange_rate()
        return '' if rate.is_nan() else "%s" % self.value_str(btc_balance, rate)

    def format_amount_and_units(self, btc_balance):
        rate = self.exchange_rate()
        return '' if rate.is_nan() else "%s %s" % (self.value_str(btc_balance, rate), self.ccy)

    def get_fiat_status_text(self, btc_balance, base_unit, decimal_point):
        rate = self.exchange_rate()
        return _("  (No FX rate available)") if rate.is_nan() else " 1 %s~%s %s" % (base_unit,
            self.value_str(COIN / (10**(8 - decimal_point)), rate), self.ccy)

    def fiat_value(self, satoshis, rate):
        return Decimal('NaN') if satoshis is None else Decimal(satoshis) / COIN * Decimal(rate)

    def value_str(self, satoshis, rate):
        return self.format_fiat(self.fiat_value(satoshis, rate))

    def format_fiat(self, value):
        if value.is_nan():
            return _("No data")
        return "%s" % (self.ccy_amount_str(value, True))

    def history_rate(self, d_t):
        if d_t is None:
            return Decimal('NaN')
        rate = self.exchange.historical_rate(self.ccy, d_t)
        # Frequently there is no rate for today, until tomorrow :)
        # Use spot quotes in that case
        if rate == 'NaN' and (datetime.today().date() - d_t.date()).days <= 2:
            rate = self.exchange.quotes.get(self.ccy, 'NaN')
            self.history_used_spot = True
        return Decimal(rate)

    def historical_value_str(self, satoshis, d_t):
        return self.format_fiat(self.historical_value(satoshis, d_t))

    def historical_value(self, satoshis, d_t):
        return self.fiat_value(satoshis, self.history_rate(d_t))

    def timestamp_rate(self, timestamp):
        from .util import timestamp_to_datetime
        date = timestamp_to_datetime(timestamp)
        return self.history_rate(date)


assert globals().get(DEFAULT_EXCHANGE), f"default exchange {DEFAULT_EXCHANGE} does not exist"
