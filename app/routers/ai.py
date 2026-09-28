from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.officer import Officer
from app.dependencies import get_current_officer
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
    Accepts an image frame, detects the reference card AND the drug test kit,
    applies color calibration, and analyzes the drug reaction color.

    The reference card and drug test kit are SEPARATE objects in the frame.
    The reference card provides color calibration; the drug kit provides
    the reaction color to analyze.

    Flow:
    1. Check lighting — returns 'too_dark' if brightness < threshold
    2. Detect reference card via multi-layer contour + colour-patch validation
    3. If card found: extract 6 calibration patches, compute CCM
    4. Look for drug test kit OUTSIDE the card area in the frame
    5. If kit found: extract its reaction color, apply CCM, analyze against drug dictionary

    Returns:
    - {status: 'card_not_detected'}         — reference card not found
    - {status: 'card_detected_no_strip'}    — card found + calibrated, but no drug kit visible
    - {status: 'success', analysis: {...}}  — card + kit detected, full analysis complete
    - {status: 'error', message: ...}       — unexpected failure
    """
    try:
        contents = await file.read()
        nparr = np.frombuffer(contents, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if frame is None:
            return {"status": "error", "message": "Invalid image — could not decode frame"}

        # ── Step 1: Check lighting ─────────────────────────────────
        with open("detection_debug.log", "a") as f:
            f.write(f"\n--- New Frame ---\n")
            
        lighting_status = reference_detector.check_lighting(frame)
        if lighting_status == "too_dark":
            with open("detection_debug.log", "a") as f:
                f.write(f"Result: too dark\n")
            return {"status": "card_not_detected", "lighting": "too_dark"}

        # ── Step 2: Detect and warp the reference card ─────────────
        warped_card = reference_detector.detect_and_warp_card(frame)
        if warped_card is None:
            with open("detection_debug.log", "a") as f:
                f.write(f"Result: card not detected\n")
            return {"status": "card_not_detected", "lighting": lighting_status}
            
        with open("detection_debug.log", "a") as f:
            f.write(f"Result: card DETECTED!\n")

        # ── Step 3: Extract 6 calibration patches from reference card
        captured_rgb_patches = reference_detector.extract_calibration_patches(warped_card)
        if not captured_rgb_patches or len(captured_rgb_patches) < 6:
            return {
                "status": "card_not_detected",
                "lighting": lighting_status,
                "message": "Reference patches not found"
            }

        # ── Step 4: Compute Color Correction Matrix ────────────────
        try:
            ccm = calibration_engine.compute_ccm(captured_rgb_patches)
        except Exception as e:
            print(f"[AI] Calibration error: {e}")
            return {"status": "error", "message": f"Calibration failed: {str(e)}"}

        # ── Step 5: Find the card contour for kit detection ────────
        # We need the card's location in the frame to exclude it
        card_contour = reference_detector.get_card_contour(frame)

        # ── Step 6: Detect drug test kit OUTSIDE the card area ─────
        kit_info = reference_detector.detect_drug_kit(frame, card_contour)

        if kit_info is None:
            # Card found and calibrated, but no drug kit detected yet
            return {
                "status": "card_detected_no_strip",
                "lighting": lighting_status,
                "calibration": "complete",
                "message": "Reference card detected ✓ Place the drug test kit next to the card.",
            }

        # ── Step 7: Extract the drug kit reaction color ────────────
        kit_reaction_rgb = reference_detector.extract_kit_reaction_color(frame, kit_info)
        if kit_reaction_rgb is None:
            return {
                "status": "card_detected_no_strip",
                "lighting": lighting_status,
                "calibration": "complete",
                "message": "Drug kit detected but could not extract reaction color. Adjust position.",
            }

        # ── Step 8: Apply CCM and analyze reaction ─────────────────
        corrected_lab = calibration_engine.apply_ccm(ccm, kit_reaction_rgb)
        analysis_result = reaction_analyzer.analyze_reaction(kit_type, corrected_lab)

        if analysis_result.get("status") == "error":
            return analysis_result

        print(f"[AI] Analysis complete: {analysis_result['result']} "
              f"substance={analysis_result['substance']} "
              f"confidence={analysis_result['confidence']}% "
              f"hex={analysis_result.get('hex_code', 'N/A')} "
              f"color={analysis_result.get('color_name', 'N/A')}")

        return {
            "status": "success",
            "lighting": lighting_status,
            "card_detected": True,
            "strip_detected": True,
            "calibration": "complete",
            "analysis": analysis_result,
            "raw_reaction_rgb": kit_reaction_rgb,
            "kit_type": kit_type,
            "kit_region": {
                "x": kit_info['bbox'][0],
                "y": kit_info['bbox'][1],
                "width": kit_info['bbox'][2],
                "height": kit_info['bbox'][3],
            },
        }

    except Exception as e:
        # Log internally for debugging but don't expose raw errors to the app
        import traceback
        traceback.print_exc()
        return {"status": "card_not_detected", "lighting": "ok", "message": "Detection processing error - retrying"}
