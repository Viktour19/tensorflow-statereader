"""Utilities for parsing text files."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import collections
import h5py
import os

import tensorflow as tf


def _read_words(filename):
  with tf.gfile.GFile(filename, "r") as f:
    return f.read().decode("utf-8").replace("\n", "<eos>").split()


def _build_vocab(filename):
  data = _read_words(filename)

  counter = collections.Counter(data)
  count_pairs = sorted(counter.items(), key=lambda x: (-x[1], x[0]))

  words, _ = list(zip(*count_pairs))
  word_to_id = dict(zip(words, range(len(words))))

  return word_to_id


def _file_to_word_ids(filename, word_to_id):
  data = _read_words(filename)
  return [word_to_id[word] for word in data if word in word_to_id]


def _write_dict(w2idx):
    out = open("words.dict", "w")
    items = [(v, k) for k, v in w2idx.iteritems()]
    items.sort()
    for v, k in items:
        out.write(str(k) + ", " + str(v) + "\n")
    out.close()

def ptb_raw_data(data_path=None, store=False):
  """Load PTB raw data from data directory "data_path".

  Args:
    data_path: string path to the directory where simple-examples.tgz has
      been extracted.

  Returns:
    tuple (train_data, valid_data, vocabulary)
    where each of the data objects can be passed to PTBIterator.
  """

  #Excluded test set but can be easily added by uncommenting this
  train_path = os.path.join(data_path, "train.txt")
  valid_path = os.path.join(data_path, "valid.txt")
  #test_path = os.path.join(data_path, "test.txt")

  word_to_id = _build_vocab(train_path)
  train_data = _file_to_word_ids(train_path, word_to_id)
  valid_data = _file_to_word_ids(valid_path, word_to_id)
  #test_data = _file_to_word_ids(test_path, word_to_id)
  vocabulary = len(word_to_id)

  print(len(train_data))
  if store:
      _write_dict(word_to_id)
      f = h5py.File("train.h5", "w")
      f["word_ids"] = train_data
      f.close()
  return train_data, valid_data, vocabulary#test_data, vocabulary


def ptb_producer(raw_data, batch_size, num_steps, name=None):
  """Iterate on the raw data.

  This chunks up raw_data into batches of examples and returns Tensors that
  are drawn from these batches.

  Args:
    raw_data: one of the raw data outputs from ptb_raw_data.
    batch_size: int, the batch size.
    num_steps: int, the number of unrolls.
    name: the name of this operation (optional).

  Returns:
    A pair of Tensors, each shaped [batch_size, num_steps]. The second element
    of the tuple is the same data time-shifted to the right by one.

  Raises:
    tf.errors.InvalidArgumentError: if batch_size or num_steps are too high.
  """
  with tf.name_scope(name, "PTBProducer", [raw_data, batch_size, num_steps]):
    raw_data = tf.convert_to_tensor(raw_data, name="raw_data", dtype=tf.int32)

    data_len = tf.size(raw_data)
    batch_len = data_len // batch_size
    data = tf.reshape(raw_data[0 : batch_size * batch_len],
                      [batch_size, batch_len])

    epoch_size = (batch_len - 1) // num_steps
    assertion = tf.assert_positive(
        epoch_size,
        message="epoch_size == 0, decrease batch_size or num_steps")
    with tf.control_dependencies([assertion]):
      epoch_size = tf.identity(epoch_size, name="epoch_size")

    i = tf.train.range_input_producer(epoch_size, shuffle=False).dequeue()
    x = tf.strided_slice(data, [0, i * num_steps],  [batch_size, (i + 1) * num_steps], [1, 1])
    x.set_shape([batch_size, num_steps])
    y = tf.strided_slice(data, [0, i * num_steps + 1], [batch_size, (i + 1) * num_steps + 1], [1, 1])
    y.set_shape([batch_size, num_steps])
    # print(y, "label size")
    # print(x, "input size")
    return x, y