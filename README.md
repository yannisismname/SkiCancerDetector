# Skin Cancer AI - Dev Run & Debugging

This README provides simple steps to run the backend and frontend, and common troubleshooting for the "Failed to fetch" error that the front-end reports.

## Run backend

1. Open a terminal and navigate to the `Backend` folder.

```powershell
cd 'c:\Users\Lawrence Akosen\OneDrive\Desktop\Software engineering project\Backend'
python -m uvicorn main:app --host 0.0.0.0 --port 5000 --reload
```

You should see output with `INFO` messages. Look for `Model loaded successfully`.

## Run frontend

From the `frontend` folder, it's best to run a simple static server. If you open the file directly with `file://` it sometimes has different origin behavior in your browser.

```powershell
cd 'c:\Users\Lawrence Akosen\OneDrive\Desktop\Software engineering project\frontend'
python -m http.server 5000
```

Then browse to: http://localhost:5500

## Troubleshooting: Failed to fetch

1. Is the server running? Open http://localhost:5000 in a browser; you should see a JSON message.
2. Check the Network tab in DevTools when you click "Analyze Image":
   - Is the request being sent? If not, check javascript errors in Console.
   - Does the request show a `CORS` error? If it does, confirm the backend CORS settings allow the frontend origin.
   - If the request doesn't reach the server (status "(failed)" or network error), check backend logs for exceptions and check your firewall.
3. If the backend returns 5xx, the new backend logging will print a server-side exception; check the terminal running the backend for stack trace.
4. If you're testing from an HTTPS page (e.g., Netlify), calling `http://localhost:5000` will be blocked (Mixed Content). Use a local static dev server on `http` for testing.

## Quick curl test

From a terminal, try:

```powershell
cd '..\frontend'
curl http://localhost:5000/
# with an example image
curl -X POST -F "image=@path\to\img.jpg" http://localhost:5000/predict
```

## Next steps if the error persists

- Confirm `model/model.h5` and `model/classes.json` exist and are readable.
- Confirm your backend prints `Model loaded successfully` at startup (if not, check the error message and stacktrace in terminal running the backend).
- If `predict` still fails, check the console that now logs exceptions in `main.py` and `model_loader.py` and copy the stacktrace into a reply here so I can help interpret it.

---
If you want, paste the server logs (the terminal running `uvicorn`) showing the error and I can help decode the stack trace and next steps.
