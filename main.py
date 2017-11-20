import os
import os.path
import tensorflow as tf
import helper
import warnings
from distutils.version import LooseVersion
import project_tests as tests
import numpy as np


# Check TensorFlow Version
assert LooseVersion(tf.__version__) >= LooseVersion('1.0'), 'Please use TensorFlow version 1.0 or newer.  You are using {}'.format(tf.__version__)
print('TensorFlow Version: {}'.format(tf.__version__))

# Check for a GPU
if not tf.test.gpu_device_name():
    warnings.warn('No GPU found. Please use a GPU to train your neural network.')
else:
    print('Default GPU Device: {}'.format(tf.test.gpu_device_name()))


def load_vgg(sess, vgg_path):
  
    """
    Load Pretrained VGG Model into TensorFlow.
    :param sess: TensorFlow Session
    :param vgg_path: Path to vgg folder, containing "variables/" and "saved_model.pb"
    :return: Tuple of Tensors from VGG model (image_input, keep_prob, layer3_out, layer4_out, layer7_out)
    """
    # TODO: Implement function
    #   Use tf.saved_model.loader.load to load the model and weights
    #extract pretrained vgg model
    helper.maybe_download_pretrained_vgg('data')
   # maybe_download_pretrained_vgg(vgg_path)
    vgg_tag = 'vgg16'
    tf.saved_model.loader.load(sess, ['vgg16'], vgg_path)
    
    vgg_input_tensor_name = 'image_input:0'
    vgg_keep_prob_tensor_name = 'keep_prob:0'
    vgg_layer3_out_tensor_name = 'layer3_out:0'
    vgg_layer4_out_tensor_name = 'layer4_out:0'
    vgg_layer7_out_tensor_name = 'layer7_out:0'
    
    default_graph= tf.get_default_graph()
    vgg_input_tensor = default_graph.get_tensor_by_name(vgg_input_tensor_name)
    keep_prob_tensor = default_graph.get_tensor_by_name(vgg_keep_prob_tensor_name)
    layer3_tensor    = default_graph.get_tensor_by_name(vgg_layer3_out_tensor_name)
    layer4_tensor    = default_graph.get_tensor_by_name(vgg_layer4_out_tensor_name)
    layer7_tensor    = default_graph.get_tensor_by_name(vgg_layer7_out_tensor_name)
    
    return vgg_input_tensor, keep_prob_tensor, layer3_tensor, layer4_tensor, layer7_tensor

tests.test_load_vgg(load_vgg, tf)

def get_bilinear_weights(filter_shape, upscale_factor):
    #from http://cv-tricks.com/image-segmentation/transpose-convolution-in-tensorflow/
    
    kernel_size = filter_shape[1] ##shape of filter: width, height, no.of in-channels, no.of out-channels
    #centre location of the filter for which value is calculated
    if kernel_size% 2 == 1:
        centre_location = upscale_factor - 1
    else:
        centre_location = upscale_factor - 0.5
        
    bilinear = np.zeros([filter_shape[0],filter_shape[1]])
    
    for x in range(filter_shape[0]):
        for y  in range(filter_shape[1]):
            ##interpolation function
            value = (1 - abs((x - centre_location)/upscale_factor))*(1-abs((y - centre_location)/upscale_factor))
            bilinear[x,y]=value ## fill values in all elements in bilinear
            
    weights= np.zeros(filter_shape)
    
    for i in range(filter_shape[2]):
        weights[:, :,i, i] = bilinear

    init_weights = tf.constant_initializer(value= weights, dtype= tf.float32)

    return init_weights


def conv1x1(x, num_outputs):
  ##for encoder process
    kernel_size = 1
    stride = 1
    return tf.layers.conv2d(x, num_outputs, kernel_size, stride)

def upsample_layer(bottom, n_channels, name, upscale_factor):
    #from http://cv-tricks.com/image-segmentation/transpose-convolution-in-tensorflow/
    # takes input tenor "bottom" and puts a deconv layer on top of it
    
    kernel_size = 2* upscale_factor - upscale_factor%2
    
    strides = [1, upscale_factor, upscale_factor, 1]
    
    with tf.variable_scope(name):
        #shape of the bottom tensor
        in_shape = tf.shape(bottom)
        
        h=  ((in_shape[1] - 1) * strides[1]) +1
        w = ((in_shape[2]- 1)  * strides[2]) +1
        new_shape = [in_shape[0], h, w, n_channels]
        output_shape = tf.stack(new_shape)
        
        filter_shape = [kernel_size, kernel_size, n_channels, n_channels]
        weights = get_bilinear_weights(filter_shape, upscale_factor)
#        deconv = tf.nn.conv2d_transpose(bottom, weights, output_shape,strides=strides, padding = 'SAME')
        deconv = tf.layers.conv2d_transpose(bottom, n_channels, kernel_size, upscale_factor, 'SAME',kernel_initializer=weights)

    return deconv


        
    
def layers(vgg_layer3_out, vgg_layer4_out, vgg_layer7_out, num_classes):
    """
    Create the layers for a fully convolutional network.  Build skip-layers using the vgg layers.
    :param vgg_layer7_out: TF Tensor for VGG Layer 3 output
    :param vgg_layer4_out: TF Tensor for VGG Layer 4 output
    :param vgg_layer3_out: TF Tensor for VGG Layer 7 output
    :param num_classes: Number of classes to classify
    :return: The Tensor for the last layer of output
    """
    # TODO: Implement function
    layer7_1x1 = conv1x1(vgg_layer7_out, num_classes)
#    layer7_upsampled = upsample_layer(layer7_1x1,num_classes, "layer7_upsampled", 2)
    layer4_1x1 = conv1x1(vgg_layer4_out, num_classes)
#    layer4_7_fused= tf. add(layer4_1x1, layer7_upsampled)
#    layer4_7_upsampled = upsample_layer(layer4_7_fused, num_classes, "layer4_7_upsampled",2)
    layer3_1x1 = conv1x1(vgg_layer3_out, num_classes)
#    layer3_4_7_fused= tf.add(layer3_1x1, layer4_7_upsampled)
#    layer3_4_7_upsampled = upsample_layer(layer3_4_7_fused, num_classes, "layer3_4_7_upsampled",8)

    fcn_decoder_l_7=tf.layers.conv2d_transpose(layer7_1x1,num_classes,kernel_size=4,strides=(2,2),padding='SAME',name='fcn_decoder_l_7')
    fcn_decoder_4_7=tf.add(fcn_decoder_l_7,layer4_1x1,name='fcn_decoder_4_7')
    fcn_decoder_l_4_7=tf.layers.conv2d_transpose(fcn_decoder_4_7,num_classes,kernel_size=4,strides=(2,2),padding='SAME',name='fcn_decoder_l_4_7')
    fcn_decoder_3_4_7=tf.add(fcn_decoder_l_4_7,layer3_1x1,name='fcn_decoder_3_4_7')
    fcn_decoder_l_3_4_7=tf.layers.conv2d_transpose(fcn_decoder_3_4_7,num_classes,kernel_size=16,strides=(8,8),padding='SAME',name='fcn_decoder_l_3_4_7')

    return fcn_decoder_l_3_4_7 #layer3_4_7_upsampled

tests.test_layers(layers)


def optimize(nn_last_layer, correct_label, learning_rate, num_classes):
    """
    Build the TensorFLow loss and optimizer operations.
    :param nn_last_layer: TF Tensor of the last layer in the neural network
    :param correct_label: TF Placeholder for the correct label image
    :param learning_rate: TF Placeholder for the learning rate
    :param num_classes: Number of classes to classify
    :return: Tuple of (logits, train_op, cross_entropy_loss)
    """
    # TODO: Implement function
    logits = tf.reshape(nn_last_layer, (-1, num_classes))
    true_labels = tf.reshape(correct_label, (-1,num_classes))
    loss = tf.reduce_mean(tf.nn.softmax_cross_entropy_with_logits(logits=logits, labels=true_labels))
    train_op = tf.train.AdamOptimizer(learning_rate).minimize(loss)
    return logits, train_op,loss

tests.test_optimize(optimize)


def train_nn(sess, epochs, batch_size, get_batches_fn, train_op, cross_entropy_loss, input_image,
             correct_label, keep_prob, learning_rate):
    """
    Train neural network and print out the loss during training.
    :param sess: TF Session
    :param epochs: Number of epochs
    :param batch_size: Batch size
    :param get_batches_fn: Function to get batches of training data.  Call using get_batches_fn(batch_size)
    :param train_op: TF Operation to train the neural network
    :param cross_entropy_loss: TF Tensor for the amount of loss
    :param input_image: TF Placeholder for input images
    :param correct_label: TF Placeholder for label images
    :param keep_prob: TF Placeholder for dropout keep probability
    :param learning_rate: TF Placeholder for learning rate
    """
    # TODO: Implement function
    training_step = 1

    for epoch in range(epochs):
        for image, gt_image in get_batches_fn(batch_size):
            _,loss = sess.run([train_op, cross_entropy_loss], feed_dict = {input_image: image, correct_label:gt_image,keep_prob:0.8,learning_rate:0.0001})
            
            print('Epoch: {} of {}; Training_steps: {}; loss:{}'.format(epoch+1, epochs,training_step,loss))
            training_step+=1

tests.test_train_nn(train_nn)




def run():
    num_classes = 2
    image_shape = (160, 576)
    epochs=20
    batch_size=1
    data_dir = './data'
    runs_dir = './runs'
    training_data_dir='./data/data_road/training'
    tests.test_for_kitti_dataset(data_dir)

    # Download pretrained vgg model
    helper.maybe_download_pretrained_vgg(data_dir)

    # OPTIONAL: Train and Inference on the cityscapes dataset instead of the Kitti dataset.
    # You'll need a GPU with at least 10 teraFLOPS to train on.
    #  https://www.cityscapes-dataset.com/

    with tf.Session() as sess:
        # Path to vgg model
        vgg_path = os.path.join(data_dir, 'vgg')
        
        # Create function to get batches
        get_batches_fn = helper.gen_batch_function(training_data_dir, image_shape)

        # OPTIONAL: Augment Images for better results
        #  https://datascience.stackexchange.com/questions/5224/how-to-prepare-augment-images-for-neural-network

        # TODO: Build NN using load_vgg, layers, and optimize function
        vgg_input_tensor, keep_prob_tensor, layer3_tensor, layer4_tensor, layer7_tensor = load_vgg(sess, vgg_path)
        output_layer= layers(layer3_tensor,layer4_tensor, layer7_tensor, num_classes)
        learning_rate = tf.placeholder(dtype = tf.float32)
        
        #keep_prob_tensor = tf.placeholder(dytype = tf.float32)
        
        correct_labels = tf.placeholder(dtype = tf.float32, shape = [None, None, None, num_classes])
        
        
        logits, train_op,loss = optimize(output_layer, correct_labels, learning_rate, num_classes)
        

        # TODO: Train NN using the train_nn function
        
        sess.run(tf.global_variables_initializer())
        train_nn(sess, epochs, batch_size, get_batches_fn, train_op, loss, vgg_input_tensor,
             correct_labels, keep_prob_tensor, learning_rate)
        

        # TODO: Save inference data using helper.save_inference_samples
        helper.save_inference_samples(runs_dir, data_dir, sess, image_shape, logits, keep_prob_tensor, vgg_input_tensor)
#        save_inference_samples(runs_dir, data_dir, sess, image_shape, logits, keep_prob_tensor, vgg_input_tensor,'FINAL')

         
        # OPTIONAL: Apply the trained model to a video


if __name__ == '__main__':
    run()
