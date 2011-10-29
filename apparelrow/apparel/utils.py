def get_pagination(paginator, page_num, on_ends=2, on_each_side=3):
    """
    >>> from django.core.paginator import Paginator
    >>> from apparel import views
    >>> p = Paginator(range(22), 2)
    >>> views.get_pagination(p, 3)
    (None, [1, 2, 3, 4, 5, 6], [10, 11])

    >>> views.get_pagination(p, 6)
    (None, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11], None)

    >>> views.get_pagination(p, 9)
    ([1, 2], [6, 7, 8, 9, 10, 11], None)

    >>> p = Paginator(range(100), 2)
    >>> views.get_pagination(p, 23)
    ([1, 2], [20, 21, 22, 23, 24, 25, 26], [49, 50])

    >>> views.get_pagination(p, 23, on_ends=5, on_each_side=2)
    ([1, 2, 3, 4, 5], [21, 22, 23, 24, 25], [46, 47, 48, 49, 50])
    """
    if paginator.num_pages <= (on_ends * 2) + (on_each_side * 2):
        return None, paginator.page_range, None

    left, mid, right = None, None, None

    if page_num <= on_ends + on_each_side + 1:
        mid = range(1, page_num + 1)
    else:
        left = range(1, on_ends + 1)
        mid = range(page_num - on_each_side, page_num + 1)

    if page_num >= paginator.num_pages - (on_ends + on_each_side + 1):
        mid.extend(range(page_num + 1, paginator.num_pages + 1))
    else:
        mid.extend(range(page_num + 1, on_each_side + page_num + 1))
        right = range(paginator.num_pages - on_ends + 1, paginator.num_pages + 1)

    return left, mid, right
