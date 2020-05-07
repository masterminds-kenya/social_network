from flask import current_app as app
from pprint import pprint


def filtered(start, under=False, dunder=True, sa=True, caps=True, special=True):
    """ Limiting the visual display while testing ways to see all desired properties. """
    if isinstance(start, dict):
        start = list(start.keys())
    result = [*start]
    # result = [ea for ea in start if not callable(ea)]
    # app.logger.debug('----- Had these callables -----')
    # calls = [ea for ea in start if callable(ea)]
    # pprint(calls)
    if not dunder:
        result = [ea for ea in result if not ea.startswith('__')]
    if not under:
        result = [ea for ea in result if not ea.startswith('_')]
    if not sa:
        result = [ea for ea in result if not ea.startswith('_sa_')]
    if not caps:
        result = [ea for ea in result if not ea.isupper()]
    if not special:
        spec_keys = ['get_id', 'is_active', 'is_anonymous', 'is_authenticated', 'query', 'query_class', 'metadata']
        result = [ea for ea in result if ea not in spec_keys]

    return set(result)


def check_stuff(row, related, safe):
    """ Determining which properties and methods are tracked through various techniques. """
    # We expect that all "properties" should be in the Mapper.attrs, or perhaps the Mapper.all_orm_descriptors
    app.logger.debug(f"==== Check stuff {row.__class__.__name__} id: {row.id} | related: {related} | safe: {safe} ====")
    # both __dict__ and vars on row.__mapper__.all_orm_descriptors are empty.
    # mapper_less_dunder = [ea for ea in dir_mapper if not ea.startswith('__')]
    # orm_less_dunder = [ea for ea in dir_orm if not ea.startswith('__')]
    # pprint(set(vars(row.__mapper__.all_orm_descriptors)))
    record_type = [
        # ('', ),
        # ('data', filtered(data)),
        # ('dir_mapper_c', filtered(dir(row.__mapper__.c))),
        ('dir_row', filtered(dir(row))),
        ('dir_orm', filtered(dir(row.__mapper__.all_orm_descriptors))),
        ('dir_mapper', filtered(dir(row.__mapper__.attrs))),
        ('dict_row', filtered(row.__dict__)),
        ('vars_row', filtered(vars(row)))
        ]
    test_items = [('_page_id', 'page_id'), ('_saved_media', 'saved_media'), 'saved_media_options']
    pprint(dir(row.__mapper__.columns))  #
    # base_mapper, column_attrs, columns. c
    app.logger.debug('---------------------------------------------------------------------')
    for item in test_items:
        app.logger.debug(f"*-*-*-*-*-*-*-*-*-*-*-*-* {item} *-*-*-*-*-*-*-*-*-*-*-*-*")
        for report in record_type:
            val = ', '.join([str(i in report[1]) for i in item]) if isinstance(item, tuple) else str(item in report[1])
            app.logger.debug(f"{report[0]}: {val}")

    app.logger.debug('---------------------------------------------------------------------')
    for i, first in record_type[:2]:
        # i = 0 if i == len(record_type) else i
        for j, second in record_type:
            # j = 0 if i == len(record_type) else j
            if i == j:
                continue
            app.logger.debug(f'------------------------------ {i} without {j} ---------------------------------------')
            unique_in_current = first - second
            pprint(unique_in_current)
            app.logger.debug(f'******************* {j} without {i} *******************')
            unique_in_current = second - first
            pprint(unique_in_current)

    for name, rec in record_type:
        app.logger.debug(f"================ {name} ================")
        pprint(rec)
    # app.logger.debug('--------------------------------- data ------------------------------------')
    # pprint(data)
    # app.logger.debug('--------------------------------- __dict__ ------------------------------------')
    # pprint(row.__dict__)
    # app.logger.debug('--------------------------------- dir ------------------------------------')
    # pprint(dir(row))
    # app.logger.debug('--------------------------------- vars ------------------------------------')
    # pprint(vars(row))
    # app.logger.debug('---------------------------------------------------------------------')
    return True
