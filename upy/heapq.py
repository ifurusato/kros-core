"""
The MIT License (MIT)

Copyright (c) 2013-2021 Damien P. George

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.

--------------------------------------------------------------------------------

Heap queue algorithm (a.k.a. priority queue).

This maintains all the code of the original but has elided most of the
comments to save space. Locate the original to read the comments.

Requires itertools.

Usage:

heap = []            # creates an empty heap
heappush(heap, item) # pushes a new item on the heap
item = heappop(heap) # pops the smallest item from the heap
item = heap[0]       # smallest item on the heap without popping it
heapify(x)           # transforms list into a heap, in-place, in linear time
item = heapreplace(heap, item) # pops and returns smallest item, and adds
                               # new item; the heap size is unchanged
"""

__all__ = [
    "heappush",
    "heappop",
    "heapify",
    "heapreplace",
    "merge",
    "nlargest",
    "nsmallest",
    "heappushpop",
]

# from itertools import count, tee, chain

def heappush(heap, item):
    """Push item onto heap, maintaining the heap invariant."""
    heap.append(item)
    _siftdown(heap, 0, len(heap) - 1)


def heappop(heap):
    """Pop the smallest item off the heap, maintaining the heap invariant."""
    lastelt = heap.pop()
    if heap:
        returnitem = heap[0]
        heap[0] = lastelt
        _siftup(heap, 0)
    else:
        returnitem = lastelt
    return returnitem


def heapreplace(heap, item):
    """Pop and return the current smallest value, and add the new item."""
    returnitem = heap[0]
    heap[0] = item
    _siftup(heap, 0)
    return returnitem


def heappushpop(heap, item):
    """Fast version of a heappush followed by a heappop."""
    if heap and heap[0] < item:
        item, heap[0] = heap[0], item
        _siftup(heap, 0)
    return item


def heapify(x):
    """Transform list into a heap, in-place, in O(len(x)) time."""
    n = len(x)
    for i in reversed(range(n // 2)):
        _siftup(x, i)


def _heappushpop_max(heap, item):
    """Maxheap version of a heappush followed by a heappop."""
    if heap and item < heap[0]:
        item, heap[0] = heap[0], item
        _siftup_max(heap, 0)
    return item


def _heapify_max(x):
    """Transform list into a maxheap, in-place, in O(len(x)) time."""
    n = len(x)
    for i in reversed(range(n // 2)):
        _siftup_max(x, i)


def nlargest(n, iterable):
    """Find the n largest elements in a dataset."""
    from itertools import islice, count, tee, chain

    if n < 0:
        return []
    it = iter(iterable)
    result = list(islice(it, n))
    if not result:
        return result
    heapify(result)
    _heappushpop = heappushpop
    for elem in it:
        _heappushpop(result, elem)
    result.sort(reverse=True)
    return result


def nsmallest(n, iterable):
    """Find the n smallest elements in a dataset."""
    from itertools import islice, count, tee, chain

    if n < 0:
        return []
    it = iter(iterable)
    result = list(islice(it, n))
    if not result:
        return result
    _heapify_max(result)
    _heappushpop = _heappushpop_max
    for elem in it:
        _heappushpop(result, elem)
    result.sort()
    return result


def _siftdown(heap, startpos, pos):
    newitem = heap[pos]
    while pos > startpos:
        parentpos = (pos - 1) >> 1
        parent = heap[parentpos]
        if newitem < parent:
            heap[pos] = parent
            pos = parentpos
            continue
        break
    heap[pos] = newitem


def _siftup(heap, pos):
    endpos = len(heap)
    startpos = pos
    newitem = heap[pos]
    childpos = 2 * pos + 1
    while childpos < endpos:
        rightpos = childpos + 1
        if rightpos < endpos and not heap[childpos] < heap[rightpos]:
            childpos = rightpos
        heap[pos] = heap[childpos]
        pos = childpos
        childpos = 2 * pos + 1
    heap[pos] = newitem
    _siftdown(heap, startpos, pos)


def _siftdown_max(heap, startpos, pos):
    "Maxheap variant of _siftdown"
    newitem = heap[pos]
    while pos > startpos:
        parentpos = (pos - 1) >> 1
        parent = heap[parentpos]
        if parent < newitem:
            heap[pos] = parent
            pos = parentpos
            continue
        break
    heap[pos] = newitem

def _siftup_max(heap, pos):
    "Maxheap variant of _siftup"
    endpos = len(heap)
    startpos = pos
    newitem = heap[pos]
    childpos = 2 * pos + 1  # leftmost child position
    while childpos < endpos:
        rightpos = childpos + 1
        if rightpos < endpos and not heap[rightpos] < heap[childpos]:
            childpos = rightpos
        heap[pos] = heap[childpos]
        pos = childpos
        childpos = 2 * pos + 1
    heap[pos] = newitem
    _siftdown_max(heap, startpos, pos)

# If available, use C implementation
try:
    from _heapq import *
except ImportError:
    pass


def merge(*iterables):
    """Merge multiple sorted inputs into a single sorted output.

    Similar to sorted(itertools.chain(*iterables)) but returns a generator,
    does not pull the data into memory all at once, and assumes that each of
    the input streams is already sorted (smallest to largest).

    >>> list(merge([1,3,5,7], [0,2,4,8], [5,10,15,20], [], [25]))
    [0, 1, 2, 3, 4, 5, 5, 7, 8, 10, 15, 20, 25]
    """
    _heappop, _heapreplace, _StopIteration = heappop, heapreplace, StopIteration
    _len = len
    h = []
    h_append = h.append
    for itnum, it in enumerate(map(iter, iterables)):
        try:
            next = it.__next__
            h_append([next(), itnum, next])
        except _StopIteration:
            pass
    heapify(h)

    while _len(h) > 1:
        try:
            while True:
                v, itnum, next = s = h[0]
                yield v
                s[0] = next()
                _heapreplace(h, s)
        except _StopIteration:
            _heappop(h)
    if h:
        v, itnum, next = h[0]
        yield v
        yield from next.__self__


# Extend the implementations of nsmallest and nlargest to use a key= argument
_nsmallest = nsmallest

def nsmallest(n, iterable, key=None):
    """Find the n smallest elements in a dataset.

    Equivalent to:  sorted(iterable, key=key)[:n]
    """
    from itertools import islice, count, tee, chain
    if n == 1:
        it = iter(iterable)
        head = list(islice(it, 1))
        if not head:
            return []
        if key is None:
            return [min(chain(head, it))]
        return [min(chain(head, it), key=key)]
    try:
        size = len(iterable)
    except (TypeError, AttributeError):
        pass
    else:
        if n >= size:
            return sorted(iterable, key=key)[:n]
    if key is None:
        it = zip(iterable, count())  # decorate
        result = _nsmallest(n, it)
        return [r[0] for r in result]  # undecorate
    in1, in2 = tee(iterable)
    it = zip(map(key, in1), count(), in2)  # decorate
    result = _nsmallest(n, it)
    return [r[2] for r in result]  # undecorate

# ...................
_nlargest = nlargest

def nlargest(n, iterable, key=None):
    """Find the n largest elements in a dataset."""
    from itertools import islice, count, tee, chain
    if n == 1:
        it = iter(iterable)
        head = list(islice(it, 1))
        if not head:
            return []
        if key is None:
            return [max(chain(head, it))]
        return [max(chain(head, it), key=key)]
    try:
        size = len(iterable)
    except (TypeError, AttributeError):
        pass
    else:
        if n >= size:
            return sorted(iterable, key=key, reverse=True)[:n]
    if key is None:
        it = zip(iterable, count(0, -1))  # decorate
        result = _nlargest(n, it)
        return [r[0] for r in result]  # undecorate
    in1, in2 = tee(iterable)
    it = zip(map(key, in1), count(0, -1), in2)  # decorate
    result = _nlargest(n, it)
    return [r[2] for r in result]  # undecorate

#EOF
