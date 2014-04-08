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

import sys
import os, os.path
import argparse
import itertools
import asyncio
from . import fetch_news_data

@asyncio.coroutine
def on_started(loop, main_ctx, news_url_task):
    news_url = news_url_task.get('news_url')
    
    if news_url is None:
        return
    
    print('{}: started'.format(news_url))

@asyncio.coroutine
def on_done(loop, main_ctx, news_url_task):
    news_url = news_url_task.get('news_url')
    
    if news_url is None:
        return
    
    news_data_list = news_url_task.get('news_data_list')
    news_data_list_error = news_url_task.get('news_data_list_error')
    
    if news_data_list_error is not None or not news_data_list:
        if news_data_list_error is not None:
            fail_msg = 'fail: {}: {}'.format(
                    news_data_list_error[0],
                    news_data_list_error[1],
                    )
        else:
            fail_msg = 'fail'
        print('{}: {}'.format(news_url, fail_msg))
        return
    
    out_dir_path = main_ctx['out_dir_path']
    out_counter = main_ctx['out_counter']
    
    for news_data in news_data_list:
        out_i = next(out_counter)
        out_path = os.path.join(out_dir_path, 'out-{}.txt'.format(out_i))
        title, body = news_data
        
        with open(out_path, mode='w', encoding='utf-8', newline='\n') as fd:
            fd.write('{}\n\n{}'.format(title, body))
    
    print('{}: done'.format(news_url))

def main():
    parser = argparse.ArgumentParser(
            description='utility for fetching news data (title and brief) '
                    'from Scan-Interfax and Google-News.',
            )
    
    parser.add_argument(
            '--conc',
            type=int,
            metavar='CONC-COUNT',
            help='concurrent thread count. default is {}'.format(fetch_news_data.DEFAULT_CONC),
            )
    parser.add_argument(
            '--url-list',
            metavar='URL-LIST-PATH',
            help='path to file of list of urls for fetching',
            )
    parser.add_argument(
            '--out',
            metavar='OUT-PATH',
            help='path to result directory (will be created)',
            )
    
    args = parser.parse_args()
    
    if args.url_list is None:
        print('argument error: missing ``URL-LIST-PATH``', file=sys.stderr)
        exit(code=2)
    
    if args.out is None:
        print('argument error: missing ``OUT-PATH``', file=sys.stderr)
        exit(code=2)
    
    main_ctx = {
            'conc': args.conc,
            'url_list_path': args.url_list,
            'out_dir_path': args.out,
            }
    
    with open(main_ctx['url_list_path'], encoding='utf-8', errors='replace') as fd:
        main_ctx['news_url_list'] = tuple(
                line
                for line in filter(None, map(lambda s: s.strip(), fd))
                )
    
    os.mkdir(main_ctx['out_dir_path'])
    
    main_ctx['out_counter'] = itertools.count()
    
    def get_news_url_task_iter():
        for news_url in main_ctx['news_url_list']:
            yield {
                    'news_url': news_url,
                    'on_started': lambda loop, news_url_task: \
                            on_started(loop, main_ctx, news_url_task),
                    'on_done': lambda loop, news_url_task: \
                            on_done(loop, main_ctx, news_url_task),
                    }
    
    loop = asyncio.get_event_loop()
    fetch_coro = fetch_news_data.fetch_news_data_bulk_cycle(
            loop,
            get_news_url_task_iter(),
            conc=main_ctx['conc'],
            )
    loop.run_until_complete(fetch_coro)
    
    print('done!')
