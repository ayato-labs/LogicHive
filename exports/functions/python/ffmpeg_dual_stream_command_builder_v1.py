import subprocess
from pathlib import Path

def build_ffmpeg_recording_command(
    device_name: str,
    output_sample_rate: int = 16000,
    mp3_path: str = None,
    mp3_bitrate: str = "64k"
) -> list:
    """
    Constructs an optimized FFmpeg command for simultaneous streaming.
    
    Args:
        device_name: The dshow audio device name (e.g., 'audio=Stereo Mix').
        output_sample_rate: Sample rate for the raw float32 stream.
        mp3_path: Optional path to save a persistent MP3 file.
        mp3_bitrate: Bitrate for the MP3 encoding.
        
    Returns:
        A list of command arguments for subprocess.Popen.
    """
    device_arg = f"audio={device_name}" if "audio=" not in device_name else device_name
    
    # Base command for raw float32 output to stdout
    command = [
        "ffmpeg", "-y", "-f", "dshow", "-i", device_arg,
        "-ac", "1", "-ar", str(output_sample_rate),
        "-f", "f32le", "-"
    ]
    
    # Optional MP3 branch
    if mp3_path:
        # Ensure parent directory exists (utility should probably expect this, but we can be safe)
        Path(mp3_path).parent.mkdir(parents=True, exist_ok=True)
        command.extend([
            "-f", "mp3", "-ac", "1", "-ab", mp3_bitrate, mp3_path
        ])
        
    return command
