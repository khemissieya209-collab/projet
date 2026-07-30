from fastapi import APIRouter, UploadFile, File
import os

from backend.services.pdf_extraction import extract_document
from backend.agents.esg_analyzer import analyze_esg
from backend.agents.greenwashing_detector import detect_greenwashing
from backend.agents.strategy_generator import generate_strategy
from backend.schemas.pipeline_schema import PipelineResult

router = APIRouter()


import time

@router.post("/upload", response_model=PipelineResult)
async def upload_pdf(file: UploadFile = File(...)):
    start_time = time.perf_counter()

    # Créer le dossier uploads s'il n'existe pas
    os.makedirs("backend/uploads", exist_ok=True)

    # Sauvegarder le PDF
    file_path = f"backend/uploads/{file.filename}"

    with open(file_path, "wb") as f:
        f.write(await file.read())

    # Extraire le document avec le pipeline robuste
    t0 = time.perf_counter()
    doc = extract_document(file_path)
    text = doc.full_text
    print(f"Extraction: {time.perf_counter() - t0:.2f}s")
    print(f"[Pipeline] Extracted {doc.total_pages} pages via {doc.extraction_method}")
    print(f"[Pipeline] Tables found: {doc.has_tables} | Scanned pages: {doc.has_scanned_pages}")
    print(f"[Pipeline] Total text length: {len(text)} chars")

    # Lancer l'analyse ESG (Agent 1)
    t0 = time.perf_counter()
    esg_result = analyze_esg(text)
    print(f"ESG Agent: {time.perf_counter() - t0:.2f}s")

    # Détecter le greenwashing (Agent 2) — receives full text for evidence search
    t0 = time.perf_counter()
    gw_result = detect_greenwashing(esg_result, text)
    print(f"Greenwashing Agent: {time.perf_counter() - t0:.2f}s")

    # Générer la stratégie (Agent 3)
    t0 = time.perf_counter()
    strategy_result = generate_strategy(esg_result, gw_result)
    print(f"Strategy Agent: {time.perf_counter() - t0:.2f}s")

    print(f"Total pipeline execution: {time.perf_counter() - start_time:.2f}s")

    # Retourner le résultat complet du pipeline
    return PipelineResult(
        esg_analysis=esg_result,
        greenwashing=gw_result,
        strategy=strategy_result
    )