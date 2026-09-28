from results_store import save_result

async def run_tb_diagnostics(self, image_path: str, audio_path: str, user_id: int) -> Dict[str, Any]:
    """
    Only runs TB analysis if explicitly requested. Includes shareable result link.
    """
    try:
        result = await self.health_module.evaluate_tb_risk(image_path, audio_path, user_id)

        # Save result and generate private link
        filename = save_result(result)
        shareable_link = f"https://huggingface.co/spaces/Raiff1982/codriao/blob/main/results/{filename}"
        result["shareable_link"] = shareable_link

        logger.info(f"TB Diagnostic Result stored as {filename}")
        return result

    except Exception as e:
        logger.error(f"TB diagnostics failed: {e}")
        return {
            "tb_risk": "ERROR",
            "error": str(e),
            "image_analysis": {},
            "audio_analysis": {},
            "ethical_analysis": "Unable to complete TB diagnostic.",
            "explanation": None,
            "system_health": None,
            "shareable_link": None
        }
