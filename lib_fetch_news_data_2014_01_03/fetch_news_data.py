# -*- mode: python; coding: utf-8 -*-
#
# Copyright (c) 2014 Andrej Antonov <polymorphm@gmail.com>.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

assert str is not bytes

from urllib import parse as url_parse
from urllib import request as url_request
from http import cookiejar
import html5lib
import asyncio
from . import et_find
from . import safe_run

DEFAULT_CONC = 20
REQUEST_TIMEOUT = 60.0
REQUEST_READ_LIMIT = 10000000

def parse_interfax_data(data):
    doc = html5lib.parse(data)
    
    news_item_elem_list = tuple(et_find.find((doc,), (
            {'tag': '{http://www.w3.org/1999/xhtml}html'},
            {'tag': '{http://www.w3.org/1999/xhtml}body'},
            {'attrib': {'class': 'frontlist'}},
            )))
    
    if not news_item_elem_list:
        return None
    
    parse_result = []
    
    for news_item_elem in news_item_elem_list:
        title_elem_list = tuple(et_find.find((news_item_elem,), (
            {'attrib': {'class': 'news_head'}},
            {'tag': '{http://www.w3.org/1999/xhtml}a'},
            )))
        
        if not title_elem_list:
            continue
        
        title_text = ' '.join(title_elem_list[0].itertext()).strip()
        
        if not title_text:
            continue
        
        body_elem_list = tuple(et_find.find((news_item_elem,), (
            {'attrib': {'class': 'news_content'}},
            )))
        
        if not body_elem_list:
            continue
        
        body_text = ' '.join(body_elem_list[0].itertext()).strip()
        
        if not body_text:
            continue
        
        parse_result.append((title_text, body_text))
    
    return parse_result

def parse_google_data(data):
    doc = html5lib.parse(data)
    
    news_item_elem_list = tuple(et_find.find((doc,), (
            {'tag': '{http://www.w3.org/1999/xhtml}html'},
            {'tag': '{http://www.w3.org/1999/xhtml}body'},
            {'attrib': {'class': 'esc-layout-article-cell'}},
            )))
    
    if not news_item_elem_list:
        return None
    
    parse_result = []
    
    for news_item_elem in news_item_elem_list:
        title_elem_list = tuple(et_find.find((news_item_elem,), (
            {'attrib': {'class': 'esc-lead-article-title'}},
            )))
        
        if not title_elem_list:
            continue
        
        title_text = ' '.join(title_elem_list[0].itertext()).strip()
        
        if not title_text:
            continue
        
        body_elem_list = tuple(et_find.find((news_item_elem,), (
            {'attrib': {'class': 'esc-lead-snippet-wrapper'}},
            )))
        
        if not body_elem_list:
            continue
        
        body_text = ' '.join(body_elem_list[0].itertext()).strip()
        
        if not body_text:
            continue
        
        parse_result.append((title_text, body_text))
    
    return parse_result

def unsafe_fetch_news_data(news_url):
    assert isinstance(news_url, str)
    
    cookies = cookiejar.CookieJar()
    opener = url_request.build_opener(
            url_request.HTTPCookieProcessor(cookiejar=cookies),
            )
    
    opener_res = opener.open(
            url_request.Request(news_url),
            timeout=REQUEST_TIMEOUT,
            )
    data = opener_res.read(REQUEST_READ_LIMIT).decode(errors='replace')
    
    url_scheme, url_netloc, url_path, url_query, url_fragment = \
            url_parse.urlsplit(news_url)
    
    if url_netloc == 'www.scan-interfax.ru' and \
            url_path == '/Home/ClusterNews':
        parse_result = parse_interfax_data(data)
    elif (url_netloc == 'news.google.ru' or url_netloc == 'news.google.com') and \
            (url_path == '/news/section' or url_path == '/news'):
        parse_result = parse_google_data(data)
    else:
        parse_result = None
    
    news_data_list = []
    
    if parse_result is not None:
        news_data_list.extend(parse_result)
    
    return tuple(news_data_list)

@asyncio.coroutine
def fetch_news_data(loop, news_url):
    assert isinstance(news_url, str)
    
    news_data_list, news_data_list_error = yield from safe_run.safe_run(
            loop,
            unsafe_fetch_news_data,
            news_url,
            )
    
    return news_data_list, news_data_list_error

@asyncio.coroutine
def fetch_news_data_cycle(loop, news_url_task_iter):
    for news_url_task in news_url_task_iter:
        news_url = news_url_task.get('news_url')
        
        if news_url is None:
            continue
        
        on_started = news_url_task.get('on_started')
        on_done = news_url_task.get('on_done')
        
        if on_started is not None:
            yield from on_started(loop, news_url_task)
        
        news_url_task['news_data_list'], news_url_task['news_data_list_error'] = \
                yield from fetch_news_data(loop, news_url)
        
        if on_done is not None:
            yield from on_done(loop, news_url_task)

@asyncio.coroutine
def fetch_news_data_bulk_cycle(loop, news_url_task_iter, conc=None):
    if conc is None:
        conc = DEFAULT_CONC
    
    news_url_task_iter = iter(news_url_task_iter)
    
    cycle_future_list = tuple(
            asyncio.async(
                    fetch_news_data_cycle(loop, news_url_task_iter),
                    loop=loop,
                    )
            for i in range(conc)
            )
    
    try:
        yield from asyncio.wait(cycle_future_list, loop=loop)
    finally:
        for cycle_future in cycle_future_list:
            cycle_future.cancel()
