import numpy as np
import tensorflow as tf
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing import image
import cv2
import json
import tempfile
import logging
import shutil
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

class ModelLoader:
    def __init__(self):
        # Resolve paths relative to repository root (two levels up from this file)
        repo_root = Path(__file__).resolve().parents[1]
        self.model_path = repo_root / "model" / "model.h5"
        self.classes_path = repo_root / "model" / "classes.json"

        try:
            logger.info("Loading model from %s", self.model_path)
            self.model = load_model(str(self.model_path))
        except Exception as e:
            logger.exception("Failed to load the Keras model: %s", str(e))
            # re-raise so server startup shows the error
            raise

        try:
            with open(self.classes_path, "r") as f:
                self.class_names = json.load(f)
        except Exception as e:
            logger.exception("Failed to load classes.json at %s: %s", self.classes_path, str(e))
            raise

        # Validate the model output shape matches the number of classes to avoid runtime failures
        try:
            output_shape = getattr(self.model, 'output_shape', None)
            # output_shape may be e.g. (None, N) or (None, rows, cols, N) depending on model
            # find the last non-None integer in output_shape
            inferred_units = None
            if output_shape:
                out_shape = list(output_shape)
                # try to find a positive integer in the last axis
                for dim in reversed(out_shape):
                    if isinstance(dim, int) and dim > 0:
                        inferred_units = dim
                        break

            classes_len = len(self.class_names) if self.class_names is not None else 0
            logger.info("Model output_shape=%s, inferred_units=%s, classes_len=%s", output_shape, inferred_units, classes_len)

            # If inferred_units is known and differs from classes length, auto-adjust class_names
            # by padding or truncating. This prevents runtime IndexError while warning the developer.
            if inferred_units is not None and inferred_units != classes_len:
                logger.warning("Model output shape units (%s) do not match classes.json length (%s). Auto-adjusting in memory and on-disk.", inferred_units, classes_len)
                if classes_len < inferred_units:
                    # pad with placeholders class_{i}
                    placeholders = [f"class_{i}" for i in range(classes_len, inferred_units)]
                    self.class_names.extend(placeholders)
                    logger.warning("Extended classes.json in-memory with placeholders: %s", placeholders)
                else:
                    # truncate the list to match model output
                    removed = self.class_names[inferred_units:]
                    self.class_names = self.class_names[:inferred_units]
                    logger.warning("Truncated classes.json in-memory. Removed: %s", removed)
                # Attempt to persist the change: create a timestamped backup first, then overwrite classes.json
                try:
                    # backup original file
                    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                    backup_path = str(self.classes_path) + f".bak-{timestamp}"
                    shutil.copyfile(str(self.classes_path), backup_path)
                    logger.info("Backed up original classes.json to %s", backup_path)

                    # write the updated class list back to disk
                    with open(self.classes_path, 'w', encoding='utf-8') as f:
                        json.dump(self.class_names, f, indent=4)
                    logger.info("Updated classes.json on disk with %s entries.", len(self.class_names))
                except Exception as e:
                    logger.exception("Failed to backup or write classes.json: %s", str(e))
        except Exception:
            # Re-raise so startup fails with the message (user should fix classes or model)
            logger.exception("Model/class count validation failed")
            raise

    def preprocess(self, img_bytes):
        temp = tempfile.NamedTemporaryFile(delete=False)
        temp.write(img_bytes)
        temp.close()

        img = image.load_img(temp.name, target_size=(75, 100))
        img_array = image.img_to_array(img)
        img_array = np.expand_dims(img_array, axis=0) / 255.0
        return img_array

    def predict(self, img_bytes):
        try:
            img = self.preprocess(img_bytes)
        except Exception as e:
            logger.exception("Failed to preprocess image: %s", str(e))
            raise

        try:
            preds_raw = self.model.predict(img)
            # Convert to numpy array and reduce spatial dims if needed to produce class vector
            preds = np.asarray(preds_raw)
            # Remove leading batch dimension if present
            if preds.ndim >= 2 and preds.shape[0] == 1:
                preds = preds[0]
            # If multi-dimensional (e.g., H, W, C), reduce spatial dimensions by mean to get (C,)
            if preds.ndim > 1:
                # average across all axes except the last
                reduce_axes = tuple(range(preds.ndim - 1))
                preds = preds.mean(axis=reduce_axes)
            preds = np.asarray(preds).ravel()
        except Exception as e:
            # Log the shape and dtype to help debug keras errors
            try:
                logger.error("Prediction failed. Input shape: %s, dtype: %s", getattr(img, 'shape', 'unknown'), getattr(img, 'dtype', 'unknown'))
            except Exception:
                pass
            logger.exception("Model.predict raised an exception: %s", str(e))
            raise
        # Validate predictions and class names
        try:
            index = int(np.argmax(preds))
        except Exception as e:
            logger.exception("argmax failed on predictions: %s", str(e))
            raise

        # Debugging log: shapes and lengths
        try:
            preds_len = len(preds)
            classes_len = len(self.class_names)
        except Exception:
            preds_len = 'unknown'
            classes_len = 'unknown'
        logger.info("Predictions length: %s, classes length: %s, argmax index: %s", preds_len, classes_len, index)

        if isinstance(classes_len, int) and isinstance(index, int) and index >= classes_len:
            # Instead of raising, provide a fallback label and log a warning.
            # The class name might be a placeholder (if we padded earlier) or we generate one on-the-fly.
            fallback_label = f"class_{index}"
            logger.warning("Predicted index %s is out of range for class_names (len=%s). Using fallback label '%s'. Full preds: %s", index, classes_len, fallback_label, np.array2string(preds, precision=4, separator=','))
            class_name = fallback_label

        confidence = float(preds[index])
        class_name = self.class_names[index]
        return class_name, index, confidence

    def explain(self, img_bytes):
        img = self.preprocess(img_bytes)
        grad_model = tf.keras.models.Model(
            [self.model.inputs],
            [self.model.get_layer(self.model.layers[-3].name).output, self.model.output]
        )

        with tf.GradientTape() as tape:
            conv_outputs, predictions = grad_model(img)
            class_idx = tf.argmax(predictions[0])
            loss = predictions[:, class_idx]

        grads = tape.gradient(loss, conv_outputs)
        guided_grads = tf.reduce_mean(grads, axis=(0, 1, 2))
        conv_outputs = conv_outputs[0]

        heatmap = tf.reduce_sum(tf.multiply(guided_grads, conv_outputs), axis=-1).numpy()
        heatmap = np.maximum(heatmap, 0)

        heatmap = cv2.resize(heatmap, (100, 75))
        max_val = heatmap.max() if heatmap.size > 0 else 0
        if max_val != 0:
            heatmap = heatmap / max_val
        else:
            logger.warning("Heatmap has max value 0; normalization skipped.")

        # Save temporary image
        heatmap_path = tempfile.NamedTemporaryFile(suffix=".png", delete=False).name
        cv2.imwrite(heatmap_path, np.uint8(255 * heatmap))

        return heatmap_path
