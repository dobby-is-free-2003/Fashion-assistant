# Cloud Run (optional, do this last)
Local is the default. Cloud Run containers are stateless, so SQLite and Qdrant in /tmp reset on restart: good for a demo, not for real use
(production swap: Firestore + Vertex AI Vector Search + Cloud Storage for images; not built in the free version).
1. Set a budget alert and quota caps in the Cloud Console first. Never send real photos on the free Gemini tier.
2. `gcloud run deploy fashion-api --source . --region asia-south1 --min-instances 0 --max-instances 2 --set-secrets GEMINI_API_KEY=gemini-key:latest`
3. The Streamlit UI is run locally against the same code; the API exposes /health /looks /choice /tryon/{id} /trends /privacy/delete.
Check current Cloud Run free-tier limits and pricing before deploying.
## Colab try-on (ColabNotebookProvider)
Select provider `colab`, preview a look: a job appears in data/tryon_jobs/<id>/ (person.png, garment.png). Run an open-source
try-on model (CatVTON, IDM-VTON, OOTDiffusion) in a free Colab or Kaggle GPU, save the output as data/tryon_results/<id>.png, preview again.
