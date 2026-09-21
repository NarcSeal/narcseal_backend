from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.officer import Officer
from app.routers.test_records import get_current_officer
import os
import cv2
import numpy as np
import sys

# Add narcseal_ai_core to path to import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../narcseal_ai_core")))
from reference_detector import ReferenceDetector
from calibration_engine import CalibrationEngine
from reaction_analyzer import ReactionAnalyzer

router = APIRouter(prefix="/ai", tags=["AI Processing"])

reference_detector = ReferenceDetector()
calibration_engine = CalibrationEngine()
reaction_analyzer = ReactionAnalyzer()

@router.post("/analyze-frame")
async def analyze_frame(
    kit_type: str = Form(...),
    file: UploadFile = File(...),
    current_officer: Officer = Depends(get_current_officer)
):
    """
    Accepts an image frame, detects the reference card, applies calibration, 
    and analyzes the drug reaction.
    """
    try:
        contents = await file.read()
        nparr = np.frombuffer(contents, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if frame is None:
            return {"status": "error", "message": "Invalid image"}

        # Check lighting
        lighting_status = reference_detector.check_lighting(frame)
        
        # 1. Detect Card
        warped_card = reference_detector.detect_and_warp_card(frame)
        if warped_card is None:
            return {"status": "card_not_detected", "lighting": lighting_status}

        # 2. Extract reference patches
        captured_rgb_patches = reference_detector.extract_calibration_patches(warped_card)
        if not captured_rgb_patches:
            return {"status": "card_not_detected", "message": "Patches not found"}

        # 3. Compute CCM
        ccm = calibration_engine.compute_ccm(captured_rgb_patches)

        # 4. Extract Test Strip Reaction Color
        # Assuming the test strip is at a known position relative to the reference patches
        # For this prototype, we'll extract it from the center of the warped card
        test_patch_radius = 20
        y, x = 200, 300 # Center of 600x400 card
        roi = warped_card[y-test_patch_radius:y+test_patch_radius, x-test_patch_radius:x+test_patch_radius]
        avg_color_per_row = np.average(roi, axis=0)
        avg_color = np.average(avg_color_per_row, axis=0)
        test_strip_rgb = [avg_color[2], avg_color[1], avg_color[0]] # BGR to RGB

        # 5. Apply CCM and Analyze Reaction
        corrected_lab = calibration_engine.apply_ccm(ccm, test_strip_rgb)
        
        analysis_result = reaction_analyzer.analyze_reaction(kit_type, corrected_lab)
        
        if analysis_result.get("status") == "error":
            return analysis_result

        return {
            "status": "success",
            "lighting": lighting_status,
            "analysis": analysis_result
        }
    except Exception as e:
        print(f"Error in analyze_frame: {e}")
        return {"status": "error", "message": str(e)}
