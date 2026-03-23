import os
from datetime import datetime
from uuid import uuid4

from PIL import Image as PILImage
from moviepy.editor import AudioFileClip, CompositeAudioClip, ImageClip, concatenate_videoclips
from moviepy.video.fx.all import crop

from config import ROOT_DIR, get_threads
from status import info, success
from utils import choose_random_song

if not hasattr(PILImage, "ANTIALIAS") and hasattr(PILImage, "Resampling"):
    PILImage.ANTIALIAS = PILImage.Resampling.LANCZOS


def discover_latest_wav(mp_dir: str) -> str:
    wavs = [
        os.path.join(root, name)
        for root, _, files in os.walk(mp_dir)
        for name in files
        if name.lower().endswith(".wav")
    ]
    if not wavs:
        raise RuntimeError("No WAV files found in .mp/")
    return max(wavs, key=os.path.getmtime)


def discover_latest_mp4(mp_dir: str) -> str:
    mp4s = [
        os.path.join(root, name)
        for root, _, files in os.walk(mp_dir)
        for name in files
        if name.lower().endswith(".mp4")
    ]
    if not mp4s:
        raise RuntimeError("No MP4 files found in .mp/")
    return max(mp4s, key=os.path.getmtime)


def discover_images(mp_dir: str, wav_path: str, window_minutes: int) -> list[str]:
    image_dir = os.path.dirname(wav_path)
    wav_mtime = os.path.getmtime(wav_path)
    min_mtime = wav_mtime - (window_minutes * 60)

    images = [
        os.path.join(image_dir, name)
        for name in os.listdir(image_dir)
        if name.lower().endswith(".png")
        and min_mtime <= os.path.getmtime(os.path.join(image_dir, name)) <= wav_mtime
    ]

    if not images:
        images = [
            os.path.join(image_dir, name)
            for name in os.listdir(image_dir)
            if name.lower().endswith(".png")
        ]

    images.sort(key=os.path.getmtime)
    if not images:
        raise RuntimeError("No PNG files found in .mp/")

    return images


def recover_last_video(
    wav_path: str | None = None,
    output_path: str | None = None,
    window_minutes: int = 120,
    return_details: bool = False,
):
    mp_dir = os.path.join(ROOT_DIR, ".mp")
    try:
        wav_path = os.path.abspath(wav_path) if wav_path else discover_latest_wav(mp_dir)
    except RuntimeError:
        existing_mp4 = discover_latest_mp4(mp_dir)
        details = {
            "created_at": datetime.now().isoformat(),
            "wav": "",
            "images": 0,
            "output": existing_mp4,
            "song": "",
            "reused_existing_mp4": True,
        }
        success(f"Using existing recovered video {existing_mp4}")
        if return_details:
            return details
        return existing_mp4
    images = discover_images(mp_dir, wav_path, window_minutes)
    output_path = os.path.abspath(output_path) if output_path else os.path.join(mp_dir, f"{uuid4()}.mp4")

    info(f"Recovering video from {len(images)} image(s) and WAV {os.path.basename(wav_path)}")

    tts_clip = AudioFileClip(wav_path)
    max_duration = tts_clip.duration
    req_dur = max_duration / len(images)

    clips = []
    for image_path in images:
        clip = ImageClip(image_path)
        clip.duration = req_dur
        clip = clip.set_fps(30)

        if round((clip.w / clip.h), 4) < 0.5625:
            clip = crop(
                clip,
                width=clip.w,
                height=round(clip.w / 0.5625),
                x_center=clip.w / 2,
                y_center=clip.h / 2,
            )
        else:
            clip = crop(
                clip,
                width=round(0.5625 * clip.h),
                height=clip.h,
                x_center=clip.w / 2,
                y_center=clip.h / 2,
            )

        clips.append(clip.resize((1080, 1920)))

    final_clip = concatenate_videoclips(clips).set_fps(30)
    random_song = choose_random_song()
    random_song_clip = AudioFileClip(random_song).set_fps(44100).volumex(0.1)
    comp_audio = CompositeAudioClip([tts_clip.set_fps(44100), random_song_clip])

    final_clip = final_clip.set_audio(comp_audio)
    final_clip = final_clip.set_duration(tts_clip.duration)
    final_clip.write_videofile(output_path, threads=get_threads())

    created_at = datetime.now().isoformat()
    success(f"Recovered video written to {output_path}")
    print(f"created_at={created_at}")
    print(f"wav={wav_path}")
    print(f"images={len(images)}")
    print(f"output={output_path}")

    details = {
        "created_at": created_at,
        "wav": wav_path,
        "images": len(images),
        "output": output_path,
        "song": random_song,
        "reused_existing_mp4": False,
    }
    if return_details:
        return details
    return output_path
