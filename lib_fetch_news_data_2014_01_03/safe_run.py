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

import threading
import asyncio

@asyncio.coroutine
def safe_run(loop, unsafe_func, *args, **kwargs):
    safe_run_ctx = {
            'result': None,
            'error': None,
            }
    done_event = asyncio.Event()
    
    def safe_run_thread_func():
        try:
            safe_run_ctx['result'] = unsafe_func(*args, **kwargs)
        except Exception as err:
            safe_run_ctx['error'] = type(err), str(err)
        finally:
            loop.call_soon_threadsafe(done_event.set)
    
    safe_run_thread = threading.Thread(target=safe_run_thread_func)
    safe_run_thread.start()
    
    # XXX   separate thread was used for avoid
    #       unexpected system errors from main thread
    
    yield from done_event.wait()
    
    return safe_run_ctx['result'], safe_run_ctx['error']
