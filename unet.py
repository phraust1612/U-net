import tensorflow as tf
import numpy as np

class Unet:

  def __init__ (self, batch_size):
    self.x = tf.placeholder (tf.float32, [None, 572, 572, 1])
    self.y = tf.placeholder (tf.float32, [None, 388, 388, 2])
    self.tf_drop = tf.placeholder (tf.float32)
    self.W = {}
    self.b = {}
    self.h = 0.025
    self.batch_size = batch_size
    self.namelist = [
      "1_1", "1_2",
      "2_1", "2_2",
      "3_1", "3_2",
      "4_1", "4_2",
      "5_1", "5_2",
      "6_0", "6_1", "6_2",
      "7_0", "7_1", "7_2",
      "8_0", "8_1", "8_2",
      "9_0", "9_1", "9_2",
      "10" ]
    self.load ()
    self.build_net ()

  def load (self):
    for name in self.namelist:
      nptmp = np.load ("param/W"+name+".npy")
      nptmp = nptmp.transpose([2,3,1,0])
      self.W[name] = tf.Variable (tf.convert_to_tensor(nptmp, name=name))

  def save (self, sess):
    for name in self.namelist:
      nptmp = sess.run (self.W[name])
      nptmp = nptmp.transpose([3,2,0,1])
      np.save ("param/W"+name+".npy", nptmp)

  def build_net (self):
    image_size = [572, 284, 140, 68, 32, 56, 104, 200, 392]
    cropL = []

    # down layers
    L = tf.reshape (self.x, [-1, 572, 572, 1])
    idx = len(image_size) - 1
    for i in range (10):
      print (self.namelist[i],L)

      # 3x3 conv + ReLU
      L = tf.nn.conv2d (L, self.W[self.namelist[i]], strides=[1,1,1,1], padding="VALID")
      L = tf.nn.relu (L)

      if i%2 == 1 and i < 8:
        # push cropped layer in a temporary list
        crop_size = image_size[idx]
        idx -= 1
        cropL.append (tf.image.resize_image_with_crop_or_pad (L, crop_size, crop_size))

        # 2x2 max-pooling
        L = tf.nn.max_pool (L, ksize=[1,2,2,1], strides=[1,2,2,1], padding="VALID")
        L = tf.nn.dropout (L, keep_prob = self.tf_drop)

    # upsampling
    idx = 5
    depth = 512
    for i in range (10, 22):
      print (self.namelist[i],L)

      # 2x2 up-conv + concatenation
      if i%3 == 1:
        ks = image_size[idx]
        L = tf.nn.conv2d_transpose (L, self.W[self.namelist[i]], [self.batch_size, ks, ks, depth], strides=[1,2,2,1], padding="VALID")
        L = tf.concat ([cropL.pop(), L], -1)
        idx += 1
        if depth > 128:
          depth //= 2

      # 3x3 conv + ReLU layer
      else:
        L = tf.nn.conv2d (L, self.W[self.namelist[i]], strides=[1,1,1,1], padding="VALID")
        L = tf.nn.relu (L)

    # final layer shape : 388 x 388 x 1
    self.output = tf.nn.conv2d (L, self.W["10"], strides=[1,1,1,1], padding="SAME")
    self.output = tf.reshape (self.output, [-1, 388, 388, 2])

    self.loss = tf.reduce_mean (tf.nn.softmax_cross_entropy_with_logits (logits=self.output, labels=self.y))
    optimizer = tf.train.AdagradOptimizer (learning_rate = self.h)
    self.train = optimizer.minimize (self.loss)

  def get_output (self, sess, image):
    """
    get_output (sess, image):
      apply Unet and take the output
      sess : tensorflow session
      image : numpy array of shape : (572, 572, 1)
    """
    _feed = {self.x:image, self.tf_drop:1}
    return sess.run (self.output, feed_dict=_feed)

  def train_param (self, sess, feed):
    """
    train_param (sess, feed):
      train and return loss
      sess : tensorflow session
      feed : dict {'x', 'y', 'drop'}
    """
    _feed = {self.x:feed['x'], self.y:feed['y'], self.tf_drop:feed['drop']}
    c,_ = sess.run([self.loss, self.train], feed_dict=_feed)
    return c
