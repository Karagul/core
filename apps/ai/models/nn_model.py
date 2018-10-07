import logging
import time
from django.db import models

from unixtimestampfield.fields import UnixTimeStampField
from apps.common.utilities.s3 import download_file_from_s3
from settings import RUN_ANN, SOURCE_CHOICES

logger = logging.getLogger(__name__)

if RUN_ANN:
    from keras.models import load_model


# AnnModel is a not very smart way to store all keras models we have in the system
# we can load the model by 's3_model_file'
# TODO: remove storing it in DB and keep all models in named dictionary?


class AnnModel(models.Model):
    '''
    Keep all NN models in a database table, so we can keep track of which indicator value
    was calculated with which NN model and be able to reproduce it
    '''

    timestamp = UnixTimeStampField(null=False)
    source = models.SmallIntegerField(choices=SOURCE_CHOICES, null=False)
    model_name = models.CharField(max_length=32, null=False, blank=False)
    s3_model_file = models.TextField(null=False, blank=False)
    s3_notebook_file = models.TextField(null=True)

    period = models.PositiveSmallIntegerField(null=False, blank=False) # 10min, we use full price table, not resampled
    slide_win_size = models.SmallIntegerField(null=False, blank=False)
    predicted_win_size = models.SmallIntegerField(null=False, blank=False)
    delta_tolerance = models.FloatField(null=False)

    train_accuracy = models.FloatField(null=True)
    train_f1_score = models.FloatField(null=True)
    validation_accuracy = models.FloatField(null=True)
    validation_f1_score = models.FloatField(null=True)

    train_data_description = models.TextField(null=True, blank=True)
    features_description = models.TextField(null=True, blank=True)

    keras_model = None

    # download keras model from s3 into keras model
    def initialize(self):
        logger.debug(" >> Start Loading Keras Model..." + self.s3_model_file)
        if self.keras_model:
            logger.debug(" >> KERAS model exists and returned !")
            return self.keras_model
        else:
            download_file_from_s3(self.s3_model_file)
            self.keras_model = load_model(self.s3_model_file) # 'lstm_model.h5'
            logger.debug(" >> KERAS model loaded and returned!")
            return self.keras_model


# download model file from s3 to local then import it into keras model, then return this keras model
def get_ann_model_object(s3_model_file):
    start = time.time()

    ann_model = AnnModel.objects.get(s3_model_file=s3_model_file) ## get ann model metainfo from DB(django objects.get)

    if not ann_model.keras_model:
        try:
            ann_model.initialize()   # download model from S3, save it on local disk, then upload to class
            logger.info(">> ANN model loaded FIRST TIME, ELapsed time: " + str(time.time() - start) + s3_model_file)
        except Exception as e:
            logger.error(" Cannot load ANN model: either no Model in DB or S3 file does not exist")
    else:
        logger.info(">> get ANN model from CACHE, elapsed time: " + str(time.time() - start))

    return ann_model



