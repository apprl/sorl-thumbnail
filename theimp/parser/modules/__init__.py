class BaseModule(object):

    def __init__(self, parser):
        self.parser = parser

    def delete_value(self, parsed_item, field):
        if field in parsed_item:
            del parsed_item[field]
