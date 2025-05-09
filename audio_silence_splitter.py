#!/usr/bin/env python
#
# Based on a script by Donald Feury
# https://gitlab.com/dak425/scripts/-/blob/master/trim_silenceV2
# https://youtu.be/ak52RXKfDw8

import math
import os
from moviepy import AudioFileClip, VideoFileClip
from proglog.proglog import default_bar_logger


def clean_intervals(intervals_to_keep, silence_min_len=5):
    clean_intervals = []
    for x in range(len(intervals_to_keep)):
        # interval example[[0, 13.0], [13.5, 17.5], [39.5, 40.5]]
        timestamp = intervals_to_keep[x]
        if x >= 1:
            previoustimestamp = intervals_to_keep[x - 1]
            silence_gap = timestamp[0] - previoustimestamp[1]
            if silence_gap < silence_min_len:
                timestamp[0] = previoustimestamp[0]
                clean_intervals.remove(previoustimestamp)
        clean_intervals.append(timestamp)
    # trim_START_END = [clean_intervals[0][0], clean_intervals[-1][1]]

    return clean_intervals


# Iterate over audio to find the non-silent parts. Outputs a list of
# (speaking_start, speaking_end) intervals.
# Args:
#  window_size: (in seconds) hunt for silence in windows of this size
#  volume_threshold: volume below this threshold is considered to be silence
#  ease_in: (in seconds) add this much silence around speaking intervals
def find_speaking(
    dir,
    BEG_END_only=False,
    silence_min_len=5,
    volume_threshold=0.01,
    window_size=1,
    ease_in=0.6,
    logger="bar",
):
    logger = default_bar_logger(logger)  # shorthand to generate a bar logger
    try:
        video_clip = VideoFileClip(dir)
        audio_clip = video_clip.audio
    except:
        audio_clip = AudioFileClip(dir)
    # First, iterate over audio to find all silent windows.
    num_windows = math.floor(audio_clip.end / window_size)
    window_is_silent = []
    for i in logger.iter_bar(timestamps=range(num_windows)):
        s = audio_clip.subclipped(i * window_size, (i + 1) * window_size)
        v = s.max_volume()
        window_is_silent.append(v < volume_threshold)
    # Find speaking intervals.
    speaking_start = 0
    speaking_end = 0
    speaking_intervals = []
    for i in range(1, len(window_is_silent)):
        e1 = window_is_silent[i - 1]
        e2 = window_is_silent[i]
        # silence -> speaking
        if e1 and not e2:
            speaking_start = i * window_size
        # speaking -> silence, now have a speaking interval
        if not e1 and e2:
            speaking_end = i * window_size
            new_speaking_interval = [
                speaking_start - ease_in if speaking_start != 0 else 0,
                (
                    speaking_end + ease_in
                    if speaking_end <= audio_clip.duration - ease_in
                    else audio_clip.duration
                ),
            ]
            # Filter Intervals <= 2sec (crossfade=0.5)
            if new_speaking_interval[1] - new_speaking_interval[0] <= 2:
                continue
            # With tiny windows, this can sometimes overlap the previous window, so merge.

            if len(speaking_intervals) > 0:
                need_to_merge = speaking_intervals[-1][1] > new_speaking_interval[0]
                # or if silence is too short
                need_to_merge = (
                    need_to_merge
                    or new_speaking_interval[0] - speaking_intervals[-1][1]
                    < silence_min_len
                )
            else:
                need_to_merge = False
            if need_to_merge:
                merged_interval = [speaking_intervals[-1][0], new_speaking_interval[1]]
                speaking_intervals[-1] = merged_interval
            else:
                speaking_intervals.append(new_speaking_interval)

    clean_speaking_intervals = clean_intervals(speaking_intervals, silence_min_len)

    # Handle the BEG_END_only case
    if BEG_END_only and speaking_intervals:
        speaking_intervals_final = [
            [speaking_intervals[0][0], speaking_intervals[-1][1]]
        ]
    else:
        speaking_intervals_final = clean_speaking_intervals

    # Clean up resources
    try:
        audio_clip.close()
    except:
        pass

    return speaking_intervals_final


def main(
    file_in,
    output_path=None,
    NORMALIZATION=False,
    BEG_END_only=False,
    silence_min_len=5,
    volume_threshold=0.01,
    window_size=1,
    ease_in=0.6,
    logger="bar",
):
    """
    Process an audio/video file by removing silent parts.

    Args:
        file_in: Input file path
        output_path: Output file path or template for multiple clips
        NORMALIZATION: Whether to apply audio normalization
        BEG_END_only: If True, only trim beginning and end silence
        silence_min_len: Minimum length of silence to be considered a break
        volume_threshold: Volume below this threshold is considered silence
        window_size: Size of window for analyzing silence
        ease_in: Buffer to add before and after speech
        logger: Type of progress logger to use
    """
    silence_min_len = silence_min_len * 60  # Convert to seconds
    # Get intervals to keep (non-silent parts)
    intervals_to_keep = find_speaking(
        file_in,
        BEG_END_only=BEG_END_only,
        silence_min_len=silence_min_len,
        volume_threshold=volume_threshold,
        window_size=window_size,
        ease_in=ease_in,
        logger=logger,
    )

    print("Keeping intervals:", intervals_to_keep)

    # Determine if it's a video or audio file
    try:
        video_clip = VideoFileClip(file_in)
        is_video = True
        clip = video_clip.audio
    except:
        clip = AudioFileClip(file_in)
        is_video = False

    # Create subclippeds for each interval
    keep_clips = [
        clip.subclipped(max(start, 0), end) for [start, end] in intervals_to_keep
    ]

    # Determine output folder and filename
    if output_path:
        # If output_path is a directory, use it as processing_folder
        if os.path.isdir(output_path):
            processing_folder = output_path
            filename_template = (
                os.path.splitext(os.path.basename(file_in))[0] + "_clip_{0}.mp3"
            )
        else:
            # If the path contains a directory, use it
            processing_folder = os.path.dirname(output_path)
            if not processing_folder:
                processing_folder = os.path.join(os.path.dirname(file_in), "processing")

            # If BEG_END_only, use the output_path directly
            if BEG_END_only:
                filename_template = os.path.basename(output_path)
                # Ensure mp3 extension
                if not filename_template.lower().endswith(".mp3"):
                    filename_template = os.path.splitext(filename_template)[0] + ".mp3"
            else:
                # For multiple clips, check if output_path contains formatting
                if "{" in output_path and "}" in output_path:
                    # Use as template
                    filename_base = os.path.basename(output_path)
                    if not filename_base.lower().endswith(".mp3"):
                        filename_base = os.path.splitext(filename_base)[0] + ".mp3"

                    # This will be formatted later with index
                    filename_template = filename_base
                else:
                    # No formatting in template, add our own
                    filename_base = os.path.basename(output_path)
                    if not filename_base.lower().endswith(".mp3"):
                        filename_base = os.path.splitext(filename_base)[0] + ".mp3"

                    filename_template = (
                        os.path.splitext(filename_base)[0] + "_take_{0}.mp3"
                    )
    else:
        # Default output location
        processing_folder = os.path.join(os.path.dirname(file_in), "processing")
        filename_template = (
            os.path.splitext(os.path.basename(file_in))[0] + "_take_{0}.mp3"
        )

    # Ensure the output directory exists
    os.makedirs(processing_folder, exist_ok=True)

    # Process and save each clip
    for index, audio_clip in enumerate(keep_clips):
        # Format the filename
        if "{" in filename_template and "}" in filename_template:
            # Use advanced formatting with the template
            original_name = os.path.splitext(os.path.basename(file_in))[0]
            start, end = intervals_to_keep[index]

            clip_filename = filename_template.format(
                filename=original_name, index=index + 1, start=int(start), end=int(end)
            )

            # Ensure mp3 extension
            if not clip_filename.lower().endswith(".mp3"):
                clip_filename = os.path.splitext(clip_filename)[0] + ".mp3"
        else:
            # Simple formatting
            clip_filename = filename_template.format(index + 1)

        clip_path = os.path.join(processing_folder, clip_filename)

        # Save the file (always as MP3)
        audio_clip.write_audiofile(
            clip_path,
            ffmpeg_params=(
                ["-af", "highpass=f=60,dynaudnorm=f=150:g=15:p=0.7:m=10:s=0"]
                if NORMALIZATION
                else []
            ),
        )

    # Clean up resources
    clip.close()
    if is_video and "video_clip" in locals():
        video_clip.close()

    if not intervals_to_keep:
        processing_folder = "Audio was silent, no clips created."

    return processing_folder


if __name__ == "__main__":
    main(r"C:\Users\Max\Downloads\recording_2025-04-28_16_36s.webm", NORMALIZATION=True)
