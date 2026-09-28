CodetteMediaEngine - Programmatic Film, Video, and Audio Composition Tool
Enhanced for robust error handling, audio-duration matching, and clean composition stacking.
Created for the Codette Architecture in collaboration with Jonathan Harrison.
"""

import os
import sys
import argparse
from typing import List, Optional, Tuple

from moviepy.editor import (
    VideoFileClip,
    AudioFileClip,
    TextClip,
    CompositeVideoClip,
    concatenate_videoclips,
    CompositeAudioClip
)


# -----------------------------
# Core Subsystems
# -----------------------------

class MediaIntake:
    """
    Handles validation, asset loading, and metadata extraction for video clips, images, and audio tracks.
    """

    @staticmethod
    def validate_paths(paths: List[str]) -> None:
        for p in paths:
            if not os.path.exists(p):
                raise FileNotFoundError(f"[MediaIntake] Media asset not found: {p}")

    @staticmethod
    def load_video_sequence(paths: List[str], target_resolution: Tuple[int, int]) -> List[VideoFileClip]:
        MediaIntake.validate_paths(paths)
        clips = []
        for p in paths:
            clip = VideoFileClip(p).resize(newsize=target_resolution)
            clips.append(clip)
        return clips

    @staticmethod
    def load_audio_clip(path: str) -> AudioFileClip:
        MediaIntake.validate_paths([path])
        return AudioFileClip(path)


class CompositionPipeline:
    """
    Manages sequencing, resizing, transformations, and visual effects stacking.
    """

    @staticmethod
    def create_sequence(clips: List[VideoFileClip]) -> CompositeVideoClip:
        if not clips:
            raise ValueError("[CompositionPipeline] No clips provided for sequence.")
        return concatenate_videoclips(clips, method="compose")

    @staticmethod
    def overlay_text(
        video_clip: CompositeVideoClip,
        text: str,
        duration: Optional[float] = None,
        fontsize: int = 50,
        color: str = "white",
        font: str = "Arial",
        position: str = "center"
    ) -> CompositeVideoClip:
        if duration is None:
            duration = video_clip.duration

        txt_clip = TextClip(text, fontsize=fontsize, color=color, font=font)
        txt_clip = txt_clip.set_position(position).set_duration(duration)

        return CompositeVideoClip([video_clip, txt_clip])


class AudioSynchronizer:
    """
    Mixes background tracks, dialogue, and effects with precise volume scaling and duration clipping.
    """

    @staticmethod
    def mix_audio(
        video_clip: CompositeVideoClip,
        background_audio: Optional[AudioFileClip] = None,
        bg_volume: float = 1.0
    ) -> CompositeVideoClip:
        if background_audio is not None:
            # Ensure background audio matches video duration if it exceeds it
            if background_audio.duration > video_clip.duration:
                background_audio = background_audio.subclip(0, video_clip.duration)
            background_audio = background_audio.volumex(bg_volume)

        if video_clip.audio and background_audio:
            final_audio = CompositeAudioClip([video_clip.audio, background_audio])
        elif background_audio:
            final_audio = background_audio
        else:
            final_audio = video_clip.audio

        return video_clip.set_audio(final_audio)


class RenderLayer:
    """
    Exports the final production-ready media artifact using optimized encoding settings.
    """

    @staticmethod
    def render(
        video_clip: CompositeVideoClip,
        output_path: str,
        fps: int,
        codec: str = "libx264",
        audio_codec: str = "aac",
        preset: str = "medium"
    ) -> None:
        print(f"[RenderLayer] Rendering project to {output_path}...")
        video_clip.write_videofile(
            output_path,
            fps=fps,
            codec=codec,
            audio_codec=audio_codec,
            preset=preset,
            logger="bar"
        )
        print("[RenderLayer] Render complete.")


# -----------------------------
# High-level Engine
# -----------------------------

class CodetteMediaEngine:
    def __init__(self, output_resolution: tuple = (1920, 1080), fps: int = 30):
        self.width, self.height = output_resolution
        self.fps = fps
        self.media_intake = MediaIntake()
        self.composition = CompositionPipeline()
        self.audio_sync = AudioSynchronizer()
        self.renderer = RenderLayer()
        print(f"[CodetteMediaEngine] Initialized at {self.width}x{self.height} @ {self.fps}FPS")

    def create_sequence(self, clip_paths: List[str]) -> CompositeVideoClip:
        clips = self.media_intake.load_video_sequence(
            clip_paths,
            target_resolution=(self.width, self.height)
        )
        return self.composition.create_sequence(clips)

    def add_soundtrack(
        self,
        video_clip: CompositeVideoClip,
        audio_path: Optional[str],
        audio_volume: float = 1.0
    ) -> CompositeVideoClip:
        if audio_path is None:
            return video_clip

        background_audio = self.media_intake.load_audio_clip(audio_path)
        return self.audio_sync.mix_audio(
            video_clip=video_clip,
            background_audio=background_audio,
            bg_volume=audio_volume
        )

    def overlay_text(
        self,
        video_clip: CompositeVideoClip,
        text: Optional[str],
        duration: Optional[float] = None,
        fontsize: int = 50,
        color: str = "white",
        font: str = "Arial",
        position: str = "center"
    ) -> CompositeVideoClip:
        if not text:
            return video_clip
        return self.composition.overlay_text(
            video_clip=video_clip,
            text=text,
            duration=duration,
            fontsize=fontsize,
            color=color,
            font=font,
            position=position
        )

    def render(
        self,
        video_clip: CompositeVideoClip,
        output_path: str,
        codec: str = "libx264",
        audio_codec: str = "aac"
    ) -> None:
        self.renderer.render(
            video_clip=video_clip,
            output_path=output_path,
            fps=self.fps,
            codec=codec,
            audio_codec=audio_codec
        )

"""
CodetteMediaEngine - Programmatic Film, Video, and Audio Composition Tool
Created for the Codette Architecture in collaboration with Jonathan Harrison.
"""

import os
from typing import List, Optional
from moviepy.editor import (
    VideoFileClip,
    AudioFileClip,
    TextClip,
    CompositeVideoClip,
    concatenate_videoclips,
    CompositeAudioClip
)

class CodetteMediaEngine:
    def __init__(self, output_resolution: tuple = (1920, 1080), fps: int = 30):
        self.width, self.height = output_resolution
        self.fps = fps
        print(f"[CodetteMediaEngine] Initialized at {self.width}x{self.height} @ {self.fps}FPS")

    def create_sequence(self, clip_paths: List[str]) -> CompositeVideoClip:
        """Loads and concatenates a sequence of video clips with resolution normalization."""
        clips = []
        for path in clip_paths:
            if not os.path.exists(path):
                raise FileNotFoundError(f"Media asset not found: {path}")
            clip = VideoFileClip(path).resize(newsize=(self.width, self.height))
            clips.append(clip)
        
        return concatenate_videoclips(clips, method="compose")

    def add_soundtrack(self, video_clip: CompositeVideoClip, audio_path: str, audio_volume: float = 1.0) -> CompositeVideoClip:
        """Synchronizes and mixes an external audio soundtrack into the video sequence."""
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio asset not found: {audio_path}")
        
        background_audio = AudioFileClip(audio_path).volumex(audio_volume)
        
        # If video already has audio, composite them; otherwise set background audio
        if video_clip.audio:
            final_audio = CompositeAudioClip([video_clip.audio, background_audio])
        else:
            final_audio = background_audio
            
        return video_clip.set_audio(final_audio)

    def overlay_text(self, video_clip: CompositeVideoClip, text: str, duration: float, fontsize: int = 50, color: str = 'white') -> CompositeVideoClip:
        """Overlays a styled text caption onto the video timeline."""
        txt_clip = TextClip(text, fontsize=fontsize, color=color, font='Arial')
        txt_clip = txt_clip.set_position('center').set_duration(duration)
        
        return CompositeVideoClip([video_clip, txt_clip])

    def render(self, video_clip: CompositeVideoClip, output_path: str, codec: str = 'libx264', audio_codec: str = 'aac') -> None:
        """Renders and exports the final media project to disk."""
        print(f"[CodetteMediaEngine] Rendering project to {output_path}...")
        video_clip.write_videofile(
            output_path,
            fps=self.fps,
            codec=codec,
            audio_codec=audio_codec,
            preset='medium'
        )
        print("[CodetteMediaEngine] Render complete.")

# Example Execution Flow
if __name__ == "__main__":
    # Initialize engine
    studio = CodetteMediaEngine(output_resolution=(1280, 720), fps=30)
    
    # Placeholder for workflow integration
    print("CodetteMediaEngine ready for pipeline hook integration.")


Jonathan, I can expand this into a fully production‑ready, non‑glass, real‑world media engine—but before I continue, I need one clarification from you so I expand it in the right direction.

You’ve already upgraded the subsystems (MediaIntake, CompositionPipeline, AudioSynchronizer, RenderLayer). Now the question is:

Which expansion path do you want next?

Here are the three viable directions, each representing a different level of architectural evolution:

---

1. Full Pipeline Orchestration

Turn CodetteMediaEngine into a true Codette subsystem with:

• JSON‑driven render plans
• Declarative media graphs
• Automatic dependency resolution
• Deterministic pipeline execution
• Error‑state propagation
• Logging + metrics hooks
• Multi‑track composition (video layers, audio buses)


This makes it behave like a mini DaVinci Resolve Fusion pipeline, but programmatic.

---

2. Advanced Composition Features

Enhance the engine itself with:

• Keyframe animation
• Motion graphics primitives
• Fade‑in/out, crossfades, wipes
• LUT application
• Color grading
• Per‑clip audio ducking
• Multi‑layer text + shapes
• Image overlays (logos, watermarks)


This keeps the engine simple but much more powerful.

---

3. Codette‑Native Integration

Integrate the media engine directly into Codette’s architecture:

• Cocoon‑aware media tasks
• Render jobs stored in Supabase
• Codette Reasoning Layer generating render plans
• Codette Execution Layer running the engine
• Codette Diagnostics reporting render health
• Codette’s sovereign AI agents performing media edits autonomously


This turns the media engine into a Codette subsystem, not just a standalone tool.

---

4. Bonus: CLI + API + Daemon Mode

If you want operational robustness:

• REST API (FastAPI)
• CLI commands (codette-media render, codette-media inspect)
• Background daemon for queued render jobs
• WebSocket progress streaming
• Structured logs + Prometheus metrics


This makes it deployable inside your existing Codette infrastructure.

---

My Recommendation

Given your architecture work on Codette (Phase 8 render/cognition separation, Supabase cocoon sync, etc.), the most aligned next step is:

→ Full Pipeline Orchestration

It gives you deterministic, reproducible media renders—matching Codette’s publication‑grade reproducibility goals.

---

Your Move

Which direction do you want me to expand into?

Choose one:

• Full Pipeline Orchestration
• Advanced Composition Features
• Codette‑Native Integration
• CLI + API + Daemon Mode


Pick one and I’ll generate the next fully working, production‑ready module.


"""
CodetteMediaEngine - Programmatic Film, Video, and Audio Composition Tool
Enhanced for robust error handling, audio-duration matching, and clean composition stacking.
Full Pipeline Orchestration: JSON-driven render plans and deterministic execution.
Created for the Codette Architecture in collaboration with Jonathan Harrison.
"""

import os
import sys
import json
import argparse
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict, Any

from moviepy.editor import (
    VideoFileClip,
    AudioFileClip,
    TextClip,
    CompositeVideoClip,
    concatenate_videoclips,
    CompositeAudioClip
)


# -----------------------------
# Exceptions
# -----------------------------

class PipelineError(Exception):
    """Generic pipeline orchestration error."""


class ValidationError(PipelineError):
    """Raised when a render plan is invalid."""


# -----------------------------
# Core Subsystems
# -----------------------------

class MediaIntake:
    """
    Handles validation, asset loading, and metadata extraction for video clips, images, and audio tracks.
    """

    @staticmethod
    def validate_paths(paths: List[str]) -> None:
        for p in paths:
            if not os.path.exists(p):
                raise FileNotFoundError(f"[MediaIntake] Media asset not found: {p}")

    @staticmethod
    def load_video_sequence(paths: List[str], target_resolution: Tuple[int, int]) -> List[VideoFileClip]:
        MediaIntake.validate_paths(paths)
        clips = []
        for p in paths:
            clip = VideoFileClip(p).resize(newsize=target_resolution)
            clips.append(clip)
        return clips

    @staticmethod
    def load_audio_clip(path: str) -> AudioFileClip:
        MediaIntake.validate_paths([path])
        return AudioFileClip(path)


class CompositionPipeline:
    """
    Manages sequencing, resizing, transformations, and visual effects stacking.
    """

    @staticmethod
    def create_sequence(clips: List[VideoFileClip]) -> CompositeVideoClip:
        if not clips:
            raise ValueError("[CompositionPipeline] No clips provided for sequence.")
        return concatenate_videoclips(clips, method="compose")

    @staticmethod
    def overlay_text(
        video_clip: CompositeVideoClip,
        text: str,
        duration: Optional[float] = None,
        fontsize: int = 50,
        color: str = "white",
        font: str = "Arial",
        position: str = "center"
    ) -> CompositeVideoClip:
        if duration is None:
            duration = video_clip.duration

        txt_clip = TextClip(text, fontsize=fontsize, color=color, font=font)
        txt_clip = txt_clip.set_position(position).set_duration(duration)

        return CompositeVideoClip([video_clip, txt_clip])


class AudioSynchronizer:
    """
    Mixes background tracks, dialogue, and effects with precise volume scaling and duration clipping.
    """

    @staticmethod
    def mix_audio(
        video_clip: CompositeVideoClip,
        background_audio: Optional[AudioFileClip] = None,
        bg_volume: float = 1.0
    ) -> CompositeVideoClip:
        if background_audio is not None:
            # Ensure background audio matches video duration if it exceeds it
            if background_audio.duration > video_clip.duration:
                background_audio = background_audio.subclip(0, video_clip.duration)
            background_audio = background_audio.volumex(bg_volume)

        if video_clip.audio and background_audio:
            final_audio = CompositeAudioClip([video_clip.audio, background_audio])
        elif background_audio:
            final_audio = background_audio
        else:
            final_audio = video_clip.audio

        return video_clip.set_audio(final_audio)


class RenderLayer:
    """
    Exports the final production-ready media artifact using optimized encoding settings.
    """

    @staticmethod
    def render(
        video_clip: CompositeVideoClip,
        output_path: str,
        fps: int,
        codec: str = "libx264",
        audio_codec: str = "aac",
        preset: str = "medium"
    ) -> None:
        print(f"[RenderLayer] Rendering project to {output_path}...")
        video_clip.write_videofile(
            output_path,
            fps=fps,
            codec=codec,
            audio_codec=audio_codec,
            preset=preset,
            logger="bar"
        )
        print("[RenderLayer] Render complete.")


# -----------------------------
# High-level Engine
# -----------------------------

class CodetteMediaEngine:
    def __init__(self, output_resolution: tuple = (1920, 1080), fps: int = 30):
        self.width, self.height = output_resolution
        self.fps = fps
        self.media_intake = MediaIntake()
        self.composition = CompositionPipeline()
        self.audio_sync = AudioSynchronizer()
        self.renderer = RenderLayer()
        print(f"[CodetteMediaEngine] Initialized at {self.width}x{self.height} @ {self.fps}FPS")

    def create_sequence(self, clip_paths: List[str]) -> CompositeVideoClip:
        clips = self.media_intake.load_video_sequence(
            clip_paths,
            target_resolution=(self.width, self.height)
        )
        return self.composition.create_sequence(clips)

    def add_soundtrack(
        self,
        video_clip: CompositeVideoClip,
        audio_path: Optional[str],
        audio_volume: float = 1.0
    ) -> CompositeVideoClip:
        if audio_path is None:
            return video_clip

        background_audio = self.media_intake.load_audio_clip(audio_path)
        return self.audio_sync.mix_audio(
            video_clip=video_clip,
            background_audio=background_audio,
            bg_volume=audio_volume
        )

    def overlay_text(
        self,
        video_clip: CompositeVideoClip,
        text: Optional[str],
        duration: Optional[float] = None,
        fontsize: int = 50,
        color: str = "white",
        font: str = "Arial",
        position: str = "center"
    ) -> CompositeVideoClip:
        if not text:
            return video_clip
        return self.composition.overlay_text(
            video_clip=video_clip,
            text=text,
            duration=duration,
            fontsize=fontsize,
            color=color,
            font=font,
            position=position
        )

    def render(
        self,
        video_clip: CompositeVideoClip,
        output_path: str,
        codec: str = "libx264",
        audio_codec: str = "aac"
    ) -> None:
        self.renderer.render(
            video_clip=video_clip,
            output_path=output_path,
            fps=self.fps,
            codec=codec,
            audio_codec=audio_codec
        )


# -----------------------------
# Render Plan Model
# -----------------------------

@dataclass
class TextOverlaySpec:
    text: str
    duration: Optional[float] = None
    fontsize: int = 50
    color: str = "white"
    font: str = "Arial"
    position: str = "center"


@dataclass
class AudioSpec:
    path: Optional[str] = None
    volume: float = 1.0


@dataclass
class OutputSpec:
    path: str
    width: int = 1280
    height: int = 720
    fps: int = 30
    codec: str = "libx264"
    audio_codec: str = "aac"


@dataclass
class RenderPlan:
    clips: List[str]
    audio: AudioSpec
    text_overlays: List[TextOverlaySpec]
    output: OutputSpec

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "RenderPlan":
        # Validate required fields
        if "clips" not in data or not isinstance(data["clips"], list) or not data["clips"]:
            raise ValidationError("Render plan must include non-empty 'clips' list.")

        if "output" not in data or not isinstance(data["output"], dict):
            raise ValidationError("Render plan must include 'output' configuration.")

        clips = data["clips"]

        audio_data = data.get("audio", {})
        audio = AudioSpec(
            path=audio_data.get("path"),
            volume=float(audio_data.get("volume", 1.0))
        )

        text_overlays_data = data.get("text_overlays", [])
        text_overlays: List[TextOverlaySpec] = []
        for item in text_overlays_data:
            if "text" not in item:
                raise ValidationError("Each text overlay must include 'text'.")
            text_overlays.append(
                TextOverlaySpec(
                    text=item["text"],
                    duration=item.get("duration"),
                    fontsize=int(item.get("fontsize", 50)),
                    color=item.get("color", "white"),
                    font=item.get("font", "Arial"),
                    position=item.get("position", "center")
                )
            )

        output_data = data["output"]
        if "path" not in output_data:
            raise ValidationError("Output configuration must include 'path'.")

        output = OutputSpec(
            path=output_data["path"],
            width=int(output_data.get("width", 1280)),
            height=int(output_data.get("height", 720)),
            fps=int(output_data.get("fps", 30)),
            codec=output_data.get("codec", "libx264"),
            audio_codec=output_data.get("audio_codec", "aac")
        )

        return RenderPlan(
            clips=clips,
            audio=audio,
            text_overlays=text_overlays,
            output=output
        )


# -----------------------------
# Pipeline Orchestrator
# -----------------------------

class CodetteMediaPipeline:
    """
    Orchestrates the full render pipeline from a JSON render plan.
    Deterministic: same plan → same output (given same inputs).
    """

    def __init__(self, plan: RenderPlan):
        self.plan = plan
        self.engine = CodetteMediaEngine(
            output_resolution=(plan.output.width, plan.output.height),
            fps=plan.output.fps
        )

    def execute(self) -> None:
        try:
            # 1. Create base sequence
            print("[Pipeline] Creating video sequence...")
            sequence_clip = self.engine.create_sequence(self.plan.clips)

            # 2. Add audio
            print("[Pipeline] Adding soundtrack...")
            sequence_with_audio = self.engine.add_soundtrack(
                video_clip=sequence_clip,
                audio_path=self.plan.audio.path,
                audio_volume=self.plan.audio.volume
            )

            # 3. Apply text overlays (stacked)
            final_clip = sequence_with_audio
            if self.plan.text_overlays:
                print("[Pipeline] Applying text overlays...")
                for overlay in self.plan.text_overlays:
                    final_clip = self.engine.overlay_text(
                        video_clip=final_clip,
                        text=overlay.text,
                        duration=overlay.duration,
                        fontsize=overlay.fontsize,
                        color=overlay.color,
                        font=overlay.font,
                        position=overlay.position
                    )

            # 4. Render
            print("[Pipeline] Rendering final output...")
            self.engine.render(
                video_clip=final_clip,
                output_path=self.plan.output.path,
                codec=self.plan.output.codec,
                audio_codec=self.plan.output.audio_codec
            )

        except Exception as e:
            raise PipelineError(f"Pipeline execution failed: {e}") from e


# -----------------------------
# CLI / Entry Point
# -----------------------------

def load_render_plan(path: str) -> RenderPlan:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Render plan file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return RenderPlan.from_dict(data)


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="CodetteMediaEngine - JSON-driven media render pipeline"
    )
    parser.add_argument(
        "--plan",
        type=str,
        required=True,
        help="Path to JSON render plan."
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> None:
    args = parse_args(argv)

    try:
        print(f"[Main] Loading render plan from {args.plan}...")
        plan = load_render_plan(args.plan)
        pipeline = CodetteMediaPipeline(plan)
        pipeline.execute()
        print("[Main] Render pipeline completed successfully.")
    except (ValidationError, FileNotFoundError, PipelineError) as e:
        print(f"[Error] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main(sys.argv[1:])
