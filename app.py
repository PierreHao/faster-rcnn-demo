#!/usr/bin/env python

# --------------------------------------------------------
# Faster R-CNN
# Copyright (c) 2015 Microsoft
# Licensed under The MIT License [see LICENSE for details]
# Written by Ross Girshick
# --------------------------------------------------------

"""
Demo script showing detections in sample images.

See README.md for installation instructions before running.
"""

import _init_paths
from fast_rcnn.config import cfg
from fast_rcnn.test import im_detect
from fast_rcnn.nms_wrapper import nms
from utils.timer import Timer
import numpy as np
import scipy.io as sio
import caffe, os, sys, cv2
import argparse

from flask import Flask, request, jsonify, render_template

CLASSES = ('__background__',
           'aeroplane', 'bicycle', 'bird', 'boat',
           'bottle', 'bus', 'car', 'cat', 'chair',
           'cow', 'diningtable', 'dog', 'horse',
           'motorbike', 'person', 'pottedplant',
           'sheep', 'sofa', 'train', 'tvmonitor')

NETS = {'vgg16': ('VGG16',
                  'VGG16_faster_rcnn_final.caffemodel'),
        'zf': ('ZF',
                  'ZF_faster_rcnn_final.caffemodel')}

app = Flask(__name__, static_folder='html')
app.config['UPLOAD_FOLDER'] =  './uploaded'
app.config['STATIC_DIR'] =  './html'
app.config['predict_file'] = "predict_file"

@app.route('/')
def index():
	return render_template('index.html')

@app.route('/html/<path:path>')
def send_html(path):
	return send_from_directory('html', path)

@app.route('/predict', methods=['POST'])
def predict():
    print("in predict")
    file = request.files['upload']
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], app.config["predict_file"]))
    print("object_detect")    
    objects = detect_objects(os.path.join(app.config['UPLOAD_FOLDER'], app.config["predict_file"]))
    print(objects)
    resJson = objects
    response = jsonify(resJson)
    return response

def detect_positions(im, class_name, dets, thresh=0.5):
    """Draw detected bounding boxes."""
    inds = np.where(dets[:, -1] >= thresh)[0]
    if len(inds) == 0:
        return ""

    im = im[:, :, (2, 1, 0)]
    results = dict()
    for i in inds:
        bbox = dets[i, :4]
        score = dets[i, -1]

        results[str(i)] = { "x" : int(bbox[0]),  "y" : int(bbox[1]),  "width" : int(bbox[2] - bbox[0]),  "height" : int(bbox[3] - bbox[1]), "score" : str(score), "class_name" : class_name }
    return results


def detect_objects(imgpath):
    """Detect object classes in an image using pre-computed object proposals."""

    print("in detect object")    
    # Load the demo image
    im_file = os.path.join(imgpath)
    im = cv2.imread(im_file)
    print("read image")

    # Detect all object classes and regress object bounds
    timer = Timer()
    timer.tic()
    print("im_detect")
    scores, boxes = im_detect(app.config['net'], im)
    timer.toc()
    print ('Detection took {:.3f}s for '
           '{:d} object proposals').format(timer.total_time, boxes.shape[0])

    # Visualize detections for each class
    CONF_THRESH = 0.8
    NMS_THRESH = 0.3
    results = dict()
    for cls_ind, cls in enumerate(CLASSES[1:]):
        cls_ind += 1 # because we skipped background
        cls_boxes = boxes[:, 4*cls_ind:4*(cls_ind + 1)]
        cls_scores = scores[:, cls_ind]
        dets = np.hstack((cls_boxes,
                          cls_scores[:, np.newaxis])).astype(np.float32)
        keep = nms(dets, NMS_THRESH)
        dets = dets[keep, :]
        results[cls] = detect_positions(im, cls, dets, thresh=CONF_THRESH)
    return results

def parse_args():
    """Parse input arguments."""
    parser = argparse.ArgumentParser(description='Faster R-CNN demo')
    parser.add_argument('--gpu', dest='gpu_id', help='GPU device id to use [0]',
                        default=0, type=int)
    parser.add_argument('--cpu', dest='cpu_mode',
                        help='Use CPU mode (overrides --gpu)',
                        action='store_true')
    parser.add_argument('--net', dest='demo_net', help='Network to use [vgg16]',
                        choices=NETS.keys(), default='vgg16')

    args = parser.parse_args()

    return args

if __name__ == '__main__':
    cfg.TEST.HAS_RPN = True  # Use RPN for proposals

    args = parse_args()

    prototxt = os.path.join(cfg.ROOT_DIR, 'models', NETS[args.demo_net][0],
                            'faster_rcnn_alt_opt', 'faster_rcnn_test.pt')
    caffemodel = os.path.join(cfg.ROOT_DIR, 'data', 'faster_rcnn_models',
                              NETS[args.demo_net][1])

    if not os.path.isfile(caffemodel):
        raise IOError(('{:s} not found.\nDid you run ./data/script/'
                       'fetch_faster_rcnn_models.sh?').format(caffemodel))

    if args.cpu_mode:
        caffe.set_mode_cpu()
    else:
        caffe.set_mode_gpu()
        caffe.set_device(args.gpu_id)
        cfg.GPU_ID = args.gpu_id
    app.config['net'] = caffe.Net(prototxt, caffemodel, caffe.TEST)

    print '\n\nLoaded network {:s}'.format(caffemodel)

    app.run(debug=True, port=5000, host='0.0.0.0')

