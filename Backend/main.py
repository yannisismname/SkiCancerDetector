from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from model_loader import ModelLoader
from fastapi.responses import JSONResponse
import uvicorn
import logging
import traceback

app = FastAPI(title="Skin Cancer AI Backend API")

# Configure logging
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Allow frontend to talk to backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load model
try:
    ml = ModelLoader()
    logger.info("Model loaded successfully")
except Exception as e:
    logger.exception("Failed to load model at startup: %s", str(e))
    # Re-raise so uvicorn shows the error and prevents the server from running if the model fails
    raise

@app.get("/")
def root():
    return {"message": "Skin Cancer AI Backend is running"}


@app.get("/diagnose")
def diagnose():
    # Provide a small diagnostic endpoint that returns model output shape and classes length
    try:
        output_shape = getattr(ml.model, 'output_shape', None)
        class_count = len(ml.class_names)
        # also provide a sample of the class names (up to 20) for quick inspection
        class_sample = ml.class_names[:20] if hasattr(ml, 'class_names') else []
        return {
            "model_output_shape": list(output_shape) if output_shape is not None else None,
            "class_count": class_count
            ,"class_sample": class_sample
        }
    except Exception as e:
        logger.exception("Error in /diagnose endpoint: %s", str(e))
        return JSONResponse({"error": "Server error during diagnose", "detail": str(e)}, status_code=500)

@app.post("/predict")
async def predict(image: UploadFile = File(...)):
    img_bytes = await image.read()
    try:
        pred_class, pred_index, confidence = ml.predict(img_bytes)
        return JSONResponse({
            "prediction": pred_class,
            "confidence": confidence
        })
    except Exception as e:
        # Log full traceback server-side
        logger.exception("Error during prediction: %s", str(e))
        # For local dev/debugging: return the exception string so the frontend can display more details
        # In production, remove the 'detail' field or use a safe error message
        return JSONResponse({"error": "Server error during prediction", "detail": str(e)}, status_code=500)

@app.post("/explain")
async def explain(image: UploadFile = File(...)):
    img_bytes = await image.read()
    try:
        heatmap_path = ml.explain(img_bytes)
        return {"heatmap": heatmap_path}
    except Exception as e:
        logger.exception("Error during explanation generation: %s", str(e))
        return JSONResponse({"error": "Server error during explanation generation", "detail": str(e)}, status_code=500)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=5000, reload=True)
