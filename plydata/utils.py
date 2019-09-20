from contextlib import contextmanager

import pandas as pd

from .eval import EvalEnvironment


def hasattrs(obj, names):
    """
    Return True of obj has all the names attributes
    """
    return all(hasattr(obj, attr) for attr in names)


@contextmanager
def temporary_key(d, key, value):
    """
    Context manager that removes key from dictionary on closing

    The dictionary will hold the key for the duration of
    the context.

    Parameters
    ----------
    d : dict-like
        Dictionary in which to insert a temporary key.
    key : hashable
        Location at which to insert ``value``.
    value : object
        Value to insert in ``d`` at location ``key``.
    """
    d[key] = value
    try:
        yield d
    finally:
        del d[key]


@contextmanager
def temporary_attr(obj, name, value):
    """
    Context manager that removes key from dictionary on closing

    The dictionary will hold the key for the duration of
    the context.

    Parameters
    ----------
    obj : object
        Object onto which to add a temporary attribute.
    name : str
        Name of attribute to add to ``obj``.
    value : object
        Value of ``attr``.
    """
    setattr(obj, name, value)
    try:
        yield obj
    finally:
        delattr(obj, name)


def get_empty_env():
    """
    Return an empty environment

    This is for testing or documentation purposes
    """
    return EvalEnvironment(namespaces={})


def Q(name):
    """
    Quote a variable name

    A way to 'quote' variable names, especially ones that do not otherwise
    meet Python's variable name rules.

    Parameters
    ----------
    name : str
        Name of variable

    Returns
    -------
    value : object
        Value of variable

    Examples
    --------
    >>> import pandas as pd
    >>> from plydata import define
    >>> df = pd.DataFrame({'class': [10, 20, 30]})

    Since ``class`` is a reserved python keyword it cannot be a variable
    name, and therefore cannot be used in an expression without quoting it.

    >>> df >> define(y='class+1')
    Traceback (most recent call last):
      File "<string>", line 1
        class+1
            ^
    SyntaxError: invalid syntax

    >>> df >> define(y='Q("class")+1')
       class   y
    0     10  11
    1     20  21
    2     30  31

    Note that it is ``'Q("some name")'`` and not ``'Q(some name)'``.
    As in the above example, you do not need to ``import`` ``Q`` before
    you can use it.
    """
    env = EvalEnvironment.capture(1)
    try:
        return env.namespace[name]
    except KeyError:
        raise NameError("No data named {!r} found".format(name))


def n():
    """
    Size of a group

    It can be used in verbs like
    :class:`~plydata.one_table_verbs.summarize`,
    :class:`~plydata.one_table_verbs.define`. and
    :class:`~plydata.one_table_verbs.create`.
    This is special function that is internally created for each
    group dataframe.
    """
    # For documentation purposes


class custom_dict(dict):
    """
    Dict datastore for conflict testing purposes

    Using a regular dict creates conflicts with verbs
    whose first parameter can be a dict
    """
    pass


@contextmanager
def regular_index(*dfs):
    """
    Change & restore the indices of dataframes

    Dataframe with duplicate values can be hard to work with.
    When split and recombined, you cannot restore the row order.
    This can be the case even if the index has unique but
    irregular/unordered. This contextmanager resets the unordered
    indices of any dataframe passed to it, on exit it restores
    the original index.

    A regular index is of the form::

        RangeIndex(start=0, stop=n, step=1)

    Parameters
    ----------
    dfs : tuple
        Dataframes

    Yields
    ------
    dfs : tuple
        Dataframe

    Examples
    --------
    Create dataframes with different indices

    >>> df1 = pd.DataFrame([4, 3, 2, 1])
    >>> df2 = pd.DataFrame([3, 2, 1], index=[3, 0, 0])
    >>> df3 = pd.DataFrame([11, 12, 13], index=[11, 12, 13])

    Within the contexmanager all frames have nice range indices

    >>> with regular_index(df1, df2, df3):
    ...     print(df1.index)
    ...     print(df2.index)
    ...     print(df3.index)
    RangeIndex(start=0, stop=4, step=1)
    RangeIndex(start=0, stop=3, step=1)
    RangeIndex(start=0, stop=3, step=1)

    Indices restored

    >>> df1.index
    RangeIndex(start=0, stop=4, step=1)
    >>> df2.index
    Int64Index([3, 0, 0], dtype='int64')
    >>> df3.index
    Int64Index([11, 12, 13], dtype='int64')
    """
    original_index = [df.index for df in dfs]
    have_bad_index = [not isinstance(df.index, pd.RangeIndex)
                      for df in dfs]

    for df, bad in zip(dfs, have_bad_index):
        if bad:
            df.reset_index(drop=True, inplace=True)

    try:
        yield dfs
    finally:
        for df, bad, idx in zip(dfs, have_bad_index, original_index):
            if bad and len(df.index) == len(idx):
                df.index = idx


def unique(lst):
    """
    Return unique elements

    :class:`pandas.unique` and :class:`numpy.unique` cast
    mixed type lists to the same type. They are faster, but
    some times we want to maintain the type.

    Parameters
    ----------
    lst : list-like
        List of items

    Returns
    -------
    out : list
        Unique items in the order that they appear in the
        input.

    Examples
    --------
    >>> import pandas as pd
    >>> import numpy as np
    >>> lst = ['one', 'two', 123, 'three']
    >>> pd.unique(lst)
    array(['one', 'two', '123', 'three'], dtype=object)
    >>> np.unique(lst)
    array(['123', 'one', 'three', 'two'],
          dtype='<U5')
    >>> unique(lst)
    ['one', 'two', 123, 'three']

    pandas and numpy cast 123 to a string!, and numpy does not
    even maintain the order.
    """
    seen = set()

    def make_seen(x):
        seen.add(x)
        return x

    return [make_seen(x) for x in lst if x not in seen]


def identity(*args):
    """
    Return whatever is passed in

    Examples
    --------
    >>> x = 1
    >>> y = 2
    >>> identity(x)
    1
    >>> identity(x, y)
    (1, 2)
    >>> identity(*(x, y))
    (1, 2)
    """
    return args if len(args) > 1 else args[0]


def clean_indices(df, sep='_', inplace=False):
    """
    Clearup any multi/fancy indices

    1. columns multiindices are flattened
    2. Fancy multivariable row indices are turned into
       columns and the row index set regular form (0..n)

    Parameters
    ----------
    df : dataframe
        Dataframe
    sep : str
        Separator for the new column names

    Returns
    -------
    out : dataframe
        Dataframe
    """
    if not inplace:
        df = df.copy()

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = collapse_multiindex(df.columns, sep)

    df.reset_index(inplace=True)
    df.columns.name = None
    df.index.name = None
    return None if inplace else df


def collapse_multiindex(midx, sep='_'):
    """
    Collapse a MultiIndex into a minimal Index

    Parameters
    ----------
    midx : pandas.MultiIndex
        MultiIndex to be collapsed

    Returns
    -------
    out : pandas.Index
        Flat Index

    Examples
    --------
    >>> m1 = pd.MultiIndex.from_product([list('a'), list('12')])
    >>> m1
    MultiIndex([('a', '1'),
                ('a', '2')],
               )
    >>> collapse_multiindex(m1)
    Index(['1', '2'], dtype='object')
    >>> m2 = pd.MultiIndex.from_product([list('ab'), list('12')])
    >>> m2
    MultiIndex([('a', '1'),
                ('a', '2'),
                ('b', '1'),
                ('b', '2')],
               )
    >>> collapse_multiindex(m2)
    Index(['a_1', 'a_2', 'b_1', 'b_2'], dtype='object')
    """
    def is_unique(lst):
        return len(set(lst)) == len(lst)

    # Minimum tokens required to uniquely identify columns.
    # We start with the columns in the inner most level of
    # the multiindex.
    # - [(a, 1), (a, 2)] -> [(1,), (2,)]
    # - [(a, 1), (a, 2), (b, 1), (b, 2)] ->
    #       [(a, 1), (a, 2), (b, 1), (b, 2)]
    # - [(z, a, 1), (z, a, 2), (z, b, 1), (z, b, 2)] ->
    #       [(a, 1), (a, 2), (b, 1), (b, 2)]
    for i in range(midx.nlevels):
        id_tokens = [x[-(1+i):] for x in midx]
        if is_unique(id_tokens):
            break
    else:
        raise ValueError("Cannot create unique column names.")

    columns = [sep.join(toks) for toks in id_tokens]
    return pd.Index(columns)
