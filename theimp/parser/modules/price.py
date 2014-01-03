import decimal

from django.db.models.loading import get_model

from theimp.parser.modules import BaseModule


class Price(BaseModule):

    def parse_price(self, price):
        if not price:
            return None

        try:
            price = decimal.Decimal(''.join(price.split()).replace(',', '.'))
        except decimal.InvalidOperation as e:
            return None

        return price

    def __call__(self, scraped_item, parsed_item, vendor):
        currency = scraped_item.get('currency', '')
        is_discount = scraped_item.get('is_discount')

        discount_price = self.parse_price(scraped_item.get('discount_price'))
        regular_price = self.parse_price(scraped_item.get('regular_price'))
        price = self.parse_price(scraped_item.get('price'))

        parsed_is_discount = None
        parsed_discount_price = None
        parsed_regular_price = None
        parsed_currency = None

        if discount_price and (regular_price or price):
            parsed_is_discount = True
            parsed_discount_price = discount_price
            parsed_regular_price = regular_price or price

        elif not discount_price and (regular_price or price):
            parsed_is_discount = False
            parsed_regular_price = regular_price
            if regular_price and price and price < regular_price:
                parsed_is_discount = True
                parsed_discount_price = price
            elif not regular_price and price:
                parsed_regular_price = price

        if len(currency) == 3:
            parsed_currency = currency

        # XXX: should we just switch the prices instead of returning empty?
        failed = False
        if parsed_discount_price and parsed_discount_price > parsed_regular_price:
            failed = True

        if parsed_currency and parsed_regular_price and not failed:
            parsed_item['currency'] = parsed_currency
            parsed_item['regular_price'] = str(parsed_regular_price)
            parsed_item['is_discount'] = False

            if parsed_discount_price and parsed_discount_price < parsed_regular_price:
                parsed_item['discount_price'] = str(parsed_discount_price)
                parsed_item['is_discount'] = True
            else:
                self.delete_value(parsed_item, 'discount_price')
        else:
            self.delete_value(parsed_item, 'regular_price')
            self.delete_value(parsed_item, 'discount_price')
            self.delete_value(parsed_item, 'currency')
            self.delete_value(parsed_item, 'is_discount')

        return parsed_item
