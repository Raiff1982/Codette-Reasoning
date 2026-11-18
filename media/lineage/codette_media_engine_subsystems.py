# Extracted 2026-11-18 from Movie_engine.py (repository root), lines 1-207,
# by Jonathan's decision (docs/APPROVALS_2026-11-18.md, item 6). Movie_engine.py
# is a chat transcript holding three versions of this engine and a message
# between them; it is left untouched. This is the version with the four subsystems (MediaIntake,
# CompositionPipeline, AudioSynchronizer, RenderLayer). Kept as lineage;
# media/codette_media_engine.py contains all of it.
#
# Repairs, and nothing else: non-breaking spaces that stood in for indentation
# replaced with spaces; the opening triple quote of the module docstring, lost
# with the segment's first line, restored; then tools/archive_diff.py repair().
# No line of the code itself was changed.
#
# Needs moviepy 1.x (it imports moviepy.editor, removed in moviepy 2.0). See
# media/README.md for the Pillow note.

"""CodetteMediaEngine - Programmatic Film, Video, and Audio Composition Tool
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

