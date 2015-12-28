#!/usr/bin/env python2
# -*- coding: UTF-8 -*-
# File: concurrency.py
# Author: Yuxin Wu <ppwwyyxx@gmail.com>

import threading
from contextlib import contextmanager
import tensorflow as tf

from .naming import *
import logger

class StoppableThread(threading.Thread):
    def __init__(self):
        super(StoppableThread, self).__init__()
        self._stop = threading.Event()

    def stop(self):
        self._stop.set()

    def stopped(self):
        return self._stop.isSet()


class EnqueueThread(threading.Thread):
    def __init__(self, sess, coord, enqueue_op, dataflow):
        super(EnqueueThread, self).__init__()
        self.sess = sess
        self.coord = coord
        self.input_vars = sess.graph.get_collection(INPUT_VARS_KEY)
        self.dataflow = dataflow
        self.op = enqueue_op

    def run(self):
        try:
            while True:
                for dp in self.dataflow.get_data():
                    if self.coord.should_stop():
                        return
                    feed = dict(zip(self.input_vars, dp))
                    self.sess.run([self.op], feed_dict=feed)
        except tf.errors.CancelledError as e:
            pass
        except Exception:
            logger.exception("Exception in EnqueueThread:")

@contextmanager
def coordinator_context(sess, coord, thread, queue):
    """
    Context manager to make sure queue is closed and thread is joined
    """
    thread.start()
    try:
        yield
    except (KeyboardInterrupt, Exception) as e:
        raise
    finally:
        coord.request_stop()
        sess.run(
            queue.close(cancel_pending_enqueues=True))
        coord.join([thread])
