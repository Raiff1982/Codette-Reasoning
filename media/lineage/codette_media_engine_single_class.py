# Extracted 2026-11-18 from Movie_engine.py (repository root), lines 208-283,
# by Jonathan's decision (docs/APPROVALS_2026-11-18.md, item 6). Movie_engine.py
# is a chat transcript holding three versions of this engine and a message
# between them; it is left untouched. This is the simpler single-class version. Kept as lineage;
# media/codette_media_engine.py contains all of it.
#
# Repairs, and nothing else: non-breaking spaces that stood in for indentation
# replaced with spaces; the opening triple quote of the module docstring, lost
# with the segment's first line, restored; then tools/archive_diff.py repair().
# No line of the code itself was changed.
#
# Needs moviepy 1.x (it imports moviepy.editor, removed in moviepy 2.0). See
# media/README.md for the Pillow note.

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


