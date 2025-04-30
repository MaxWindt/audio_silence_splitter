#!/usr/bin/env python
#
# Based on a script by Donald Feury
# https://gitlab.com/dak425/scripts/-/blob/master/trim_silenceV2
# https://youtu.be/ak52RXKfDw8

import math
import os
from moviepy.editor import AudioFileClip, VideoFileClip
from proglog.proglog import default_bar_logger

import math


def clean_intervals(intervals_to_keep, silence_min_len=3):
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
    video_dir,
    BEG_END_only=False,
    silence_min_len=600,
    volume_threshold=0.01,
    window_size=1,
    ease_in=0.6,
    logger="bar",
):
    logger = default_bar_logger(logger)  # shorthand to generate a bar logger
    try:
        video_clip = VideoFileClip(video_dir)
        audio_clip = video_clip.audio
    except:
        audio_clip = AudioFileClip(video_dir)
    # First, iterate over audio to find all silent windows.
    num_windows = math.floor(audio_clip.end / window_size)
    window_is_silent = []
    for i in logger.iter_bar(timestamps=range(num_windows)):
        s = audio_clip.subclip(i * window_size, (i + 1) * window_size)
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

    speaking_intervals_final = (
        clean_speaking_intervals
        if not BEG_END_only
        else [speaking_intervals[0][0], speaking_intervals[-1][1]]
    )
    return speaking_intervals_final


def main(file_in, NORMALIZATION=False):
    # Parse args
    # Input file path
    NORMALIZATION = False

    intervals_to_keep = find_speaking(file_in)
    try:
        video_clip = VideoFileClip(file_in)
        clip = video_clip.audio
    except:
        clip = AudioFileClip(file_in)

    print("Keeping intervals: " + str(intervals_to_keep))

    keep_clips = [
        clip.subclip(max(start, 0), end) for [start, end] in intervals_to_keep
    ]

    processing_folder = os.path.join(os.path.dirname(file_in), "processing")
    os.makedirs(processing_folder, exist_ok=True)

    for index, clip in enumerate(keep_clips):
        clip_path = os.path.join(
            processing_folder,
            os.path.splitext(os.path.basename(file_in))[0] + f"_take_{index+1}.mp3",
        )
        clip.write_audiofile(
            clip_path,
            ffmpeg_params=(
                [
                    "-af",
                    "highpass=f=60,dynaudnorm=f=150:g=15:p=0.7:m=10:s=0",
                ]
                if NORMALIZATION
                else []
            ),
        )
    clip.close()


if __name__ == "__main__":
    main(r"C:\Users\Max\Downloads\recording_2025-04-27_13_13.webm", True)
